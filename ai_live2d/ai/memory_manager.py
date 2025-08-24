"""
记忆管理模块 - 负责保存和检索用户记忆
"""

import os
import json
import time
import logging
import aiohttp
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger("memory_manager")

class MemoryManager:
    """记忆管理类，处理用户记忆的保存和检索"""
    
    def __init__(self, config, event_bus=None):
        """初始化记忆管理器
        
        Args:
            config: 配置信息，包含记忆相关配置
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus
        
        # 从配置中获取记忆相关配置
        self.memory_file_path = config.get("memory", {}).get("file_path", "text_database.txt")
        self.memory_check_url = config.get("memory", {}).get("check_url", "http://127.0.0.1:7878/check")
        
        # 确保记忆文件存在
        self._ensure_memory_file()
        
        logger.info("初始化记忆管理器... [ 完成 ]")
    
    def _ensure_memory_file(self):
        """确保记忆文件存在，如果不存在则创建"""
        try:
            if not os.path.exists(self.memory_file_path):
                # 创建目录
                os.makedirs(os.path.dirname(os.path.abspath(self.memory_file_path)), exist_ok=True)
                
                # 创建空文件
                with open(self.memory_file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                
                logger.info(f"- 已创建记忆文件: {self.memory_file_path}")
        except Exception as e:
            logger.error(f"- 创建记忆文件失败: {e}")
    
    async def check_memory_needed(self, text: str) -> bool:
        """检查消息是否需要保存到记忆
        
        Args:
            text: 要检查的文本
        
        Returns:
            是否需要保存
        """
        try:
            # 构建请求URL
            url = f"{self.memory_check_url}?text={text}"
            
            # 发送POST请求
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if not response.status == 200:
                        logger.error(f"记忆检查API请求失败: {response.status}")
                        return False
                    
                    # 解析响应
                    response_data = await response.json()
                    logger.info(f"记忆检查结果: {response_data}")
                    
                    # 判断是否需要保存
                    need_memory = response_data.get("需要检索") == "是"
                    return need_memory
        
        except Exception as e:
            logger.error(f"记忆检查错误: {e}")
            return False
    
    async def save_to_memory(self, text: str) -> bool:
        """保存消息到记忆文件
        
        Args:
            text: 要保存的文本
        
        Returns:
            是否保存成功
        """
        try:
            # 获取当前时间戳
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            memory_entry = f"[{timestamp}] {text}\n"
            
            # 追加到记忆文件
            with open(self.memory_file_path, 'a', encoding='utf-8') as f:
                f.write(memory_entry)
            
            logger.info(f"已保存到记忆文件: {text}")
            
            # 发布记忆保存事件
            if self.event_bus:
                self.event_bus.publish("memory_saved", {
                    "text": text,
                    "timestamp": timestamp
                })
            
            return True
        
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
            return False
    
    def read_memory(self) -> str:
        """读取记忆文件内容
        
        Returns:
            记忆文件的全部内容
        """
        try:
            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                memory_content = f.read()
            
            logger.info("成功读取记忆库内容")
            return memory_content
        
        except Exception as e:
            logger.error(f"读取记忆库文件失败: {e}")
            return "无法读取记忆库内容"
    
    async def process_user_message(self, text: str) -> bool:
        """处理用户消息，检查并保存到记忆（如需要）
        
        Args:
            text: 用户消息文本
        
        Returns:
            是否处理成功
        """
        try:
            # 检查是否需要保存到记忆
            need_memory = await self.check_memory_needed(text)
            
            if need_memory:
                # 保存到记忆
                await self.save_to_memory(text)
                logger.info("用户消息已保存到记忆库")
                return True
            else:
                logger.info("用户消息不需要保存到记忆库")
                return False
        
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            return False