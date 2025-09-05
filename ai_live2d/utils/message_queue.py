#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程间消息队列通信管理器
用于替代socket通信，提供更可靠的main.py和UI.py之间的通信
"""

import json
import time
import threading
import queue
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

class MessageQueue:
    """消息队列管理器"""
    
    def __init__(self, queue_file: str = "message_queue.json"):
        self.queue_file = Path(queue_file)
        self.lock = threading.Lock()
        self.logger = logging.getLogger("message_queue")
        
        # 内存队列，用于快速访问
        self.memory_queue = queue.Queue()
        
        # 消息处理器映射
        self.message_handlers: Dict[str, Callable] = {}
        
        # 监听线程
        self.listener_thread = None
        self.is_running = False
        
        # 初始化队列文件
        self._initialize_queue_file()
    
    def _initialize_queue_file(self):
        """初始化队列文件"""
        try:
            if not self.queue_file.exists():
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    json.dump({"messages": []}, f, ensure_ascii=False, indent=2)
            else:
                # 清空现有消息
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    json.dump({"messages": []}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"初始化队列文件失败: {e}")
    
    def send_message(self, message_type: str, data: Dict[str, Any], priority: int = 1) -> bool:
        """发送消息到队列
        
        Args:
            message_type: 消息类型 (interrupt, play_audio, show_subtitle等)
            data: 消息数据
            priority: 优先级 (1=高, 2=中, 3=低)
        
        Returns:
            bool: 发送是否成功
        """
        try:
            message = {
                "type": message_type,
                "data": data,
                "priority": priority,
                "timestamp": time.time(),
                "id": f"{message_type}_{int(time.time() * 1000)}"
            }
            
            # 添加到内存队列
            self.memory_queue.put(message)
            
            # 同时写入文件队列（作为备份）
            self._write_to_file_queue(message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    def _write_to_file_queue(self, message: Dict[str, Any]):
        """写入消息到文件队列"""
        try:
            with self.lock:
                # 读取现有消息
                messages = []
                if self.queue_file.exists():
                    try:
                        with open(self.queue_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            messages = data.get("messages", [])
                    except (json.JSONDecodeError, FileNotFoundError):
                        messages = []
                
                # 添加新消息
                messages.append(message)
                
                # 限制队列长度，只保留最新的100条消息
                if len(messages) > 100:
                    messages = messages[-100:]
                
                # 写回文件
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            self.logger.error(f"写入文件队列失败: {e}")
    
    def receive_message(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """从队列接收消息
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            Dict: 消息字典，如果没有消息则返回None
        """
        try:
            # 首先尝试从内存队列获取
            try:
                message = self.memory_queue.get(timeout=timeout)
                self.memory_queue.task_done()
                return message
            except queue.Empty:
                pass
            
            # 如果内存队列为空，尝试从文件队列读取
            return self._read_from_file_queue()
            
        except Exception as e:
            self.logger.error(f"接收消息失败: {e}")
            return None
    
    def _read_from_file_queue(self) -> Optional[Dict[str, Any]]:
        """从文件队列读取消息"""
        try:
            with self.lock:
                if not self.queue_file.exists():
                    return None
                
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    messages = data.get("messages", [])
                
                if not messages:
                    return None
                
                # 按优先级和时间戳排序
                messages.sort(key=lambda x: (x.get("priority", 3), x.get("timestamp", 0)))
                
                # 取出第一条消息
                message = messages.pop(0)
                
                # 写回剩余消息
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)
                
                return message
                
        except Exception as e:
            self.logger.error(f"从文件队列读取失败: {e}")
            return None
    
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type] = handler
        self.logger.info(f"注册消息处理器: {message_type}")
    
    def start_listener(self):
        """启动消息监听器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()
        self.logger.info("消息队列监听器已启动")
    
    def stop_listener(self):
        """停止消息监听器"""
        self.is_running = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)
        self.logger.info("消息队列监听器已停止")
    
    def _listener_loop(self):
        """消息监听循环"""
        while self.is_running:
            try:
                message = self.receive_message(timeout=0.5)
                if message:
                    self._process_message(message)
            except Exception as e:
                self.logger.error(f"消息监听循环出错: {e}")
                time.sleep(0.1)
    
    def _process_message(self, message: Dict[str, Any]):
        """处理消息"""
        try:
            message_type = message.get("type", "")
            message_data = message.get("data", {})
            
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                handler(message_data)
                self.logger.debug(f"处理消息: {message_type}")
            else:
                self.logger.warning(f"未找到消息处理器: {message_type}")
                
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
    
    def clear_queue(self):
        """清空队列"""
        try:
            # 清空内存队列
            while not self.memory_queue.empty():
                try:
                    self.memory_queue.get_nowait()
                    self.memory_queue.task_done()
                except queue.Empty:
                    break
            
            # 清空文件队列
            with self.lock:
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    json.dump({"messages": []}, f, ensure_ascii=False, indent=2)
            
            self.logger.info("消息队列已清空")
            
        except Exception as e:
            self.logger.error(f"清空队列失败: {e}")
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        try:
            memory_size = self.memory_queue.qsize()
            
            file_size = 0
            if self.queue_file.exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_size = len(data.get("messages", []))
            
            return memory_size + file_size
            
        except Exception as e:
            self.logger.error(f"获取队列大小失败: {e}")
            return 0


# 全局消息队列实例
_global_message_queue: Optional[MessageQueue] = None

def get_message_queue() -> MessageQueue:
    """获取全局消息队列实例"""
    global _global_message_queue
    if _global_message_queue is None:
        _global_message_queue = MessageQueue()
    return _global_message_queue

def send_message(message_type: str, data: Dict[str, Any], priority: int = 1) -> bool:
    """便捷的发送消息函数"""
    return get_message_queue().send_message(message_type, data, priority)

def receive_message(timeout: float = 0.1) -> Optional[Dict[str, Any]]:
    """便捷的接收消息函数"""
    return get_message_queue().receive_message(timeout)

def register_handler(message_type: str, handler: Callable):
    """便捷的注册处理器函数"""
    get_message_queue().register_handler(message_type, handler)

def start_message_listener():
    """启动消息监听器"""
    get_message_queue().start_listener()

def stop_message_listener():
    """停止消息监听器"""
    get_message_queue().stop_listener()

def clear_message_queue():
    """清空消息队列"""
    get_message_queue().clear_queue()
