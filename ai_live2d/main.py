#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI桌面宠物核心服务 - 集成Qt事件循环和asyncio
"""
import sys
import os
# === 添加强制UTF-8编码设置 ===
if sys.platform.startswith("win"):
    # Windows系统需要特别处理
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') # type: ignore
    sys.stderr.reconfigure(encoding='utf-8', errors='replace') # type: ignore
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"
else:
    # 非Windows系统
    sys.stdout.reconfigure(encoding='utf-8') # type: ignore
    sys.stderr.reconfigure(encoding='utf-8') # type: ignore

import asyncio
import logging
import signal
import sys
import os
import json
import traceback
import re
# 注释掉不再使用的socket导入
# import socket
import threading
import time
from pathlib import Path
from typing import Any

# Qt相关导入
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtCore import Qt

# 导入核心管理器
from core.app_manager import AppManager
from utils.logger import setup_logger
import qasync
from utils.message_queue import get_message_queue
from utils.lrc_manager import LRCManager
from interface.action_buttons import ActionButtonsWindow
import io
import wave
import numpy as np
import sounddevice as sd
import tempfile

class PetService:
    """AI桌面宠物服务类 - 支持Qt和asyncio集成"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.app_manager: AppManager|None = None
        self.qt_app: QApplication|None = None
        self.logger: Any = None
        self._running: bool = False
        self._shutdown_event = asyncio.Event()
        
        # 进程间通信相关 - 使用消息队列替代socket
        self.message_queue = get_message_queue()
        self.interrupt_signal_file = Path("interrupt_signal.tmp")
        self.event_loop = None  # 保存事件循环引用
        
        # 音频播放相关
        self.audio_thread = None
        self._stop_singing = False
        self.current_audio_stream = None
        
        # 动作按钮相关
        self.action_buttons_window = None
        
        # LRC歌词管理器
        self.lrc_manager = None
    
    # ====== 文本清洗与可见内容提取 ======
    def _strip_think_blocks(self, text: str) -> str:
        """移除深度思考标记块，例如 <think>...</think>。
        - 大小写不敏感，跨行匹配；
        - 多个片段全部移除；
        - 若存在不闭合的 <think>，则从该标签起始到文本末尾全部移除。
        """
        if not text:
            return text
        # 先移除成对的 <think>...</think>
        cleaned = re.sub(r"(?is)<\s*think\b[^>]*>.*?<\s*/\s*think\s*>", "", text)
        # 再兜底移除未闭合的 <think>...（直到文本末尾）
        cleaned = re.sub(r"(?is)<\s*think\b[^>]*>.*$", "", cleaned)
        return cleaned

    def _sanitize_visible_text(self, text: str) -> str:
        """获取可对外展示/朗读的文本：
        1) 去掉 <think> 思考内容；
        2) 收敛多余空白；
        3) 去除首尾空白。
        """
        if not text:
            return text
        cleaned = self._strip_think_blocks(text)
        # 收敛连续空行为单个空行，收敛多空格
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
        return cleaned.strip()
        
    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 设置日志
            self.logger = setup_logger(
                level=logging.DEBUG,
                log_file="pet_system.log"
            )
            self.logger.info(">>> 初始化AI桌宠系统... [ 进行中 ]")
            
            # 记录主进程PID
            import os
            main_pid = os.getpid()
            try:
                with open('main_pid.txt', 'w', encoding='utf-8') as f:
                    f.write(str(main_pid))
                self.logger.info(f">>> 主进程PID已记录: {main_pid}")
            except Exception as e:
                self.logger.warning(f">>> 记录主进程PID失败: {e}")
            
            # 检查配置文件
            if not self.config_path.exists():
                raise FileNotFoundError(f">>> 配置文件不存在: {self.config_path}")
            
            # 创建应用管理器
            self.app_manager = AppManager(str(self.config_path))
            
            # 初始化应用管理器
            await self.app_manager.initialize()
            
            # 启动消息队列监听器
            self.start_message_listener()
            
            # 初始化动作按钮窗口
            self.initialize_action_buttons()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 系统初始化失败: {e}")
            raise
    
    async def start(self) -> None:
        """启动服务"""
        try:
            self._running = True
            
            # 保存当前事件循环引用，用于线程间通信
            self.event_loop = asyncio.get_running_loop()
            
            # 启动应用管理器
            assert self.app_manager is not None
            await self.app_manager.start()
            self.logger.info(">>> 初始化AI桌宠系统... [ 完成 ]")
            
            # 检查并显示动作按钮
            self.check_and_show_action_buttons()
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f">>> 服务运行错误: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """关闭服务"""
        if not self._running:
            return
            
        self._running = False
        
        try:
            if self.logger:
                self.logger.info(">>> 关闭AI桌宠系统... [ 进行中 ]")
            
            # 关闭应用管理器
            if self.app_manager:
                await self.app_manager.shutdown()
                if self.logger:
                    self.logger.info(">>> 应用管理器... [ 已关闭 ]")
            
            # 停止消息队列监听器
            self.stop_message_listener()
            
            # 清理事件循环引用
            self.event_loop = None
            
            # 清理PID文件
            import os
            pid_files = ['main_pid.txt', 'tts_pid.txt', 'asr_pid.txt', 'audio_pid.txt']
            for pid_file in pid_files:
                try:
                    if os.path.exists(pid_file):
                        os.remove(pid_file)
                        if self.logger:
                            self.logger.info(f">>> 清理PID文件: {pid_file}")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 清理PID文件失败 {pid_file}: {e}")
            
            if self.logger:
                self.logger.info(">>> AI桌宠系统... [ 已关闭 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 关闭服务时出错: {e}")
    
    def request_shutdown(self):
        """请求关闭服务"""
        if self._running:
            self._shutdown_event.set()

    def start_message_listener(self):
        """启动消息队列监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 启动消息队列监听器... [ 进行中 ]")
            
            # 注册消息处理器
            self.message_queue.register_handler('interrupt', self._handle_interrupt_message)
            self.message_queue.register_handler('shutdown', self._handle_shutdown_message)
            self.message_queue.register_handler('play_audio', self._handle_play_audio_message)
            self.message_queue.register_handler('custom_action', self._handle_custom_action_message)
            self.message_queue.register_handler('show_action_buttons', self._handle_show_action_buttons_message)
            self.message_queue.register_handler('hide_action_buttons', self._handle_hide_action_buttons_message)
            self.message_queue.register_handler('show_subtitle', self._handle_show_subtitle_message)
            self.message_queue.register_handler('hide_subtitle', self._handle_hide_subtitle_message)
            self.message_queue.register_handler('update_subtitle_display', self._handle_update_subtitle_display_message)
            self.message_queue.register_handler('set_live2d_parts_opacity', self._handle_set_live2d_parts_opacity_message)
            
            # 启动监听器
            self.message_queue.start_listener()
            
            if self.logger:
                self.logger.info(">>> 消息队列监听器... [ 已启动 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 启动消息队列监听器失败: {e}")

    def stop_message_listener(self):
        """停止消息队列监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 停止消息队列监听器... [ 进行中 ]")
            
            # 停止监听器
            self.message_queue.stop_listener()
            
            if self.logger:
                self.logger.info(">>> 消息队列监听器... [ 已停止 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 停止消息队列监听器失败: {e}")

    def _handle_interrupt_message(self, data):
        """处理中断消息"""
        try:
            if self.logger:
                self.logger.info(">>> 收到中断消息")
            
            # 安全地在主事件循环中运行异步中断操作
            if self.event_loop and self.event_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._perform_interrupt(), 
                    self.event_loop
                )
            else:
                if self.logger:
                    self.logger.warning(">>> 事件循环不可用，无法执行异步中断操作")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理中断消息时出错: {e}")

    def _handle_shutdown_message(self, data):
        """处理关闭消息"""
        try:
            if self.logger:
                self.logger.info(">>> 收到关闭消息")
            self.request_shutdown()
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理关闭消息时出错: {e}")

    def _handle_play_audio_message(self, data):
        """处理音频播放消息"""
        try:
            if self.logger:
                self.logger.info(">>> 收到音频播放消息")
            
            audio_data_b64 = data.get('audio_data', '')
            volume = data.get('volume', 1.0)
            loop = data.get('loop', False)
            singing_motion = data.get('singing_motion', '唱歌')
            lrc_content = data.get('lrc_content', '')  # 添加LRC歌词内容
            
            if audio_data_b64:
                import base64
                audio_data = base64.b64decode(audio_data_b64)
                self.play_singing_audio(audio_data, volume, loop, singing_motion, lrc_content)
                if self.logger:
                    self.logger.info(">>> 收到音频播放请求，开始播放")
            else:
                if self.logger:
                    self.logger.warning(">>> 音频播放请求缺少音频数据")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理音频播放消息时出错: {e}")

    def _handle_custom_action_message(self, data):
        """处理自定义动作消息"""
        try:
            action_num = data.get('action_num', 1)
            self.trigger_custom_action(action_num)
            if self.logger:
                self.logger.info(f">>> 收到自定义动作请求: {action_num}")
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理自定义动作消息时出错: {e}")

    def _handle_show_action_buttons_message(self, data):
        """处理显示动作按钮消息"""
        try:
            self.show_action_buttons()
            if self.logger:
                self.logger.info(">>> 收到显示动作按钮请求")
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理显示动作按钮消息时出错: {e}")

    def _handle_hide_action_buttons_message(self, data):
        """处理隐藏动作按钮消息"""
        try:
            self.hide_action_buttons()
            if self.logger:
                self.logger.info(">>> 收到隐藏动作按钮请求")
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理隐藏动作按钮消息时出错: {e}")

    def _handle_show_subtitle_message(self, data):
        """处理显示字幕消息"""
        try:
            subtitle_text = data.get('text', '')
            source = data.get('source', 'unknown')
            if subtitle_text:
                self.show_subtitle(subtitle_text, source)
                if self.logger:
                    self.logger.info(f">>> 收到字幕显示请求: {source} - {subtitle_text[:30]}...")
            else:
                if self.logger:
                    self.logger.warning(">>> 字幕显示请求缺少文本内容")
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理字幕显示消息时出错: {e}")

    def _handle_hide_subtitle_message(self, data):
        """处理隐藏字幕消息"""
        try:
            source = data.get('source', 'unknown')
            if self.subtitle_manager:
                self.subtitle_manager.clear_text()
                if self.logger:
                    self.logger.info(f">>> 收到字幕隐藏请求: {source}")
            else:
                if self.logger:
                    self.logger.warning(">>> 字幕管理器未初始化")
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理字幕隐藏消息时出错: {e}")

    def _handle_update_subtitle_display_message(self, data):
        """处理更新字幕显示设置消息"""
        try:
            monitor_index = data.get('monitor_index')
            position = data.get('position')
            position_x = data.get('position_x')
            position_y = data.get('position_y')
            offset_x = data.get('offset_x')
            offset_y = data.get('offset_y')
            
            if self.logger:
                self.logger.info(f">>> 收到字幕显示设置更新请求: monitor={monitor_index}, position={position}, coords=({position_x}, {position_y}), offset=({offset_x}, {offset_y})")
            
            # 调用字幕显示设置更新方法
            self.update_subtitle_display_settings(
                monitor_index=monitor_index,
                position=position,
                position_x=position_x,
                position_y=position_y,
                offset_x=offset_x,
                offset_y=offset_y
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理字幕显示设置更新消息时出错: {e}")

    def _handle_set_live2d_parts_opacity_message(self, data):
        """处理设置Live2D部件透明度消息"""
        try:
            parts_opacity = data.get('parts_opacity', {})
            
            if self.logger:
                self.logger.info(f">>> 收到Live2D部件透明度设置请求: {len(parts_opacity)} 个部件")
            
            # 在事件循环中运行异步操作
            if self.event_loop and self.event_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._apply_live2d_parts_opacity(parts_opacity), 
                    self.event_loop
                )
            else:
                if self.logger:
                    self.logger.warning(">>> 事件循环不可用，无法应用Live2D部件透明度设置")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理Live2D部件透明度设置消息时出错: {e}")

    async def _apply_live2d_parts_opacity(self, parts_opacity):
        """应用Live2D部件透明度设置"""
        try:
            if self.logger:
                self.logger.info(f">>> 应用Live2D部件透明度设置: {len(parts_opacity)} 个部件")
            
            if not self.app_manager or not hasattr(self.app_manager, 'live2d_model') or not self.app_manager.live2d_model:
                if self.logger:
                    self.logger.warning(">>> Live2D模型不可用，无法应用部件透明度设置")
                return
            
            live2d_model = self.app_manager.live2d_model
            
            # 应用每个部件的透明度设置
            applied_count = 0
            for part_id, opacity in parts_opacity.items():
                try:
                    # 将百分比转换为0-1之间的浮点数
                    opacity_float = opacity / 100.0
                    
                    # 尝试设置部件透明度
                    if hasattr(live2d_model, 'set_part_opacity'):
                        # 如果模型有直接的方法
                        live2d_model.set_part_opacity(part_id, opacity_float)
                        applied_count += 1
                    elif hasattr(live2d_model, 'model') and live2d_model.model:
                        # 通过Live2D SDK设置
                        if hasattr(live2d_model.model, 'SetPartOpacity'):
                            # 查找部件索引
                            part_index = self._find_live2d_part_index(live2d_model.model, part_id)
                            if part_index >= 0:
                                live2d_model.model.SetPartOpacity(part_index, opacity_float)
                                applied_count += 1
                        elif hasattr(live2d_model.model, 'GetPartCount'):
                            # 尝试通过部件ID设置
                            part_count = live2d_model.model.GetPartCount()
                            for i in range(part_count):
                                part_id_obj = live2d_model.model.GetPartId(i)
                                current_part_id = part_id_obj.ToString() if hasattr(part_id_obj, 'ToString') else str(part_id_obj)
                                if current_part_id == part_id:
                                    if hasattr(live2d_model.model, 'SetPartOpacity'):
                                        live2d_model.model.SetPartOpacity(i, opacity_float)
                                        applied_count += 1
                                    break
                    else:
                        # 尝试通用方法
                        if hasattr(live2d_model, 'setParamFloat'):
                            # 有些Live2D实现使用参数方式控制透明度
                            param_name = f"PartOpacity{part_id}"
                            live2d_model.setParamFloat(param_name, opacity_float)
                            applied_count += 1
                            
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 设置部件 {part_id} 透明度失败: {e}")
            
            if self.logger:
                self.logger.info(f">>> Live2D部件透明度设置完成: {applied_count}/{len(parts_opacity)} 个部件已应用")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 应用Live2D部件透明度设置时出错: {e}")

    def _find_live2d_part_index(self, model, part_id):
        """查找Live2D部件的索引"""
        try:
            if hasattr(model, 'GetPartCount'):
                part_count = model.GetPartCount()
                for i in range(part_count):
                    part_id_obj = model.GetPartId(i)
                    current_part_id = part_id_obj.ToString() if hasattr(part_id_obj, 'ToString') else str(part_id_obj)
                    if current_part_id == part_id:
                        return i
            return -1
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 查找部件索引失败: {e}")
            return -1

    async def _perform_interrupt(self):
        """执行中断操作"""
        try:
            if self.logger:
                self.logger.info(">>> 执行中断操作... [ 进行中 ]")
            
            # 中断LLM输出
            if self.app_manager and hasattr(self.app_manager, 'llm_client') and self.app_manager.llm_client:
                if hasattr(self.app_manager.llm_client, 'interrupt'):
                    self.app_manager.llm_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> LLM输出已中断")
                # 将过滤拦截标志置为True，用于忽略随后可能到来的流式片段（与过滤硬停保持一致）
                if hasattr(self.app_manager, 'filter_block_active'):
                    self.app_manager.filter_block_active = True
                if hasattr(self.app_manager, 'filter_block_replacement_sent'):
                    # 手动中断不显示替代文本，但标志保持默认False也可
                    self.app_manager.filter_block_replacement_sent = False
                # 标记LLM流式结束
                if hasattr(self.app_manager, 'llm_streaming'):
                    self.app_manager.llm_streaming = False
            
            # 中断TTS播放（仅清空与复位，不关闭会话或循环）
            if self.app_manager and hasattr(self.app_manager, 'tts_client') and self.app_manager.tts_client:
                if hasattr(self.app_manager.tts_client, 'interrupt'):
                    self.app_manager.tts_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> TTS播放已中断")
                try:
                    if hasattr(self.app_manager.tts_client, 'reset'):
                        await self.app_manager.tts_client.reset()
                    # 清空累计文本，确保不再继续送入分段
                    if hasattr(self.app_manager.tts_client, 'current_full_text'):
                        self.app_manager.tts_client.current_full_text = ''
                    if self.logger:
                        self.logger.info(">>> 已清空TTS队列并复位")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 清空TTS队列失败: {e}")
            
            # 中断ASR
            if self.app_manager and hasattr(self.app_manager, 'asr_client') and self.app_manager.asr_client:
                if hasattr(self.app_manager.asr_client, 'interrupt'):
                    self.app_manager.asr_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> ASR已中断")
                elif hasattr(self.app_manager.asr_client, 'stop'):
                    await self.app_manager.asr_client.stop()
                    if self.logger:
                        self.logger.info(">>> ASR已中断")
            
            # 中断字幕显示
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                self.app_manager.subtitle_manager.clear_text()
                if self.logger:
                    self.logger.info(">>> 字幕已中断")
            
            # 停止Live2D动作
            if self.app_manager and hasattr(self.app_manager, 'live2d_model') and self.app_manager.live2d_model:
                # 这里可以调用Live2D的停止方法
                if self.logger:
                    self.logger.info(">>> Live2D动作已停止")
            
            # 停止音频播放
            self.stop_audio_playback()
            
            # 停止LRC歌词播放
            if self.lrc_manager:
                try:
                    self.lrc_manager.stop_playback()
                    if self.logger:
                        self.logger.info(">>> LRC歌词播放已中断")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 中断LRC歌词播放失败: {e}")
            
            # 重置动作按钮
            self.reset_action_buttons()
            
            # 同步ASR锁定状态，避免残留锁定
            try:
                if self.app_manager and hasattr(self.app_manager, '_check_and_update_asr_status'):
                    await self.app_manager._check_and_update_asr_status()
            except Exception as e:
                if self.logger:
                    self.logger.warning(f">>> 刷新ASR状态失败: {e}")
            
            if self.logger:
                self.logger.info(">>> 中断操作... [ 完成 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 执行中断操作时出错: {e}")

    def initialize_action_buttons(self):
        """检查中断信号文件"""
        try:
            if self.interrupt_signal_file.exists():
                # 读取信号文件
                with open(self.interrupt_signal_file, 'r', encoding='utf-8') as f:
                    signal_data = json.load(f)
                
                if self.logger:
                    self.logger.info(">>> 收到中断信号文件")
                
                # 处理中断信号
                self._process_interrupt_signal(signal_data)
                
                # 删除信号文件
                self.interrupt_signal_file.unlink()
                
        except FileNotFoundError:
            pass  # 文件不存在，正常情况
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 处理中断信号文件出错: {e}")

    def _process_interrupt_signal(self, signal_data):
        """处理中断信号"""
        try:
            if self.logger:
                self.logger.info(f">>> 处理中断信号: {signal_data}")
            
            signal_type = signal_data.get('type', 'interrupt')
            
            if signal_type == 'interrupt':
                # 安全地在主事件循环中运行异步中断操作
                if self.event_loop and self.event_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self._perform_interrupt(), 
                        self.event_loop
                    )
                    # 可选：等待完成或设置回调
                    # future.add_done_callback(lambda f: print("中断操作完成"))
                else:
                    if self.logger:
                        self.logger.warning(">>> 事件循环不可用，无法执行异 asynchronous中断操作")
            elif signal_type == 'shutdown':
                # 请求关闭服务
                self.request_shutdown()
            elif signal_type == 'play_audio':
                # 处理音频播放请求
                audio_data_b64 = signal_data.get('audio_data', '')
                volume = signal_data.get('volume', 1.0)
                loop = signal_data.get('loop', False)
                singing_motion = signal_data.get('singing_motion', '唱歌')
                
                if audio_data_b64:
                    import base64
                    audio_data = base64.b64decode(audio_data_b64)
                    self.play_singing_audio(audio_data, volume, loop, singing_motion)
                    if self.logger:
                        self.logger.info(">>> 收到音频播放请求，开始播放")
                else:
                    if self.logger:
                        self.logger.warning(">>> 音频播放请求缺少音频数据")
            elif signal_type == 'custom_action':
                # 处理自定义动作请求
                action_num = signal_data.get('action_num', 1)
                self.trigger_custom_action(action_num)
                if self.logger:
                    self.logger.info(f">>> 收到自定义动作请求: {action_num}")
            elif signal_type == 'show_action_buttons':
                # 处理显示动作按钮请求
                self.show_action_buttons()
                if self.logger:
                    self.logger.info(">>> 收到显示动作按钮请求")
            elif signal_type == 'hide_action_buttons':
                # 处理隐藏动作按钮请求
                self.hide_action_buttons()
                if self.logger:
                    self.logger.info(">>> 收到隐藏动作按钮请求")
            elif signal_type == 'show_subtitle':
                # 处理显示字幕请求
                subtitle_text = signal_data.get('text', '')
                source = signal_data.get('source', 'unknown')
                if subtitle_text:
                    self.show_subtitle(subtitle_text, source)
                    if self.logger:
                        self.logger.info(f">>> 收到字幕显示请求: {source} - {subtitle_text[:30]}...")
                else:
                    if self.logger:
                        self.logger.warning(">>> 字幕显示请求缺少文本内容")
            else:
                if self.logger:
                    self.logger.warning(f">>> 未知的信号类型: {signal_type}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理中断信号时出错: {e}")
                import traceback
                self.logger.error(f">>> 错误详情: {traceback.format_exc()}")

    def initialize_action_buttons(self):
        """初始化动作按钮窗口"""
        try:
            if self.logger:
                self.logger.info(">>> 初始化动作按钮窗口... [ 进行中 ]")
            
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 创建动作按钮窗口（作为顶级窗口）
            self.action_buttons_window = ActionButtonsWindow(config_data, None, None)
            
            # 设置窗口属性，确保它能正确显示
            if self.action_buttons_window:
                # 确保窗口在所有桌面之上
                self.action_buttons_window.setWindowFlags(
                    self.action_buttons_window.windowFlags() | Qt.WindowStaysOnTopHint
                )
                # 设置窗口位置（屏幕右下角）
                screen_rect = QApplication.desktop().availableGeometry()
                self.action_buttons_window.move(
                    screen_rect.width() - self.action_buttons_window.width() - 50,
                    screen_rect.height() - self.action_buttons_window.height() - 150
                )
            
            # 连接动作按钮信号到服务方法
            if self.action_buttons_window:
                self.action_buttons_window.interrupt_btn.clicked.connect(self.interrupt_current_operations)
                self.action_buttons_window.action_one_btn.clicked.connect(lambda: self.trigger_custom_action(1))
                self.action_buttons_window.action_two_btn.clicked.connect(lambda: self.trigger_custom_action(2))
            
            if self.logger:
                self.logger.info(">>> 动作按钮窗口... [ 已初始化 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 初始化动作按钮窗口失败: {e}")
            import traceback
            if self.logger:
                self.logger.error(f">>> 错误详情: {traceback.format_exc()}")

    def check_and_show_action_buttons(self):
        """检查配置文件并显示动作按钮"""
        try:
            if self.logger:
                self.logger.info(">>> 检查动作按钮启用状态...")
            
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查动作按钮是否启用
            action_buttons_enabled = config_data.get('setting', {}).get('action_buttons_enabled', False)
            
            if self.logger:
                self.logger.info(f">>> 动作按钮启用状态: {action_buttons_enabled}")
            
            if action_buttons_enabled:
                # 显示动作按钮
                self.show_action_buttons()
                if self.logger:
                    self.logger.info(">>> 动作按钮已显示")
            else:
                # 隐藏动作按钮
                self.hide_action_buttons()
                if self.logger:
                    self.logger.info(">>> 动作按钮已禁用，不显示")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 检查并显示动作按钮失败: {e}")
            import traceback
            if self.logger:
                self.logger.error(f">>> 错误详情: {traceback.format_exc()}")

    def interrupt_current_operations(self):
        """打断当前AI输出和语音播放"""
        try:
            if self.logger:
                self.logger.info(">>> UI请求中断当前操作")
            
            # 设置停止标志
            self._stop_singing = True
            
            # 执行中断操作
            if self.event_loop and self.event_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._perform_interrupt(), 
                    self.event_loop
                )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 中断操作失败: {e}")

    def trigger_custom_action(self, action_num):
        """触发自定义动作"""
        try:
            if self.logger:
                self.logger.info(f">>> 触发自定义动作: {action_num}")
            
            # 从配置文件中获取动作配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            action_config = config_data.get('action_buttons', {})
            action_key = f'action_{action_num}'
            
            if action_key in action_config:
                motion_name = action_config[action_key]
                if motion_name:
                    motion_index = self._get_motion_index_by_name(motion_name)
                    if motion_index is not None:
                        # 触发Live2D动作
                        if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                            # 这里可以调用Live2D模型的动作触发方法
                            if self.logger:
                                self.logger.info(f">>> 播放动作: {motion_name} (索引: {motion_index})")
                        return
            
            # 使用默认动作
            default_motion = action_num
            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                if self.logger:
                    self.logger.info(f">>> 播放默认动作 (索引: {default_motion})")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 触发自定义动作失败: {e}")

    def _get_motion_index_by_name(self, motion_name):
        """根据动作名称获取motion index"""
        motion_map = {
            '唱歌': 5,
            '开始唱歌': 5,
            '停止唱歌': 7,
            '跳舞': 6,
            '开心': 1,
            '悲伤': 2,
            '生气': 3,
            '惊讶': 4
        }
        return motion_map.get(motion_name, 5)  # 默认唱歌动作

    def _set_live2d_motion(self, motion_index):
        """设置Live2D动作的统一方法"""
        try:
            if self.app_manager and hasattr(self.app_manager, 'live2d_model') and self.app_manager.live2d_model:
                # 检查Live2D模型的正确方法名
                if hasattr(self.app_manager.live2d_model, 'set_motion'):
                    self.app_manager.live2d_model.set_motion(motion_index)
                elif hasattr(self.app_manager.live2d_model, 'setMotion'):
                    self.app_manager.live2d_model.setMotion(motion_index, 0)  # 参数可能不同
                elif hasattr(self.app_manager.live2d_model, 'play_motion'):
                    self.app_manager.live2d_model.play_motion(motion_index)
                else:
                    if self.logger:
                        self.logger.info(f">>> Live2D模型没有可用的动作设置方法，尝试设置动作: {motion_index}")
                    return False
                return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 设置Live2D动作失败: {e}")
            return False

    def play_singing_audio(self, audio_data, volume=1.0, loop=False, singing_motion="唱歌", lrc_content=""):
        """播放唱歌音频"""
        try:
            if self.logger:
                self.logger.info(">>> 开始播放唱歌音频")
            
            # 初始化LRC管理器（如果有歌词内容）
            if lrc_content and self.app_manager and hasattr(self.app_manager, 'subtitle_manager'):
                try:
                    if self.logger:
                        self.logger.info(f">>> 接收到LRC歌词内容长度: {len(lrc_content)} 字符")
                        self.logger.info(f">>> LRC歌词内容前200字符: {lrc_content[:200]}")
                    
                    self.lrc_manager = LRCManager(self.app_manager.subtitle_manager)
                    if self.lrc_manager.load_lrc_content(lrc_content):
                        if self.logger:
                            self.logger.info(">>> LRC歌词加载成功")
                    else:
                        if self.logger:
                            self.logger.warning(">>> LRC歌词加载失败")
                        self.lrc_manager = None
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 初始化LRC管理器失败: {e}")
                        self.logger.error(f">>> 错误详情: {traceback.format_exc()}")
                    self.lrc_manager = None
            else:
                if self.logger:
                    if not lrc_content:
                        self.logger.info(">>> 没有LRC歌词内容")
                    else:
                        self.logger.warning(">>> 字幕管理器不可用，无法初始化LRC管理器")
            
            # 转换音频格式
            converted_audio_data = self._convert_audio_format(audio_data)
            
            # 在后台线程中播放音频
            import threading
            self.audio_thread = threading.Thread(
                target=self._play_singing_audio,
                args=(converted_audio_data, volume, loop, singing_motion)
            )
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 播放唱歌音频失败: {e}")

    def _convert_audio_format(self, audio_data):
        """检测音频格式并转换为WAV格式用于播放"""
        try:
            # 首先尝试检测音频格式
            audio_stream = io.BytesIO(audio_data)
            
            # 检查文件头来判断格式
            header = audio_stream.read(12)
            audio_stream.seek(0)
            
            format_detected = "unknown"
            
            # WAV格式检测
            if header.startswith(b'RIFF') and b'WAVE' in header:
                format_detected = "wav"
                if self.logger:
                    self.logger.info(">>> 检测到WAV格式音频")
                return audio_data  # WAV格式直接返回
            
            # MP3格式检测
            elif header.startswith(b'\xFF\xFB') or header.startswith(b'\xFF\xF3') or header.startswith(b'\xFF\xF2'):
                format_detected = "mp3"
            # FLAC格式检测
            elif header.startswith(b'fLaC'):
                format_detected = "flac"
            # OGG格式检测
            elif header.startswith(b'OggS'):
                format_detected = "ogg"
            # M4A/AAC格式检测
            elif header.startswith(b'\x00\x00\x00') and len(header) >= 8:
                # 检查是否为M4A格式
                audio_stream.seek(4)
                if audio_stream.read(4) == b'ftyp':
                    format_detected = "m4a"
            
            if format_detected == "unknown":
                # 如果无法检测格式，假设是WAV格式
                if self.logger:
                    self.logger.info(">>> 无法检测音频格式，假设为WAV格式")
                return audio_data
            
            # 需要转换格式
            if self.logger:
                self.logger.info(f">>> 检测到{format_detected.upper()}格式音频，开始转换为WAV")
            
            try:
                # 尝试使用pydub进行格式转换
                from pydub import AudioSegment
                
                # 根据格式加载音频
                if format_detected == "mp3":
                    audio = AudioSegment.from_mp3(audio_stream)
                elif format_detected == "flac":
                    audio = AudioSegment.from_file(audio_stream, format="flac")
                elif format_detected == "ogg":
                    audio = AudioSegment.from_file(audio_stream, format="ogg")
                elif format_detected == "m4a":
                    audio = AudioSegment.from_file(audio_stream, format="m4a")
                else:
                    # 其他格式尝试自动检测
                    audio = AudioSegment.from_file(audio_stream)
                
                # 转换为WAV格式
                wav_buffer = io.BytesIO()
                audio.export(wav_buffer, format='wav')
                converted_data = wav_buffer.getvalue()
                
                if self.logger:
                    self.logger.info(f">>> 音频格式转换完成: {format_detected.upper()} -> WAV ({len(converted_data)} bytes)")
                
                return converted_data
                
            except ImportError:
                # 如果没有pydub，使用ffmpeg进行转换
                if self.logger:
                    self.logger.info(">>> pydub不可用，尝试使用ffmpeg转换")
                
                # 保存原始音频到临时文件
                with tempfile.NamedTemporaryFile(suffix=f'.{format_detected}', delete=False) as temp_input:
                    temp_input.write(audio_data)
                    input_path = temp_input.name
                
                # 输出WAV文件路径
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                    output_path = temp_output.name
                
                try:
                    # 使用ffmpeg进行转换
                    import subprocess
                    cmd = [
                        'ffmpeg', '-y', '-i', input_path, 
                        '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                        output_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # 读取转换后的WAV文件
                        with open(output_path, 'rb') as f:
                            converted_data = f.read()
                        
                        if self.logger:
                            self.logger.info(f">>> ffmpeg转换完成: {format_detected.upper()} -> WAV ({len(converted_data)} bytes)")
                        
                        return converted_data
                    else:
                        if self.logger:
                            self.logger.error(f">>> FFMPEG_CONVERT_ERROR: {result.stderr}")
                        raise Exception(f"ffmpeg转换失败: {result.stderr}")
                        
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                        
            except Exception as convert_error:
                if self.logger:
                    self.logger.error(f">>> 格式转换失败: {convert_error}")
                
                # 如果转换失败，尝试直接播放原始数据
                if self.logger:
                    self.logger.info(">>> 格式转换失败，尝试直接播放原始数据")
                return audio_data
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 音频格式检测失败: {e}")
            return audio_data  # 返回原始数据

    def _play_singing_audio(self, audio_data, volume, loop, singing_motion):
        """播放唱歌音频并触发Live2D动作"""
        try:
            if self.logger:
                self.logger.info(">>> 开始播放唱歌音频")
            
            # 解析WAV音频数据
            with io.BytesIO(audio_data) as wav_io:
                with wave.open(wav_io, 'rb') as wave_file:
                    sample_width = wave_file.getsampwidth()
                    channels = wave_file.getnchannels()
                    framerate = wave_file.getframerate()
                    num_frames = wave_file.getnframes()
                    frames = wave_file.readframes(num_frames)
            
            if self.logger:
                self.logger.info(f">>> WAV解析完成: {channels}声道, {framerate}Hz, {num_frames}帧")
            
            # 转换为numpy数组并应用音量
            dtype = np.int16 if sample_width == 2 else np.int8
            audio_array = np.frombuffer(frames, dtype=dtype)
            
            # 确保正确的数据类型转换
            if sample_width == 2:
                audio_float = audio_array.astype(np.float32) / 32767.0
            else:
                audio_float = audio_array.astype(np.float32) / 127.0
            
            # 重塑为多声道（必须在其他操作之前）
            if channels > 1:
                audio_float = audio_float.reshape(-1, channels)
            
            # 应用音量并确保在有效范围内，避免失真和噪音
            audio_float *= volume
            audio_float = np.clip(audio_float, -0.8, 0.8)  # 限制在更安全的范围内
            
            # 添加淡入淡出效果减少噪音
            fade_samples = int(framerate * 0.01)  # 10ms淡入淡出
            if len(audio_float) > 2 * fade_samples:
                # 淡入
                fade_in = np.linspace(0, 1, fade_samples)
                if channels > 1:
                    fade_in = fade_in.reshape(-1, 1)  # 为多声道调整形状
                audio_float[:fade_samples] *= fade_in
                
                # 淡出
                fade_out = np.linspace(1, 0, fade_samples)
                if channels > 1:
                    fade_out = fade_out.reshape(-1, 1)  # 为多声道调整形状
                audio_float[-fade_samples:] *= fade_out
            
            if self.logger:
                self.logger.info(f">>> 音频数据处理完成，应用音量: {volume}, 数据范围: [{audio_float.min():.3f}, {audio_float.max():.3f}]")
            
            # 触发Live2D唱歌动作
            singing_motion_index = self._get_motion_index_by_name(singing_motion)
            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                if self.logger:
                    self.logger.info(f">>> 触发Live2D唱歌动作: {singing_motion} (索引: {singing_motion_index})")
                # 这里可以调用Live2D模型的动作触发方法
            
            # 启动LRC歌词播放（如果有）
            if self.lrc_manager:
                try:
                    self.lrc_manager.start_playback()
                    if self.logger:
                        self.logger.info(">>> LRC歌词播放已启动")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 启动LRC歌词播放失败: {e}")
            
            # 检查音频设备可用性并选择最佳设备
            try:
                devices = sd.query_devices()
                output_devices = [d for d in devices if d['max_output_channels'] > 0]
                if not output_devices:
                    raise Exception("没有可用的音频输出设备")
                
                # 从配置文件中获取音频设备设置
                config_audio = {}
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        config_audio = config_data.get('audio', {})
                except Exception as config_e:
                    if self.logger:
                        self.logger.warning(f">>> 读取音频配置失败，使用默认设置: {config_e}")
                
                # 获取配置中的音频设备索引和音量
                configured_device_index = config_audio.get('device_index', None)
                configured_volume = config_audio.get('volume', 1.0)
                
                # 应用配置的音量
                volume *= configured_volume
                
                # 选择音频设备
                selected_device = None
                
                if configured_device_index is not None:
                    # 验证配置的设备是否可用
                    try:
                        if 0 <= configured_device_index < len(devices):
                            device = devices[configured_device_index]
                            if device['max_output_channels'] > 0:
                                selected_device = configured_device_index
                                if self.logger:
                                    self.logger.info(f">>> 使用配置的音频设备: [{configured_device_index}] {device['name']}")
                            else:
                                if self.logger:
                                    self.logger.warning(f">>> 配置的设备不支持音频输出: [{configured_device_index}] {device['name']}")
                        else:
                            if self.logger:
                                self.logger.warning(f">>> 配置的设备索引无效: {configured_device_index}")
                    except Exception as device_e:
                        if self.logger:
                            self.logger.warning(f">>> 验证配置设备失败: {device_e}")
                
                # 如果配置的设备无效，选择最佳设备
                if selected_device is None:
                    if self.logger:
                        self.logger.info(">>> 配置设备无效，自动选择最佳音频设备...")
                    
                    # 选择支持当前采样率且延迟较低的设备
                    best_device = None
                    min_latency = float('inf')
                    target_sample_rate = framerate
                    
                    for i, device in enumerate(devices):
                        if device['max_output_channels'] > 0:
                            # 检查设备是否支持目标采样率
                            device_sample_rate = device.get('default_samplerate', 44100)
                            if abs(device_sample_rate - target_sample_rate) <= 1000:  # 允许1kHz误差
                                latency = device.get('default_low_output_latency', device.get('default_high_output_latency', 0.1))
                                if latency < min_latency:
                                    min_latency = latency
                                    best_device = i
                    
                    # 如果没找到匹配的设备，使用默认设备
                    if best_device is None:
                        # 重新寻找，优先选择44100Hz或48000Hz的设备
                        for i, device in enumerate(devices):
                            if device['max_output_channels'] > 0:
                                device_sample_rate = device.get('default_samplerate', 44100)
                                if device_sample_rate in [44100, 48000]:
                                    best_device = i
                                    break
                    
                    selected_device = best_device
                
                # 应用选择的设备
                if selected_device is not None:
                    try:
                        sd.default.device[1] = selected_device
                        if self.logger:
                            device_name = devices[selected_device]['name']
                            self.logger.info(f">>> 设置音频输出设备: [{selected_device}] {device_name}")
                    except:
                        # 如果设置失败，使用系统默认
                        if self.logger:
                            self.logger.warning(">>> 设备选择失败，使用系统默认设备")
                
                if self.logger:
                    self.logger.info(f">>> 找到 {len(output_devices)} 个音频输出设备")
            except Exception as e:
                if self.logger:
                    self.logger.error(f">>> 音频设备检查失败: {e}")
                
                # 检查是否是严重的音频驱动错误
                error_str = str(e)
                critical_errors = [
                    "PaErrorCode -9999",  # Windows WDM-KS错误
                    "Unanticipated host error",
                    "DeviceIoControl",
                    "WdmSyncIoctl"
                ]
                
                is_critical_error = any(error in error_str for error in critical_errors)
                
                if is_critical_error:
                    if self.logger:
                        self.logger.error(">>> 检测到严重音频设备错误，退出播放")
                    
                    # 停止LRC歌词播放
                    if self.lrc_manager:
                        try:
                            self.lrc_manager.stop_playback()
                            if self.logger:
                                self.logger.info(">>> LRC歌词播放已停止")
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f">>> 停止LRC歌词播放失败: {e}")
                    
                    # 清理字幕显示
                    if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                        try:
                            self.app_manager.subtitle_manager.clear_text()
                            if self.logger:
                                self.logger.info(">>> 字幕已清理")
                        except Exception as e:
                            if self.logger:
                                self.logger.warning(f">>> 清理字幕时出错: {e}")
                    
                    # 停止Live2D动作
                    if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                        try:
                            self._set_live2d_motion(0)  # 设置为默认动作
                            if self.logger:
                                self.logger.info(">>> Live2D动作已重置为默认状态")
                        except Exception as e:
                            if self.logger:
                                self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
                    
                    # 重置播放状态
                    self._stop_singing = True
                    self.current_audio_stream = None
                    
                    if self.logger:
                        self.logger.info(">>> 播放状态已重置，退出音频播放")
                    return
                
                # 回退到系统播放器
                self._play_audio_fallback(audio_data, volume, loop, singing_motion)
                return
            
            # 非阻塞播放音频
            if loop:
                # 循环播放 - 在后台线程中处理
                if self.logger:
                    self.logger.info(">>> 开始循环播放音频")
                
                def loop_playback():
                    current_stream = None
                    try:
                        while not self._stop_singing:
                            try:
                                # 开始播放
                                current_stream = sd.play(audio_float, samplerate=framerate, blocking=False)
                                self.current_audio_stream = current_stream
                                
                                if self.logger:
                                    self.logger.info(">>> 音频流已启动")
                                
                                # 等待播放完成
                                start_time = time.time()
                                timeout = 30.0  # 30秒超时
                                
                                while not self._stop_singing and time.time() - start_time < timeout:
                                    if current_stream and hasattr(current_stream, 'active'):
                                        if not current_stream.active:
                                            break
                                    else:
                                        # 尝试使用sd.wait()
                                        try:
                                            sd.wait(timeout=0.1)
                                            if not sd.get_stream() or not sd.get_stream().active:
                                                break
                                        except:
                                            break
                                    time.sleep(0.01)
                                
                                # 停止当前流
                                if current_stream:
                                    try:
                                        current_stream.stop()
                                        current_stream.close()
                                    except:
                                        pass
                                
                                if self._stop_singing:
                                    if self.logger:
                                        self.logger.info(">>> 收到停止信号，结束循环播放")
                                    break
                                    
                            except Exception as stream_error:
                                if self.logger:
                                    self.logger.error(f">>> 音频流播放异常: {stream_error}")
                                
                                # 检查是否是严重的音频驱动错误
                                error_str = str(stream_error)
                                critical_errors = [
                                    "PaErrorCode -9999",  # Windows WDM-KS错误
                                    "Unanticipated host error",
                                    "DeviceIoControl",
                                    "WdmSyncIoctl"
                                ]
                                
                                is_critical_error = any(error in error_str for error in critical_errors)
                                
                                if is_critical_error:
                                    if self.logger:
                                        self.logger.error(">>> 循环播放中检测到严重音频驱动错误，退出播放")
                                    
                                    # 清理字幕显示
                                    if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                                        try:
                                            self.app_manager.subtitle_manager.clear_text()
                                            if self.logger:
                                                self.logger.info(">>> 字幕已清理")
                                        except Exception as e:
                                            if self.logger:
                                                self.logger.warning(f">>> 清理字幕时出错: {e}")
                                    
                                    # 停止LRC歌词播放
                                    if self.lrc_manager:
                                        try:
                                            self.lrc_manager.stop_playback()
                                            if self.logger:
                                                self.logger.info(">>> LRC歌词播放已停止")
                                        except Exception as e:
                                            if self.logger:
                                                self.logger.error(f">>> 停止LRC歌词播放失败: {e}")
                                    
                                    # 停止Live2D动作
                                    if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                        try:
                                            self._set_live2d_motion(0)  # 设置为默认动作
                                            if self.logger:
                                                self.logger.info(">>> Live2D动作已重置为默认状态")
                                        except Exception as e:
                                            if self.logger:
                                                self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
                                    
                                    self._stop_singing = True  # 强制停止循环
                                    break
                                
                                time.sleep(0.1)  # 短暂延迟后重试
                                
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f">>> 循环播放异常: {e}")
                    finally:
                        # 清理音频流
                        if current_stream:
                            try:
                                current_stream.stop()
                                current_stream.close()
                            except:
                                pass
                        self.current_audio_stream = None
                        
                        # 播放结束后清理字幕、停止唱歌动作和LRC歌词
                        # 清理字幕显示
                        if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                            try:
                                self.app_manager.subtitle_manager.clear_text()
                                if self.logger:
                                    self.logger.info(">>> 字幕已清理")
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(f">>> 清理字幕时出错: {e}")
                        
                        # 停止Live2D动作
                        if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                            try:
                                self._set_live2d_motion(0)  # 设置为默认动作
                                if self.logger:
                                    self.logger.info(">>> Live2D动作已重置为默认状态")
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
                        
                        # 停止LRC歌词播放
                        if self.lrc_manager:
                            try:
                                self.lrc_manager.stop_playback()
                                if self.logger:
                                    self.logger.info(">>> LRC歌词播放已停止")
                            except Exception as e:
                                if self.logger:
                                    self.logger.error(f">>> 停止LRC歌词播放失败: {e}")
                        
                        if self.logger:
                            self.logger.info(">>> 循环播放完成")
                
                import threading
                loop_thread = threading.Thread(target=loop_playback)
                loop_thread.daemon = True
                loop_thread.start()
            else:
                # 单次播放 - 非阻塞
                if self.logger:
                    self.logger.info(">>> 开始单次播放音频")
                
                try:
                    # 开始播放，使用更安全的参数
                    current_stream = sd.play(audio_float, samplerate=framerate, blocking=False)
                    self.current_audio_stream = current_stream
                    
                    if self.logger:
                        self.logger.info(">>> 音频流已启动")
                    
                    # 在后台线程中等待播放完成并停止动作
                    def wait_and_stop():
                        try:
                            # 计算音频实际播放时长
                            audio_duration = len(audio_float) / framerate
                            if channels > 1:
                                audio_duration = len(audio_float) / framerate  # 已经是正确的长度
                            
                            if self.logger:
                                self.logger.info(f">>> 音频时长: {audio_duration:.2f}秒, 采样率: {framerate}Hz, 声道: {channels}")
                            
                            start_time = time.time()
                            # 设置超时为音频时长的1.5倍，最少10秒，最多5分钟
                            timeout = max(10.0, min(audio_duration * 1.5, 300.0))
                            
                            if self.logger:
                                self.logger.info(f">>> 开始等待音频播放完成，超时时间: {timeout:.2f}秒")
                            
                            while not self._stop_singing and time.time() - start_time < timeout:
                                try:
                                    # 首先检查流是否还活跃
                                    if current_stream and hasattr(current_stream, 'active'):
                                        if not current_stream.active:
                                            if self.logger:
                                                self.logger.info(">>> 检测到音频流已停止")
                                            break
                                    
                                    # 尝试获取当前流状态
                                    try:
                                        active_stream = sd.get_stream()
                                        if not active_stream or not active_stream.active:
                                            if self.logger:
                                                self.logger.info(">>> 通过sd.get_stream()检测到音频播放完成")
                                            break
                                    except:
                                        # 如果获取不到流，检查时间是否超过预期播放时间
                                        elapsed = time.time() - start_time
                                        if elapsed >= audio_duration * 0.9:  # 播放了90%以上认为完成
                                            if self.logger:
                                                self.logger.info(f">>> 基于时间判断音频播放完成 ({elapsed:.2f}s >= {audio_duration * 0.9:.2f}s)")
                                            break
                                
                                except Exception as wait_error:
                                    if self.logger:
                                        self.logger.warning(f">>> 检查音频流状态时出错: {wait_error}")
                                    # 如果检查状态失败，基于时间判断
                                    elapsed = time.time() - start_time
                                    if elapsed >= audio_duration * 0.8:  # 播放了80%以上可能完成
                                        if self.logger:
                                            self.logger.info(f">>> 状态检查失败，基于时间判断播放可能完成 ({elapsed:.2f}s >= {audio_duration * 0.8:.2f}s)")
                                        break
                                
                                time.sleep(0.1)  # 短暂延迟后重试
                            
                            elapsed_time = time.time() - start_time
                            if self.logger:
                                if elapsed_time >= timeout:
                                    self.logger.warning(f">>> 音频播放超时 ({elapsed_time:.2f}s >= {timeout:.2f}s)")
                                else:
                                    self.logger.info(f">>> 音频播放完成，实际播放时间: {elapsed_time:.2f}s")
                            
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f">>> 等待播放完成异常: {e}")
                        finally:
                            # 清理音频流
                            if current_stream:
                                try:
                                    current_stream.stop()
                                    current_stream.close()
                                except:
                                    pass
                            self.current_audio_stream = None
                            
                            # 播放结束后清理字幕、停止唱歌动作和LRC歌词
                            # 清理字幕显示
                            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                                try:
                                    self.app_manager.subtitle_manager.clear_text()
                                    if self.logger:
                                        self.logger.info(">>> 字幕已清理")
                                except Exception as e:
                                    if self.logger:
                                        self.logger.warning(f">>> 清理字幕时出错: {e}")
                            
                            # 停止Live2D动作
                            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                try:
                                    self._set_live2d_motion(0)  # 设置为默认动作
                                    if self.logger:
                                        self.logger.info(">>> Live2D动作已重置为默认状态")
                                except Exception as e:
                                    if self.logger:
                                        self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
                            
                            # 停止LRC歌词播放
                            if self.lrc_manager:
                                try:
                                    self.lrc_manager.stop_playback()
                                    if self.logger:
                                        self.logger.info(">>> LRC歌词播放已停止")
                                except Exception as e:
                                    if self.logger:
                                        self.logger.error(f">>> 停止LRC歌词播放失败: {e}")
                            
                            if self.logger:
                                self.logger.info(">>> 单次播放完成")
                    
                    import threading
                    stop_thread = threading.Thread(target=wait_and_stop)
                    stop_thread.daemon = True
                    stop_thread.start()
                    
                except Exception as play_error:
                    if self.logger:
                        self.logger.error(f">>> sounddevice播放失败: {play_error}")
                    
                    # 检查是否是严重的音频驱动错误，直接退出播放状态
                    error_str = str(play_error)
                    critical_errors = [
                        "PaErrorCode -9999",  # Windows WDM-KS错误
                        "Unanticipated host error",
                        "DeviceIoControl",
                        "WdmSyncIoctl"
                    ]
                    
                    is_critical_error = any(error in error_str for error in critical_errors)
                    
                    if is_critical_error:
                        if self.logger:
                            self.logger.error(">>> 检测到严重音频驱动错误，直接退出播放状态")
                        
                        # 停止LRC歌词播放
                        if self.lrc_manager:
                            try:
                                self.lrc_manager.stop_playback()
                                if self.logger:
                                    self.logger.info(">>> LRC歌词播放已停止")
                            except Exception as e:
                                if self.logger:
                                    self.logger.error(f">>> 停止LRC歌词播放失败: {e}")
                        
                        # 清理字幕显示
                        if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                            try:
                                self.app_manager.subtitle_manager.clear_text()
                                if self.logger:
                                    self.logger.info(">>> 字幕已清理")
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(f">>> 清理字幕时出错: {e}")
                        
                        # 停止Live2D动作
                        if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                            try:
                                self._set_live2d_motion(0)  # 设置为默认动作
                                if self.logger:
                                    self.logger.info(">>> Live2D动作已重置为默认状态")
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
                        
                        # 重置播放状态
                        self._stop_singing = True
                        self.current_audio_stream = None
                        
                        if self.logger:
                            self.logger.info(">>> 播放状态已重置，退出音频播放")
                        return  # 直接退出，不进行任何重试
                    
                    # 如果是采样率错误，尝试使用默认设备和常见采样率
                    if "Invalid sample rate" in error_str or "PaErrorCode -9997" in error_str:
                        if self.logger:
                            self.logger.info(">>> 尝试使用系统默认设备和标准采样率...")
                        
                        try:
                            # 重置为系统默认设备
                            sd.default.reset()
                            
                            # 尝试48000Hz采样率
                            if framerate != 48000:
                                # 简单重采样
                                ratio = 48000 / framerate
                                new_length = int(len(audio_float) * ratio)
                                indices = np.linspace(0, len(audio_float) - 1, new_length)
                                if channels > 1:
                                    resampled_audio = np.zeros((new_length, channels))
                                    for ch in range(channels):
                                        resampled_audio[:, ch] = np.interp(indices, np.arange(len(audio_float)), audio_float[:, ch])
                                else:
                                    resampled_audio = np.interp(indices, np.arange(len(audio_float)), audio_float)
                                
                                current_stream = sd.play(resampled_audio, samplerate=48000, blocking=False)
                                if self.logger:
                                    self.logger.info(">>> 使用48000Hz采样率播放成功")
                            else:
                                current_stream = sd.play(audio_float, samplerate=framerate, blocking=False)
                                if self.logger:
                                    self.logger.info(">>> 使用默认设备播放成功")
                                    
                        except Exception as retry_error:
                            if self.logger:
                                self.logger.error(f">>> 重试播放也失败: {retry_error}")
                            # 最终回退到系统播放器
                            self._play_audio_fallback(audio_data, volume, loop, singing_motion)
                    else:
                        # 其他错误，直接回退到系统播放器
                        self._play_audio_fallback(audio_data, volume, loop, singing_motion)
            
        except ImportError as e:
            if self.logger:
                self.logger.error(f">>> 缺少音频播放依赖: {e}")
            # 回退到简单播放
            self._play_audio_fallback(audio_data, volume, loop, singing_motion)
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 播放唱歌音频失败: {e}")

    def _play_audio_fallback(self, audio_data, volume, loop, singing_motion):
        """音频播放的回退方法"""
        try:
            # 从配置文件中获取音频设置
            config_audio = {}
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    config_audio = config_data.get('audio', {})
            except Exception as config_e:
                if self.logger:
                    self.logger.warning(f">>> 读取音频配置失败（回退播放），使用默认设置: {config_e}")
            
            # 应用配置的音量
            configured_volume = config_audio.get('volume', 1.0)
            volume *= configured_volume
            
            # 保存为临时文件并使用系统播放器
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # 触发Live2D动作
            singing_motion_index = self._get_motion_index_by_name(singing_motion)
            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                # 这里可以调用Live2D模型的动作触发方法
                pass
            
            # 在后台线程中播放音频
            def play_audio_background():
                try:
                    if sys.platform == 'win32':
                        import winsound
                        
                        # 获取音频时长（估算）
                        try:
                            with wave.open(temp_path, 'rb') as wav_file:
                                frames = wav_file.getnframes()
                                rate = wav_file.getframerate()
                                duration = frames / float(rate) if rate > 0 else 0
                        except:
                            duration = 0
                        
                        if loop:
                            # 循环播放 - 使用定时器方式避免阻塞
                            def play_loop():
                                try:
                                    winsound.PlaySound(temp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    # 等待播放完成后再重新播放
                                    if duration > 0:
                                        time.sleep(duration)
                                        # 检查是否还有循环播放的请求
                                        if not self._stop_singing:
                                            play_loop()
                                        else:
                                            # 停止Live2D动作
                                            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                                # 这里可以调用Live2D的停止方法
                                                pass
                                except Exception as e:
                                    if self.logger:
                                        self.logger.error(f">>> 循环播放异常: {e}")
                        
                            import threading
                            loop_thread = threading.Thread(target=play_loop)
                            loop_thread.daemon = True
                            loop_thread.start()
                        else:
                            # 单次播放
                            winsound.PlaySound(temp_path, winsound.SND_FILENAME)
                            
                            # 等待播放完成或超时
                            if duration > 0:
                                timeout = min(duration + 1.0, 30.0)  # 最长等待30秒
                                time.sleep(min(duration, timeout))
                            
                            # 停止Live2D动作
                            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                # 这里可以调用Live2D的停止方法
                                pass
                    else:
                        # Linux/Mac
                        import subprocess
                        if loop:
                            # 循环播放
                            def play_loop_unix():
                                while not self._stop_singing:
                                    try:
                                        cmd = ['aplay', temp_path]
                                        subprocess.run(cmd, timeout=10)
                                        time.sleep(0.1)  # 短暂延迟
                                    except subprocess.TimeoutExpired:
                                        continue
                                    except Exception as e:
                                        if self.logger:
                                            self.logger.error(f">>> Unix循环播放异常: {e}")
                                        break
                                # 停止Live2D动作
                                if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                    # 这里可以调用Live2D的停止方法
                                    pass
                        
                            import threading
                            loop_thread = threading.Thread(target=play_loop_unix)
                            loop_thread.daemon = True
                            loop_thread.start()
                        else:
                            # 单次播放
                            cmd = ['aplay', temp_path]
                            subprocess.run(cmd, timeout=30)  # 30秒超时
                            
                            # 停止Live2D动作
                            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                                # 这里可以调用Live2D的停止方法
                                pass
                
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 系统播放异常: {e}")
                    # 确保Live2D动作停止
                    if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                        # 这里可以调用Live2D的停止方法
                        pass
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            
            import threading
            play_thread = threading.Thread(target=play_audio_background)
            play_thread.daemon = True
            play_thread.start()
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 回退播放失败: {e}")
            # 确保Live2D动作停止
            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                # 这里可以调用Live2D的停止方法
                pass

    def show_action_buttons(self):
        """显示动作按钮窗口"""
        if self.action_buttons_window:
            self.action_buttons_window.show()

    def hide_action_buttons(self):
        """隐藏动作按钮窗口"""
        if self.action_buttons_window:
            self.action_buttons_window.hide()

    def show_subtitle(self, text, source="unknown"):
        """显示字幕
        
        Args:
            text: 要显示的字幕文本
            source: 字幕来源 (dialogue, singing, etc.)
        """
        try:
            # 先移除深度思考内容，仅保留可发表内容
            visible_text = self._sanitize_visible_text(text)

            # 在展示前进行内容过滤（基于可见文本）— 使用“快速模式”（仅关键词），避免阻塞
            try:
                from content_filter import check as filter_check
                cfg_path = getattr(self, 'config_path', 'config.json') if hasattr(self, 'config_path') else 'config.json'
                cfg = {}
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except Exception:
                    cfg = {}
                # 构造快速过滤配置：禁用 LLM / 易盾
                fast_cfg = dict(cfg)
                fast_filters = dict((fast_cfg.get('filters') or {}))
                llm_cfg = dict((fast_filters.get('llm') or {}))
                yidun_cfg = dict((fast_filters.get('yidun') or {}))
                llm_cfg['enabled'] = False
                yidun_cfg['enabled'] = False
                fast_filters['llm'] = llm_cfg
                fast_filters['yidun'] = yidun_cfg
                fast_cfg['filters'] = fast_filters
                is_blocked, final_text, reason, repl = filter_check(visible_text, fast_cfg)
                if is_blocked:
                    if self.logger:
                        self.logger.info(f">>> 字幕/语音内容被过滤: {reason}")
                    # 显示替换文本；原始被屏蔽文本不提交给TTS
                    visible_text = final_text
                    # 可选：播放语音提示（安全且不含敏感内容）
                    try:
                        if not cfg:
                            with open(cfg_path, 'r', encoding='utf-8') as f:
                                cfg = json.load(f)
                        voice_cfg = cfg.get('filters', {}).get('voice', {})
                        if voice_cfg.get('enabled') and voice_cfg.get('text'):
                            if self.app_manager and hasattr(self.app_manager, 'tts_client') and self.app_manager.tts_client:
                                try:
                                    coro = self.app_manager.tts_client.speak(voice_cfg.get('text'))
                                    if asyncio.iscoroutine(coro):
                                        asyncio.create_task(coro)
                                except Exception as te:
                                    if self.logger:
                                        self.logger.warning(f">>> 播放过滤语音提示失败: {te}")
                    except Exception:
                        pass
            except Exception:
                # 过滤流程失败时不影响字幕正常显示
                pass

            if self.logger:
                # 为歌词显示完整内容，其他内容截断显示
                if source == "lyrics":
                    self.logger.info(f">>> 显示字幕: {source} - 完整歌词内容:\n{visible_text}")
                else:
                    self.logger.info(f">>> 显示字幕: {source} - {visible_text[:50]}...")
            
            # 检查字幕管理器是否存在
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                # 根据来源决定是否流式显示
                stream = source == "dialogue"  # 台词使用流式显示，唱歌使用完整显示
                # 仅展示经过清洗后的可见文本
                self.app_manager.subtitle_manager.add_text(visible_text, stream=stream)
                
                if self.logger:
                    self.logger.info(f">>> 字幕已发送到管理器: stream={stream}")
            else:
                if self.logger:
                    self.logger.warning(">>> 字幕管理器不可用，无法显示字幕")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 显示字幕失败: {e}")

    def update_subtitle_display_settings(self, monitor_index=None, position=None, position_x=None, position_y=None, offset_x=None, offset_y=None):
        """更新字幕显示设置
        
        Args:
            monitor_index: 目标显示器索引
            position: 显示位置
            position_x: X坐标
            position_y: Y坐标
            offset_x: X轴偏移量
            offset_y: Y轴偏移量
        """
        try:
            if self.logger:
                self.logger.info(f">>> 更新字幕显示设置: monitor={monitor_index}, position={position}, coords=({position_x}, {position_y}), offset=({offset_x}, {offset_y})")
            
            # 检查字幕管理器是否存在
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                # 调用字幕管理器的更新方法
                self.app_manager.subtitle_manager.update_display_settings(
                    monitor_index=monitor_index,
                    position=position,
                    position_x=position_x,
                    position_y=position_y,
                    offset_x=offset_x,
                    offset_y=offset_y
                )
                
                if self.logger:
                    self.logger.info(">>> 字幕显示设置已更新")
            else:
                if self.logger:
                    self.logger.warning(">>> 字幕管理器不可用，无法更新显示设置")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 更新字幕显示设置失败: {e}")
    
    def get_subtitle_monitor_info(self):
        """获取字幕管理器的显示器信息
        
        Returns:
            list: 显示器信息列表
        """
        try:
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                return self.app_manager.subtitle_manager.get_monitor_info()
            else:
                if self.logger:
                    self.logger.warning(">>> 字幕管理器不可用，无法获取显示器信息")
                return []
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 获取显示器信息失败: {e}")
            return []

    def stop_audio_playback(self):
        """停止音频播放"""
        try:
            if self.logger:
                self.logger.info(">>> 停止音频播放... [ 进行中 ]")
            
            # 设置停止标志
            self._stop_singing = True
            
            # 停止当前的音频流
            if self.current_audio_stream:
                try:
                    self.current_audio_stream.stop()
                    self.current_audio_stream.close()
                    self.current_audio_stream = None
                    if self.logger:
                        self.logger.info(">>> 当前音频流已停止")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 停止音频流时出错: {e}")
            
            # 等待音频线程结束
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join(timeout=2.0)
                if self.logger:
                    self.logger.info(">>> 音频播放线程已停止")
            
            # 清理音频线程引用
            self.audio_thread = None
            
            # 停止LRC歌词播放和清理字幕
            if self.lrc_manager:
                try:
                    self.lrc_manager.stop_playback()
                    if self.logger:
                        self.logger.info(">>> LRC歌词播放已停止")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 停止LRC歌词时出错: {e}")
            
            # 清理字幕显示
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                try:
                    self.app_manager.subtitle_manager.clear_text()
                    if self.logger:
                        self.logger.info(">>> 字幕已清理")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 清理字幕时出错: {e}")
            
            # 停止Live2D动作（返回默认状态）
            if self.app_manager and hasattr(self.app_manager, 'live2d_model') and self.app_manager.live2d_model:
                try:
                    self._set_live2d_motion(0)  # 设置为默认动作
                    if self.logger:
                        self.logger.info(">>> Live2D动作已重置为默认状态")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 重置Live2D动作时出错: {e}")
            
            if self.logger:
                self.logger.info(">>> 音频播放... [ 已停止 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 停止音频播放失败: {e}")

    def reset_action_buttons(self):
        """重置动作按钮状态"""
        try:
            if self.logger:
                self.logger.info(">>> 重置动作按钮状态")
            
            # 这里可以添加重置动作按钮状态的逻辑
            # 例如：取消所有按钮的高亮状态，恢复默认状态等
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 重置动作按钮失败: {e}")


class QtAsyncManager:
    """Qt和asyncio集成管理器"""
    
    def __init__(self):
        self.qt_app = None
        self.event_loop = None
        self.service = None
        self.logger = logging.getLogger("qt_async")
        
    def setup_qt_application(self) -> 'QApplication|Any':
        """设置Qt应用程序"""
        try:
            # 检查是否已经有QApplication实例
            if QApplication.instance() is None:
                # 设置OpenGL格式（针对Live2D）
                format = QSurfaceFormat.defaultFormat()
                format.setSwapInterval(0)  # 禁用垂直同步
                QSurfaceFormat.setDefaultFormat(format)
                
                # 创建QApplication
                self.qt_app = QApplication(sys.argv)
                self.qt_app.setQuitOnLastWindowClosed(False)  # 防止窗口关闭时退出
                self.logger.info(">>> Qt应用程序... [ 已创建 ]")
            else:
                self.qt_app = QApplication.instance()
                self.logger.info(">>> 使用现有的Qt应用程序实例")
            
            return self.qt_app
            
        except Exception as e:
            self.logger.error(f">>> 设置Qt应用程序失败: {e}")
            raise
    
    def setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        def signal_handler(sig, frame):
            self.logger.info(f">>> 收到信号 {sig}")
            if self.service:
                self.service.request_shutdown()
            if self.qt_app:
                self.qt_app.quit()
        
        # 设置优雅关闭信号
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
        
        # Windows特殊处理
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, signal_handler)
    
    async def run_with_qasync(self, config_path: str) -> None|int:
        """使用qasync运行"""
        try:
            # 创建Qt应用
            qt_app = self.setup_qt_application()
            
            # 设置qasync事件循环
            self.event_loop = qasync.QEventLoop(qt_app)
            asyncio.set_event_loop(self.event_loop)
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            # 创建服务
            self.service = PetService(config_path)
            
            # 使用事件循环运行服务
            async def main_task():
                try:
                    assert self.service is not None
                    await self.service.initialize()
                    await self.service.start()
                    return 0
                except KeyboardInterrupt:
                    self.logger.info(">>> 用户中断服务")
                    return 0
                except Exception as e:
                    self.logger.error(f">>> 服务运行失败: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return 1
            
            # 运行主任务
            with self.event_loop:
                exit_code = self.event_loop.run_until_complete(main_task())
            
            return exit_code
            
        except Exception as e:
            self.logger.error(f">>> qasync运行失败: {e}")
            return 1

def main() -> int|None:
    """主函数"""
    # 获取配置文件路径
    config_path = os.getenv("PET_CONFIG", "config.json")
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # 创建Qt异步管理器
    qt_manager = QtAsyncManager()
    
    try:
        # 使用qasync
        exit_code = asyncio.run(qt_manager.run_with_qasync(config_path))
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n>>> 用户中断启动")
        return 0
    except Exception as e:
        print(f">>> 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f">>> 程序异常退出: {e}")
        sys.exit(1)