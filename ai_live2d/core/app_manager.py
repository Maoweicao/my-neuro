"""
应用管理器模块
负责初始化和协调所有模块
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Any, Optional

# 导入事件总线
from core.event_bus import EventBus

# 导入模块连接器
from core.module_connector import ModuleConnector

# 导入模型关闭代码
from models.live2d_model import dispose_live2d

logger = logging.getLogger("app_manager")

class AppManager:
    """
    应用管理器类
    
    负责协调和管理所有模块
    """
    
    def __init__(self, config_path="config.json"):
        """
        初始化应用管理器
        
        Args:
            config_path: 配置文件路径
        """
        logger.info("创建应用管理器... [ 进行中 ]")
        # 保存配置路径
        self.config_path = config_path
        
        # 初始化模块引用
        self.event_bus = None
        self.module_connector: 'ModuleConnector|None' = None
        self.live2d_model = None
        self.subtitle_manager = None
        self.user_input = None
        self.llm_client = None
        self.rag_system = None
        self.mcp_client = None
        self.memory_manager = None
        self.context_processor = None
        self.prompt_integrator = None
        self.auto_chat = None
        self.tts_client = None
        self.asr_client = None
        self.vision_client = None
        self.bilibili_listener = None
        
        # 核心状态管理 - 用于精确控制ASR开放时机
        self.llm_streaming = False      # LLM是否正在流式输出
        self.user_input_processing = False  # 是否正在处理用户输入
        
        # 应用状态
        self.is_running = False
        self.initialized = False
        
        # 异步任务管理
        self.tasks = set()
        self.shutdown_event = asyncio.Event()
        
        logger.info("创建应用管理器... [ 完成 ]")

    async def start(self):
        """启动应用"""
        try:
            if not self.initialized:
                await self.initialize()
            
            if self.is_running:
                logger.warning("- 应用已经在运行中")
                return

            await self._check_and_update_asr_status()
            self.is_running = True
            logger.info("启动应用管理器... [ 完成 ]")
        except Exception as e:
            logger.error(f"- 启动应用失败: {e}")
            self.is_running = False
            import traceback
            logger.error(traceback.format_exc())
            raise

    async def initialize(self):
        """异步初始化所有模块"""
        try:
            if self.initialized:
                logger.warning("- 应用管理器已经初始化")
                return
            
            logger.info("启动应用管理器... [ 进行中 ]")
            
            # 创建事件总线
            self.event_bus = EventBus()

            # 创建模块连接器
            self.module_connector = ModuleConnector(self.event_bus, self.config_path)
            
            # 初始化模块
            await self._init_module_components()
            
            # 注册事件处理器
            await self._register_event_handlers()
            
            # 设置模块间的回调关系
            await self._setup_module_callbacks()
            
            self.initialized = True
        
        except Exception as e:
            logger.error(f"- 初始化应用管理器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _init_module_components(self):
        """初始化模块组件"""
        try:
            logger.info("初始化模块组件... [ 进行中 ]")
            assert self.module_connector is not None
            modules = await asyncio.gather(
                self.module_connector._init_llm_module(),
                self.module_connector._init_asr_module(),
                self.module_connector._init_tts_module(),
                self.module_connector._init_live2d_module(),
                self.module_connector._init_subtitle_module(),
                self.module_connector._init_user_input_module(),
                self.module_connector._init_rag_module(),
                self.module_connector._init_mcp_module(),
                self.module_connector._init_memory_module(),
                self.module_connector._init_vision_module(),
                self.module_connector._init_auto_chat_module(),
                self.module_connector._init_bilibili_listener_module()
            )
            (self.llm_client, self.context_processor, self.prompt_integrator), *modules = modules
            self.asr_client, self.tts_client, self.live2d_model, *modules = modules
            self.subtitle_manager, self.user_input, self.rag_system, *modules = modules
            self.memory_manager, self.mcp_client, self.vision_client, *modules = modules
            self.auto_chat, self.bilibili_listener = modules
            
            logger.info("初始化模块组件... [ 完成 ]")
        except Exception as e:
            logger.error(f"- 初始化模块组件失败: {e}")
            raise
    
    async def _register_event_handlers(self):
        """注册事件处理函数"""
        try:
            logger.info("注册事件处理函数... [ 进行中 ]")
            
            # LLM相关事件 - 核心：用于状态管理
            if self.llm_client:
                await self.event_bus.subscribe("llm_streaming", self._on_llm_streaming)
                await self.event_bus.subscribe("llm_complete", self._on_llm_complete)
                await self.event_bus.subscribe("llm_error", self._on_llm_error)
                await self.event_bus.subscribe('prompt_sending', self._on_send_prompt)
            
            # TTS相关事件 - 核心：用于状态管理
            if self.tts_client:
                await self.event_bus.subscribe("tts_start", self._on_tts_start)
                await self.event_bus.subscribe("tts_end", self._on_tts_end)
                await self.event_bus.subscribe("tts_error", self._on_tts_error)
            
            # ASR相关事件
            if self.asr_client:
                await self.event_bus.subscribe("user_speaking", self._on_user_speaking)
                await self.event_bus.subscribe("speech_recognized", self._on_speech_recognized)

            # 用户输入框相关事件
            if self.user_input:
                await self.event_bus.subscribe("user_text_input", self.handle_user_input)

            # RAG相关事件
            if self.rag_system:
                await self.event_bus.subscribe("get_rag_output", self._on_get_rag_output)
            
            # 自动聊天相关事件
            if self.auto_chat:
                await self.event_bus.subscribe("auto_chat_request", self._on_auto_chat_request)
                await self.event_bus.subscribe("auto_chat_response", self._on_auto_chat_response)
            
            # B站直播相关事件
            if self.bilibili_listener:
                await self.event_bus.subscribe("bilibili_message", self._on_bilibili_message_event)
            
            # 应用控制事件
            await self.event_bus.subscribe("app_shutdown", self._on_app_shutdown)
            
            logger.info("注册事件处理函数... [ 完成 ]")
        except Exception as e:
            logger.error(f"- 注册事件处理失败: {e}")
            raise
    
    async def _setup_module_callbacks(self):
        """设置模块间的回调关系"""
        try:
            logger.info("设置模块间回调关系... [ 进行中 ]")
            # 设置TTS回调 - 用于嘴型同步等
            if self.tts_client:
                self.tts_client.set_callbacks(
                    on_audio_data=self._on_audio_data,
                    on_text_update=self._on_text_update
                )

            # 设置LLM回调 - 用于处理输出文本
            if self.llm_client:
                self.llm_client.set_callbacks(
                    on_llm_output=self._on_llm_output
                )
            
            logger.info("设置模块间回调关系... [ 完成 ]")
        except Exception as e:
            logger.error(f"- 设置模块间回调关系失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭应用"""
        try:
            logger.info("开始关闭应用... [ 进行中 ]")
            
            # 设置关闭标志
            self.is_running = False
            self.shutdown_event.set()
            
            # 停止各个组件
            await self._stop_components()
            
            # 取消所有任务
            await self._cancel_tasks()
            
            # 关闭事件总线
            if self.event_bus:
                await self.event_bus.shutdown()
            
            # 关闭Live2D引擎
            if self.live2d_model:
                dispose_live2d()
            
            logger.info("关闭应用... [ 完成 ]")
        except Exception as e:
            logger.error(f"- 关闭应用失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _stop_components(self):
        """停止各个组件"""
        try:
            # 停止自动聊天
            if self.auto_chat:
                await self.auto_chat.stop()
                logger.info("自动聊天模块... [ 已停止 ]")
            
            # 停止ASR
            if self.asr_client:
                await self.asr_client.stop()
                logger.info("ASR客户端... [ 已停止 ]")
            
            # 停止TTS
            if self.tts_client:
                await self.tts_client.stop()
                logger.info("TTS客户端... [ 已停止 ]")
            
            # 停止B站直播监听
            if self.bilibili_listener:
                await self.bilibili_listener.stop()
                logger.info("B站直播监听... [ 已停止 ]")
            
            # 清理字幕管理器
            if self.subtitle_manager:
                await self.subtitle_manager.cleanup()
                logger.info("字幕管理器... [ 已清理 ]")
            
        except Exception as e:
            logger.error(f"- 停止组件失败: {e}")
    
    async def _cancel_tasks(self):
        """取消所有异步任务"""
        try:
            if self.tasks:
                logger.info(f"- 取消{len(self.tasks)}个异步任务")
                for task in list(self.tasks):
                    if not task.done():
                        task.cancel()
                
                # 等待任务完成
                await asyncio.gather(*self.tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"- 取消任务失败: {e}")
    
    # ============================
    # 核心状态管理和ASR控制逻辑
    # ============================
    
    async def _check_and_update_asr_status(self):
        """根据TTS状态更新ASR锁定状态 - 内部调用函数"""
        if self.tts_client:
            # 只有当状态变化时才执行操作
            tts_active, *_ , is_playing_audio = await self._is_tts_active()
            if self.asr_client:
                if tts_active and is_playing_audio:
                    self.asr_client.asr_locked = True
                    logger.debug("ASR锁定：TTS活动")
                elif (not tts_active) and (not is_playing_audio):
                    self.asr_client.asr_locked = False
                    logger.debug("ASR解锁：TTS空闲")
            if not tts_active:
                await self.tts_client.reset()
                self.subtitle_manager.clear_text()
    
    # ============================
    # LLM相关事件处理
    # ============================

    async def _on_input_to_llm(self, data:dict):
        """将输入传输给LLM - 内部调用函数"""
        # 检查是否需要记忆
        text = data.get("text", "")
        if self.memory_manager:
            try:
                need_memory = await self.memory_manager.check_memory_needed(text)
                if need_memory:
                    await self.memory_manager.save_to_memory(text)
                    logger.info("用户消息已保存到记忆库")
            except Exception as e:
                logger.error(f"记忆管理失败: {e}")
        
        # 检查是否需要视觉
        image_data = None
        if self.vision_client:
            try:
                need_vision = await self.vision_client.check_vision_needed(text)
                if need_vision:
                    logger.info("用户消息需要视觉处理")
                    image_data = await self.vision_client.take_screenshot()
            except Exception as e:
                logger.error(f"视觉处理失败: {e}")

        # 检查是否需要mcp
        if self.mcp_client:
            try:
                all_available_tools_for_llm = self.mcp_client.all_available_tools_for_llm
                tool_to_session_map = self.mcp_client.tool_to_session_map
                self.llm_client.mcp_client = self.mcp_client
            except Exception as e:
                logger.warning(f"MCP处理失败: {e}")
        
        # 发送到LLM处理
        if self.llm_client:
            try:
                if not self.mcp_client:
                    response = await self.llm_client.send_message(text, image_data, stream=True)
                    logger.info(f"AI回复: {response[:50]}..." if len(response) > 50 else f"AI回复: {response}")
                else:
                    response = await self.llm_client.send_message(text, image_data, stream=True, tools=all_available_tools_for_llm, tool_choice=tool_to_session_map, use_tool_call=True)
                    if "http" in response:
                        logger.info(f"AI回复: {response}")
                    else:
                        logger.info(f"AI回复: {response[:50]}..." if len(response) > 50 else f"AI回复: {response}")
            except Exception as e:
                logger.error(f"LLM处理失败: {e}")
    
    async def _on_llm_streaming(self, data:dict):
        """处理LLM流式输出事件 - 事件调用函数"""
        try:
            text = data.get("text", "").replace('\n', '') # 已初步分割完成的输出片段
            full_text = data.get("full_text", "").replace('\n', '')
            is_final = data.get("is_final", False)
            
            if not is_final:
                # LLM正在流式输出
                self.llm_streaming = True
                if self.tts_client:
                    self.tts_client.current_full_text += text
                    # 检查是否需要发送给TTS（遇到标点符号）
                    if any(True for word in text if word in self.tts_client.punctuations):
                        segments = self.tts_client._segment_text(self.tts_client.current_full_text)
                        if len(segments) > 1:
                            # 发送所有完整片段(除了最后一个)
                            for i in range(len(segments)-1):
                                # 将片段发送给TTS进行处理
                                await self.tts_client.add_streaming_text(segments[i])
                                logger.debug(f"发送文本片段到TTS: {segments[i]}")
                            # 保留最后一个片段
                            self.tts_client.current_full_text = segments[-1]
                        else:
                            # 只有一个片段
                            await self.tts_client.add_streaming_text(segments[0])
                            self.tts_client.current_full_text = ''
                            logger.debug(f"发送文本片段到TTS: {segments[0]}")
                else:
                    if self.subtitle_manager:
                        self.subtitle_manager.add_text(text, stream=True)
            
            elif is_final and text:
                if self.tts_client:
                    self.tts_client.current_full_text += text
                    if self.tts_client.current_full_text.strip():
                        segments = self.tts_client._segment_text(self.tts_client.current_full_text)
                        for segment in segments:
                            if segment.strip():
                                await self.tts_client.add_streaming_text(segment)
                                logger.debug(f"发送最终文本片段到TTS: {segment}")
                        self.tts_client.current_full_text = ''
                else:
                    if self.subtitle_manager:
                        self.subtitle_manager.add_text(text, stream=True)
                # LLM流式输出结束
                self.llm_streaming = False
                logger.debug("LLM流式输出结束")
        
        except Exception as e:
            logger.error(f"处理LLM流式输出事件失败: {e}")
    
    async def _on_llm_complete(self, data:dict):
        """处理LLM完成事件 - 事件调用函数"""
        try:
            text = data.get("text", "")
            
            # 确保LLM流式状态为False
            self.llm_streaming = False

            with open('chat_log.txt', 'a', encoding='utf-8') as chat_log:
                chat_log.write("Fake Neuro:{}\n\n".format(text.replace('\n', ' ')))
            if self.rag_system:
                self.rag_system.records += 1
                if self.rag_system.records >= self.llm_client.max_messages:
                    self.rag_system.records = 0
                    await self.rag_system.update_database('chat_log.txt')

            await self._check_and_update_asr_status()
            if not self.tts_client and self.subtitle_manager:
                await asyncio.sleep(len(text) * self.subtitle_manager.stream_delay / 1000)
                self.subtitle_manager.clear_text()
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
                await self.auto_chat.update_state(llm_inputing=False)
            
            logger.debug(f"LLM完成响应: {len(text)}字符")
        
        except Exception as e:
            logger.error(f"处理LLM完成事件失败: {e}")
    
    async def _on_llm_error(self, data):
        """处理LLM错误事件 - 事件调用函数"""
        try:
            error = data.get("error", "未知错误")
            logger.error(f"LLM错误: {error}")
            
            # 重置状态
            self.llm_streaming = False
            self.user_input_processing = False
        
        except Exception as e:
            logger.error(f"处理LLM错误事件失败: {e}")

    async def _on_llm_output(self, data: dict):
        """处理LLM输出文本回调 - 回调函数"""
        try:
            text = data.get("text", "")
            full_text = data.get("full_text", "")
            is_final = data.get("is_final", False)
            await self.context_processor.handle_llm_output(text, full_text, is_final)

        except Exception as e:
            logger.error(f"处理LLM输出失败: {e}")

    async def _on_send_prompt(self, data: dict):
        """将提示词发送到LLM"""
        prompt = data.get('prompt', '')
        await self._on_input_to_llm({'text': prompt})
    
    # ============================
    # TTS相关事件处理
    # ============================
    
    async def _on_tts_start(self, data):
        """处理TTS开始事件 - 事件调用函数"""
        try:
            logger.debug("TTS开始处理")
            await self._check_and_update_asr_status()
            # 更新自动聊天的最后交互时间
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
                await self.auto_chat.update_state(tts_playing=True)
        except Exception as e:
            logger.error(f"处理TTS开始事件失败: {e}")
    
    async def _on_tts_end(self, data):
        """处理TTS结束事件 - 事件调用函数"""
        try:
            logger.debug("TTS处理结束")
            await self._check_and_update_asr_status()
            # 更新自动聊天的最后交互时间
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
                await self.auto_chat.update_state(tts_playing=False)
        except Exception as e:
            logger.error(f"处理TTS结束事件失败: {e}")
    
    async def _on_tts_error(self, data):
        """处理TTS错误事件 - 事件调用函数"""
        try:
            error = data.get("error", "未知错误")
            logger.error(f"TTS错误: {error}")
        except Exception as e:
            logger.error(f"处理TTS错误事件失败: {e}")
    
    async def _on_audio_data(self, data:dict):
        """音频数据回调（用于嘴型同步） - 回调函数"""
        try:
            if self.live2d_model:
                self.live2d_model.wav_handler.Start(data)
                
                logger.debug(f"嘴型同步数据已设置")
        except Exception as e:
            logger.error(f"处理音频数据失败: {e}")
    
    async def _on_text_update(self, text):
        """文本更新回调（用于字幕显示） - 回调函数"""
        try:
            if self.subtitle_manager:
                # 发送给字幕管理器
                self.subtitle_manager.add_text(text)
                logger.debug(f"更新字幕文本: {text}")
        except Exception as e:
            logger.error(f"文本更新回调失败: {e}")

    async def _is_tts_active(self) -> bool:
        """检查TTS是否处于活动状态  - 内部调用函数"""
        if self.tts_client:
            return await self.tts_client.is_active()
        return False, False, False, False, False
    
    # ============================
    # ASR相关事件处理
    # ============================
    
    async def _on_user_speaking(self, data:dict):
        """处理用户说话事件 - 事件调用函数"""
        try:
            is_speaking = data.get("is_speaking", False)
            
            if is_speaking:
                logger.debug("用户开始说话")
                # 更新自动聊天的最后交互时间
                if self.auto_chat:
                    self.auto_chat.update_last_interaction_time()
                    await self.auto_chat.update_state(user_speaking=True)
            else:
                logger.debug("用户停止说话")
        
        except Exception as e:
            logger.error(f"处理用户说话事件失败: {e}")
    
    async def _on_speech_recognized(self, data:dict):
        """处理语音识别结果 - 事件调用函数"""
        try:
            text = data.get("text", "")
            logger.info(f"识别到用户语音输入: '{text}'")
            # 设置用户输入处理标志
            if self.subtitle_manager:
                self.subtitle_manager.add_text(f"用户:{text}", user_input=text)
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
                await self.auto_chat.update_state(user_speaking=False, llm_inputing=True)
            self.user_input_processing = True
            self.asr_client.asr_locked = True

            with open('chat_log.txt', 'a', encoding='utf-8') as chat_log:
                chat_log.write(f"用户:{text}\n")
            if not self.rag_system:
                await self.prompt_integrator.add_prompt(text)
            else:
                if self.rag_system.counts >= 10:
                    await self.rag_system.get_output(text)
                else:
                    await self.prompt_integrator.add_prompt(text)
            
        except Exception as e:
            logger.error(f"处理语音识别失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 重置用户输入处理标志
            self.user_input_processing = False
            logger.debug("用户输入处理完成")

    # ============================
    # 用户输入框相关事件处理
    # ============================

    async def handle_user_input(self, data):
        """处理用户输入事件 - 事件调用函数"""
        try:
            text = data.get("text", "")
            logger.info(f"收到用户输入: {text}")
            # 设置用户输入处理标志
            if self.subtitle_manager:
                self.subtitle_manager.add_text(f"用户:{text}", user_input=text)
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
                await self.auto_chat.update_state(llm_inputing=True)

            with open('chat_log.txt', 'a', encoding='utf-8') as chat_log:
                chat_log.write(f"用户:{text}\n")
            if not self.rag_system:
                await self.prompt_integrator.add_prompt(text)
            else:
                if self.rag_system.counts >= 10:
                    await self.rag_system.get_output(text)
                else:
                    await self.prompt_integrator.add_prompt(text)
            
        except Exception as e:
            logger.error(f"处理输入框输入失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # ============================
    # RAG相关事件处理
    # ============================
    
    async def _on_get_rag_output(self, data: dict):
        user_input = data.get('user_input', '')
        rag_output = data.get("rag_output", '')
        await self.prompt_integrator.add_prompt(user_input, rag_output)
            
    # ============================
    # 自动聊天相关事件处理
    # ============================
    
    async def _on_auto_chat_request(self, data):
        """处理自动聊天请求 - 事件调用函数"""
        try:
            prompt = data.get("prompt", "")
            logger.info(f"收到自动聊天请求: {prompt}")
            
            # 检查是否可以处理自动聊天（不在处理其他任务时）
            if not (self.llm_streaming or (await self._is_tts_active())[0] or self.user_input_processing):
                # 直接处理自动聊天
                if self.llm_client:
                    await self.prompt_integrator.add_prompt(prompt)
            else:
                logger.info("当前正在处理其他任务，跳过自动聊天")
        except Exception as e:
            logger.error(f"处理自动聊天请求失败: {e}")
    
    async def _on_auto_chat_response(self, data):
        """处理自动聊天响应 - 事件调用函数"""
        try:
            text = data.get("text", "")
            if text and self.tts_client:
                await self.tts_client.speak(text)
        except Exception as e:
            logger.error(f"处理自动聊天响应失败: {e}")
    
    # ============================
    # B站直播相关事件处理
    # ============================
    
    async def _on_bilibili_message_event(self, data):
        """处理B站弹幕事件 - 事件调用函数"""
        try:
            message = data.get("message", {})
            if message:
                # 创建任务处理弹幕
                task = asyncio.create_task(self._process_bilibili_message(message))
                self.tasks.add(task)
                task.add_done_callback(lambda t: self.tasks.discard(t))
        except Exception as e:
            logger.error(f"处理B站弹幕事件失败: {e}")
    
    async def _process_bilibili_message(self, message):
        """处理B站弹幕消息 - 事件调用函数"""
        try:
            # 检查是否可以处理弹幕（不在处理其他重要任务时）
            if self.user_input_processing:
                logger.info("正在处理用户输入，跳过弹幕处理")
                return
            
            nickname = message.get("nickname", "观众")
            text = f"[弹幕] {nickname}: {text}"
            logger.info(f"收到弹幕: {nickname}: {text}")
            
            with open('chat_log.txt', 'a', encoding='utf-8') as chat_log:
                chat_log.write(text+'\n')
            if not self.rag_system:
                await self.prompt_integrator.add_prompt(text)
            else:
                if self.rag_system.counts >= 10:
                    await self.rag_system.get_output(text)
                else:
                    await self.prompt_integrator.add_prompt(text)
            
            # 更新自动聊天的最后交互时间
            if self.auto_chat:
                self.auto_chat.update_last_interaction_time()
        
        except Exception as e:
            logger.error(f"处理B站弹幕消息失败: {e}")
    
    # ============================
    # 应用控制事件处理
    # ============================
    
    async def _on_app_shutdown(self, data):
        """处理应用关闭事件 - 事件调用函数"""
        try:
            logger.info("收到应用关闭事件")
            await self.shutdown()
        except Exception as e:
            logger.error(f"处理应用关闭事件失败: {e}")
    
    # ============================
    # 异步上下文管理器支持
    # ============================
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.shutdown()
    
    def __del__(self):
        """析构函数 - 清理资源警告"""
        if self.is_running:
            logger.warning("AppManager被销毁时仍在运行，建议使用异步上下文管理器或手动调用shutdown()")