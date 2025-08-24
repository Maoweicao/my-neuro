"""
B站直播监听模块 - 监听B站直播间弹幕
"""

import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("bilibili_listener")

class BiliBiliListener:
    """B站直播监听类，用于获取直播间弹幕"""
    
    def __init__(self, config, event_bus=None):
        """初始化B站直播监听模块
        
        Args:
            config: 配置信息，包含直播相关配置
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus
        
        # 从配置中获取直播相关配置
        self.room_id = config.get("bilibili", {}).get("roomId", "")
        self.check_interval = config.get("bilibili", {}).get("checkInterval", 5000) / 1000  # 转换为秒
        self.max_messages = config.get("bilibili", {}).get("maxMessages", 50)
        self.api_url = config.get("bilibili", {}).get("apiUrl", "http://api.live.bilibili.com/ajax/msg")
        
        # 状态变量
        self.is_running = False
        self.last_checked_timestamp = time.time()
        self.message_cache = []
        self.task = None
        
        # 回调函数
        self.on_new_message = None
        
        logger.info("初始化B站直播监听模块... [ 完成 ]")
    
    def set_on_new_message(self, callback: Callable):
        """设置新消息回调函数
        
        Args:
            callback: 回调函数，参数为消息对象
        """
        self.on_new_message = callback
    
    async def start(self):
        """启动直播监听"""
        if self.is_running:
            return False
        
        logger.info(f"- B站直播监听模块启动，监听房间: {self.room_id}")
        self.is_running = True
        
        # 立即获取一次弹幕
        await self.fetch_barrage()
        
        # 创建定时任务
        self.task = asyncio.create_task(self._check_loop())
        
        return True
    
    async def stop(self):
        """停止直播监听"""
        if not self.is_running:
            return False
        
        # 取消定时任务
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        self.is_running = False
        logger.info("停止B站直播监听模块... [ 完成 ]")
        
        return True
    
    async def _check_loop(self):
        """弹幕检查循环"""
        try:
            while self.is_running:
                await self.fetch_barrage()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("B站直播监听循环已取消")
            raise
        except Exception as e:
            logger.error(f"B站直播监听循环错误: {e}")
            self.is_running = False
    
    async def fetch_barrage(self):
        """获取弹幕"""
        try:
            # 构建API请求URL
            url = f"{self.api_url}?roomid={self.room_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
                }) as response:
                    if not response.status == 200:
                        logger.error(f"获取弹幕失败: HTTP状态码 {response.status}")
                        return
                    
                    # 解析响应
                    data = await response.json()
                    
                    if not data or 'data' not in data or 'room' not in data['data']:
                        logger.error("API返回数据格式错误")
                        return
                    
                    messages = data['data']['room']
                    
                    # 过滤出新消息
                    new_messages = []
                    for message in messages:
                        message_time = time.mktime(time.strptime(message['timeline'], "%Y-%m-%d %H:%M:%S"))
                        if message_time > self.last_checked_timestamp:
                            new_messages.append(message)
                    
                    # 只有在有新消息时更新时间戳
                    if new_messages:
                        self.last_checked_timestamp = time.time()
                        
                        # 更新消息缓存
                        self.message_cache.extend(new_messages)
                        
                        # 如果超过最大缓存数量，裁剪旧消息
                        if len(self.message_cache) > self.max_messages:
                            self.message_cache = self.message_cache[-self.max_messages:]
                        
                        # 处理每条新消息
                        for message in new_messages:
                            logger.debug(f"收到弹幕: {message['nickname']}: {message['text']}")
                            
                            # 调用回调函数
                            if self.on_new_message:
                                self.on_new_message(message)
                            
                            # 发布事件
                            if self.event_bus:
                                self.event_bus.publish("bilibili_message", {
                                    "message": message
                                })
        
        except Exception as e:
            logger.error(f"获取弹幕出错: {e}")
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取缓存的所有消息
        
        Returns:
            消息列表
        """
        return self.message_cache.copy()
    
    def clear_messages(self):
        """清除消息缓存"""
        self.message_cache = []
    
    def set_room_id(self, room_id: str) -> bool:
        """修改房间ID
        
        Args:
            room_id: 房间ID
        
        Returns:
            是否修改成功
        """
        if not room_id:
            return False
        
        self.room_id = room_id
        
        # 如果正在运行，重启以应用新的房间ID
        if self.is_running:
            asyncio.create_task(self._restart())
        
        return True
    
    async def _restart(self):
        """重启监听"""
        await self.stop()
        await self.start()
    
    def set_check_interval(self, interval: int) -> bool:
        """修改轮询间隔
        
        Args:
            interval: 间隔时间（毫秒）
        
        Returns:
            是否修改成功
        """
        if interval < 1000:  # 至少1秒
            return False
        
        self.check_interval = interval / 1000  # 转换为秒
        
        # 如果正在运行，重启以应用新的轮询间隔
        if self.is_running:
            asyncio.create_task(self._restart())
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取模块当前状态
        
        Returns:
            状态信息
        """
        return {
            "is_running": self.is_running,
            "room_id": self.room_id,
            "check_interval": self.check_interval,
            "last_checked_timestamp": self.last_checked_timestamp,
            "message_count": len(self.message_cache)
        }