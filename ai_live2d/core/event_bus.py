"""
事件总线模块 - 实现模块间的低耦合通信，支持同步和异步回调(完全异步化)
"""

import logging
import asyncio
import inspect
from collections import defaultdict
from typing import Dict, List, Callable, Any, Coroutine

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        """初始化事件总线"""
        self.subscribers = defaultdict(list)  # 自动处理不存在的键
        self.lock = asyncio.Lock()  # 异步锁
        self.tasks = set()  # 跟踪所有异步任务
        self.is_shutting_down = False  # 关闭状态标志
        
        logger.info("初始化事件总线... [ 完成 ]")
    
    async def subscribe(self, event_type: str, callback: Callable):
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数（支持同步和异步）
        """
        # 检查是否正在关闭
        if self.is_shutting_down:
            logger.warning(f"拒绝订阅: 事件总线正在关闭 ({event_type})")
            return

        async with self.lock: # 异步上下文管理器
            self.subscribers[event_type].append(callback)
            logger.debug(f"订阅事件: {event_type} - {callback.__name__}")
    
    async def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅事件
        
        Args:
            event_type: 事件类型
            callback: 要移除的回调函数
        """
        async with self.lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                logger.debug(f"取消订阅事件: {event_type} - {callback.__name__}")
    
    async def publish(self, event_type: str, data: Dict[str, Any] = None):
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        # 如果正在关闭，拒绝新事件
        if self.is_shutting_down:
            logger.warning(f"拒绝发布: 事件总线正在关闭 ({event_type})")
            return

        data = data or {}
        
        # 获取回调列表（需要加锁）
        async with self.lock:
            callbacks = self.subscribers[event_type].copy()

        # 记录事件发布信息
        logger.debug(f"发布事件: {event_type}, 订阅者数: {len(callbacks)}")
        
        # 为每个回调创建任务
        for callback in callbacks:
            # 创建任务并添加到集合中
            task = asyncio.create_task(
                self._process_callback(callback, data, event_type),
                name=f"EventTask-{event_type}-{callback.__name__}"
            )
            # 任务完成后自动从集合中移除
            task.add_done_callback(lambda t: self.tasks.discard(t))
            self.tasks.add(task)

    def publish_sync(self, event_type: str, data: Dict[str, Any] = None):
        """同步发布事件，避免创建额外任务"""
        if self.is_shutting_down:
            return
            
        data = data or {}
        callbacks = self.subscribers[event_type].copy()
        
        for callback in callbacks:
            if inspect.iscoroutinefunction(callback):
                # 对于异步回调，仍然需要任务
                asyncio.create_task(callback(data))
            else:
                # 同步回调直接执行
                callback(data)
    
    async def _process_callback(self, callback: Callable, data: dict, event_type: str):
        """处理回调函数，支持同步和异步回调
        
        Args:
            callback: 回调函数
            data: 事件数据
            event_type: 事件类型(用于日志)
        """
        try:
            logger.debug(f"开始处理回调: {event_type} -> {callback.__name__}")

            # 检查是否为协程函数
            if inspect.iscoroutinefunction(callback):
                logger.debug(f"执行异步回调: {event_type} -> {callback.__name__}")
                await callback(data)  # 直接等待异步回调
            else:
                # 对于同步函数，使用run_in_executor避免阻塞事件循环
                logger.debug(f"执行同步回调: {event_type} -> {callback.__name__}")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,  # 使用默认线程池执行器
                    callback, 
                    data
                )
        
        except asyncio.CancelledError:
            # 任务被正常取消，不记录为错误
            logger.debug(f"回调取消: {event_type} -> {callback.__name__}")
            
        except Exception as e:
            logger.error(f"处理回调出错: {event_type} -> {callback.__name__}, {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def shutdown(self):
        """关闭事件总线，清理资源"""
        # 取消所有未完成的任务
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        logger.info("开始关闭事件总线...")

        # 取消所有未完成的任务
        cancel_tasks = []
        for task in self.tasks:
            if not task.done():
                task.cancel()
                cancel_tasks.append(task)
        
        logger.info(f"已取消 {len(cancel_tasks)} 个进行中的任务")
        
        # 等待所有任务完成或取消
        if cancel_tasks:
            await asyncio.gather(*cancel_tasks, return_exceptions=True)

        # 清空订阅者
        async with self.lock:
            self.subscribers.clear()
        
        logger.info("事件总线已关闭")