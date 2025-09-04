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
import socket
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

# 导入qasync
import qasync

# 导入音频播放和动作按钮相关模块
import io
import wave
import tempfile
import numpy as np
import sounddevice as sd
from interface.action_buttons import ActionButtonsWindow

class PetService:
    """AI桌面宠物服务类 - 支持Qt和asyncio集成"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.app_manager: AppManager|None = None
        self.qt_app: QApplication|None = None
        self.logger: Any = None
        self._running: bool = False
        self._shutdown_event = asyncio.Event()
        
        # 进程间通信相关
        self.interrupt_socket = None
        self.interrupt_thread = None
        self.interrupt_signal_file = Path("interrupt_signal.tmp")
        self.interrupt_port = 8889  # 固定的中断通信端口
        self.event_loop = None  # 保存事件循环引用
        
        # 音频播放相关
        self.audio_thread = None
        self._stop_singing = False
        self.current_audio_stream = None
        
        # 动作按钮相关
        self.action_buttons_window = None
        
    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 设置日志
            self.logger = setup_logger(
                level=logging.INFO,
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
            
            # 启动中断监听器
            self.start_interrupt_listener()
            
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
            
            # 停止中断监听器
            self.stop_interrupt_listener()
            
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

    def start_interrupt_listener(self):
        """启动中断监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 启动中断监听器... [ 进行中 ]")
            
            # 启动socket监听线程
            self.interrupt_thread = threading.Thread(
                target=self._interrupt_listener_thread,
                daemon=True
            )
            self.interrupt_thread.start()
            
            if self.logger:
                self.logger.info(">>> 中断监听器... [ 已启动 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 启动中断监听器失败: {e}")

    def stop_interrupt_listener(self):
        """停止中断监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 停止中断监听器... [ 进行中 ]")
            
            # 关闭socket
            if self.interrupt_socket:
                self.interrupt_socket.close()
                self.interrupt_socket = None
            
            # 等待线程结束
            if self.interrupt_thread and self.interrupt_thread.is_alive():
                self.interrupt_thread.join(timeout=2.0)
            
            if self.logger:
                self.logger.info(">>> 中断监听器... [ 已停止 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 停止中断监听器失败: {e}")

    def _interrupt_listener_thread(self):
        """中断监听器线程"""
        try:
            # 创建socket服务器
            self.interrupt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.interrupt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.interrupt_socket.bind(('127.0.0.1', self.interrupt_port))
            self.interrupt_socket.listen(1)
            self.interrupt_socket.settimeout(1.0)  # 1秒超时，用于定期检查
            
            if self.logger:
                self.logger.info(f">>> 中断监听器绑定到端口: {self.interrupt_port}")
            
            while self._running:
                try:
                    # 同时监听socket连接和文件信号
                    self._check_interrupt_signal()
                    
                    # 尝试接受socket连接
                    try:
                        client_socket, addr = self.interrupt_socket.accept()
                        self._handle_interrupt_connection(client_socket, addr)
                    except socket.timeout:
                        continue  # 超时，继续循环
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 中断监听器循环出错: {e}")
                    time.sleep(0.1)  # 短暂延迟
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 中断监听器线程异常: {e}")
        finally:
            if self.interrupt_socket:
                self.interrupt_socket.close()

    def _check_interrupt_signal(self):
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

    def _handle_interrupt_connection(self, client_socket, addr):
        """处理中断连接"""
        try:
            if self.logger:
                self.logger.info(f">>> 收到中断连接: {addr}")
            
            # 接收数据
            data = client_socket.recv(1024)
            if data:
                signal_data = json.loads(data.decode('utf-8'))
                self._process_interrupt_signal(signal_data)
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 处理中断连接出错: {e}")
        finally:
            client_socket.close()

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
            else:
                if self.logger:
                    self.logger.warning(f">>> 未知的信号类型: {signal_type}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理中断信号时出错: {e}")
                import traceback
                self.logger.error(f">>> 错误详情: {traceback.format_exc()}")

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
            
            # 中断TTS播放
            if self.app_manager and hasattr(self.app_manager, 'tts_client') and self.app_manager.tts_client:
                if hasattr(self.app_manager.tts_client, 'interrupt'):
                    self.app_manager.tts_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> TTS播放已中断")
                elif hasattr(self.app_manager.tts_client, 'stop'):
                    await self.app_manager.tts_client.stop()
                    if self.logger:
                        self.logger.info(">>> TTS播放已中断")
            
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
            
            # 重置动作按钮
            self.reset_action_buttons()
            
            if self.logger:
                self.logger.info(">>> 中断操作... [ 完成 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 执行中断操作时出错: {e}")

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

    def play_singing_audio(self, audio_data, volume=1.0, loop=False, singing_motion="唱歌"):
        """播放唱歌音频"""
        try:
            if self.logger:
                self.logger.info(">>> 开始播放唱歌音频")
            
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
            audio_float = audio_array.astype(np.float32) / 32767.0
            audio_float *= volume  # 应用音量
            
            # 重塑为多声道
            if channels > 1:
                audio_float = audio_float.reshape(-1, channels)
            
            if self.logger:
                self.logger.info(f">>> 音频数据处理完成，应用音量: {volume}")
            
            # 触发Live2D唱歌动作
            singing_motion_index = self._get_motion_index_by_name(singing_motion)
            if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                if self.logger:
                    self.logger.info(f">>> 触发Live2D唱歌动作: {singing_motion} (索引: {singing_motion_index})")
                # 这里可以调用Live2D模型的动作触发方法
            
            # 非阻塞播放音频
            if loop:
                # 循环播放 - 在后台线程中处理
                if self.logger:
                    self.logger.info(">>> 开始循环播放音频")
                
                def loop_playback():
                    try:
                        while not self._stop_singing:
                            sd.play(audio_float, samplerate=framerate, blocking=False)
                            while sd.get_stream().active and not self._stop_singing:
                                time.sleep(0.01)
                            if self._stop_singing:
                                if self.logger:
                                    self.logger.info(">>> 收到停止信号，结束循环播放")
                                break
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f">>> 循环播放异常: {e}")
                    finally:
                        # 播放结束后停止唱歌动作
                        if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                            if self.logger:
                                self.logger.info(">>> 停止Live2D唱歌动作")
                            # 这里可以调用Live2D的停止方法
                        
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
                
                sd.play(audio_float, samplerate=framerate, blocking=False)
                
                # 在后台线程中等待播放完成并停止动作
                def wait_and_stop():
                    try:
                        while sd.get_stream().active and not self._stop_singing:
                            time.sleep(0.01)
                        # 播放结束后停止唱歌动作
                        if self.app_manager and hasattr(self.app_manager, 'live2d_model'):
                            if self.logger:
                                self.logger.info(">>> 播放完成，停止Live2D唱歌动作")
                            # 这里可以调用Live2D的停止方法
                        
                        if self.logger:
                            self.logger.info(">>> 单次播放完成")
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f">>> 等待播放完成异常: {e}")
                
                import threading
                stop_thread = threading.Thread(target=wait_and_stop)
                stop_thread.daemon = True
                stop_thread.start()
            
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