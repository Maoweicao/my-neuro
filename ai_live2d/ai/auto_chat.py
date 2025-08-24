"""
自动聊天模块 - 完全异步版本
在用户空闲时触发主动对话
"""

import time
import random
import logging
import asyncio
import inspect
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("auto_chat")

class AutoChatModule:
    """自动聊天模块，定期检查空闲状态并触发对话"""
    
    def __init__(self, config, event_bus=None):
        """初始化自动聊天模块
        
        Args:
            config: 配置信息，包含自动聊天相关配置
            event_bus: 事件总线，用于发布/订阅事件
        """
        self.config = config
        self.event_bus = event_bus
        
        # 从配置中获取自动聊天相关配置
        self.check_interval = config.get("auto_chat", {}).get("interval", 5000) / 1000  # 转换为秒
        self.min_interval = config.get("auto_chat", {}).get("min_interval", 30000) / 1000  # 转换为秒
        self.max_interval = config.get("auto_chat", {}).get("max_interval", 180000) / 1000  # 转换为秒
        self.idle_time = config.get("auto_chat", {}).get("idle_time", 15000) / 1000  # 转换为秒
        
        # 状态变量
        self.is_running = False
        self.last_interaction_time = time.time()
        self.user_speaking = None  # 用户说话状态
        self.tts_playing = None    # TTS播放状态
        self.llm_inputing = None   # LLM输出状态
        
        # 异步任务管理
        self.tasks = set()  # 跟踪所有异步任务
        self.idle_check_task = None  # 空闲检查任务
        self.should_stop = False    # 停止标志
        
        logger.info("初始化自动聊天模块... [ 完成 ]")
    
    async def start(self):
        """启动自动聊天模块"""
        if self.is_running:
            logger.warning("- 自动聊天模块已在运行")
            return
        
        logger.info(f"- 自动聊天模块启动，空闲触发时间：{self.idle_time}秒，检查间隔：{self.check_interval}秒")
        self.is_running = True
        self.should_stop = False
        
        # 初始化最后交互时间
        self.last_interaction_time = time.time()
        
        # 启动空闲检查任务
        self.idle_check_task = asyncio.create_task(self._idle_check_loop())
        self.tasks.add(self.idle_check_task)
        self.idle_check_task.add_done_callback(lambda t: self.tasks.discard(t))
    
    async def stop(self):
        """停止自动聊天模块"""
        if not self.is_running:
            return
        
        self.should_stop = True
        self.is_running = False
        
        logger.info("停止自动聊天模块... [ 进行中 ]")
        
        # 取消所有任务
        for task in list(self.tasks):
            if not task.done():
                task.cancel()
        
        # 等待所有任务完成
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("停止自动聊天模块... [ 完成 ]")

    async def update_state(self, user_speaking=None, tts_playing=None, llm_inputing=None):
        """更新状态"""
        if user_speaking is not None:
            self.user_speaking = user_speaking
        if tts_playing is not None:
            self.tts_playing = tts_playing
        if llm_inputing is not None:
            self.llm_inputing = llm_inputing
    
    async def _idle_check_loop(self):
        """空闲检查循环"""
        logger.info("启动空闲检查任务... [ 成功 ]")
        
        while not self.should_stop:
            try:
                # 等待检查间隔
                await asyncio.sleep(self.check_interval)
                
                if self.should_stop:
                    break
                
                # 检查空闲状态
                await self._check_idle_state()
                
            except asyncio.CancelledError:
                logger.debug("空闲检查任务被取消")
                break
            except Exception as e:
                logger.error(f"空闲检查循环出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # 出错后继续运行，避免整个模块停止
                await asyncio.sleep(1)
        
        logger.info("停止空闲检查任务... [ 成功 ]")
    
    async def _check_idle_state(self):
        """检查空闲状态"""
        try:
            if not self.is_running:
                return
            
            current_time = time.time()
            idle_time = current_time - self.last_interaction_time
            
            logger.debug(f"检查空闲状态: {idle_time:.1f}秒/{self.idle_time}秒")
            
            # 如果空闲时间超过阈值，触发主动对话
            if idle_time >= self.idle_time:
                # 检查是否可以触发自动对话
                if await self._can_trigger_auto_chat():
                    await self._handle_auto_chat()
                    # 重置最后交互时间
                    self.last_interaction_time = time.time()
                else:
                    logger.debug("当前状态不适合触发自动对话，跳过")
        
        except Exception as e:
            logger.error(f"检查空闲状态出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _can_trigger_auto_chat(self):
        """检查是否可以触发自动对话
        
        Returns:
            bool: 是否可以触发
        """
        # 检查用户是否正在说话
        if self.user_speaking:
            logger.debug("用户正在说话，跳过自动对话")
            self.update_last_interaction_time()
            return False
        
        # 检查TTS是否正在播放
        if self.tts_playing:
            logger.debug("TTS正在播放，跳过自动对话")
            self.update_last_interaction_time()
            return False
        
        # 检查LLM是否正在输出
        if self.llm_inputing:
            logger.debug("LLM正在输出，跳过自动对话")
            self.update_last_interaction_time()
            return False
        
        return True
    
    async def _handle_auto_chat(self):
        """处理自动对话"""
        try:
            # 随机选择提示词
            prompt_templates = [
                "你看到主人一段时间没有说话，请基于对话历史，现有的上下文对话记录来主动发起一段简短的对话。",
                "似乎有一段时间没有对话了，你可以主动说点什么来活跃气氛吗？",
                "检测到长时间没有互动，你可以主动聊个轻松的话题吗？",
                "主人好像在忙别的事情，你可以说点什么来陪伴一下吗？",
                "看起来有点安静，你想和主人聊什么呢？"
            ]
            
            prompt = random.choice(prompt_templates)
            
            logger.info(f"触发自动对话，提示词: {prompt}")
            
            # 添加自动触发标记
            auto_prompt = f"[自动触发] {prompt}"
            
            # 通过事件总线发布自动对话请求
            if self.event_bus:
                await self.event_bus.publish("auto_chat_request", {
                    "prompt": auto_prompt,
                    "timestamp": time.time()
                })
                logger.info("已通过事件总线发布自动对话请求")
        
        except Exception as e:
            logger.error(f"处理自动对话出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_last_interaction_time(self):
        """更新最后交互时间"""
        self.last_interaction_time = time.time()
        logger.debug("自动聊天：更新最后交互时间")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.stop()
    
    def __del__(self):
        """析构函数 - 清理资源"""
        # 在同步上下文中无法直接调用异步方法
        # 只能记录警告
        if self.is_running:
            logger.warning("AutoChatModule被销毁时仍在运行，建议使用上下文管理器或手动调用stop()")