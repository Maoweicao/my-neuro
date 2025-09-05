#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试消息队列集成
验证main.py和UI.py之间的消息队列通信是否正常工作
"""

import time
import threading
import os
import sys
from utils.message_queue import MessageQueue

def test_message_queue_basic():
    """测试基本消息队列功能"""
    print("=== 测试基本消息队列功能 ===")
    
    # 创建消息队列实例
    mq = MessageQueue()
    
    # 测试发送消息
    test_message = {
        "text": "测试消息",
        "timestamp": time.time()
    }
    
    success = mq.send_message("test", test_message, priority=1)
    print(f"发送测试消息: {'成功' if success else '失败'}")
    
    # 测试接收消息
    received = mq.receive_message()
    if received:
        print(f"接收到消息: {received}")
        print(f"消息类型: {received['type']}")
        print(f"消息数据: {received['data']}")
    else:
        print("未接收到消息")
    
    print()

def test_message_handlers():
    """测试消息处理器"""
    print("=== 测试消息处理器 ===")
    
    # 创建消息队列实例
    mq = MessageQueue()
    
    # 定义处理器
    def test_handler(data):
        print(f"处理器收到数据: {data}")
        return True
    
    def interrupt_handler(data):
        print(f"中断处理器收到数据: {data}")
        return True
    
    # 注册处理器
    mq.register_handler("test", test_handler)
    mq.register_handler("interrupt", interrupt_handler)
    
    # 启动监听器
    listener_thread = threading.Thread(target=mq.start_listener, daemon=True)
    listener_thread.start()
    
    # 发送测试消息
    time.sleep(0.1)  # 等待监听器启动
    
    mq.send_message("test", {"action": "test_action"})
    mq.send_message("interrupt", {"action": "stop_audio"})
    
    # 等待处理完成
    time.sleep(1)
    
    print()

def test_priority_queue():
    """测试优先级队列"""
    print("=== 测试优先级队列 ===")
    
    mq = MessageQueue()
    
    # 发送不同优先级的消息
    mq.send_message("low", {"priority": "low"}, priority=3)
    mq.send_message("high", {"priority": "high"}, priority=1)
    mq.send_message("medium", {"priority": "medium"}, priority=2)
    
    # 接收消息，应该按优先级顺序
    for i in range(3):
        msg = mq.receive_message()
        if msg:
            print(f"接收消息 {i+1}: {msg['type']}, 优先级: {msg['priority']}")
    
    print()

def test_file_persistence():
    """测试文件持久化"""
    print("=== 测试文件持久化 ===")
    
    # 删除现有的消息队列文件
    queue_file = "message_queue.json"
    if os.path.exists(queue_file):
        os.remove(queue_file)
    
    # 创建第一个实例并发送消息
    mq1 = MessageQueue()
    mq1.send_message("persistent", {"data": "持久化测试"})
    
    # 创建第二个实例，应该能读取到消息
    mq2 = MessageQueue()
    msg = mq2.receive_message()
    
    if msg and msg['type'] == 'persistent':
        print("✓ 文件持久化测试成功")
    else:
        print("✗ 文件持久化测试失败")
    
    print()

def main():
    """主测试函数"""
    print("开始测试消息队列集成...")
    print()
    
    try:
        test_message_queue_basic()
        test_priority_queue()
        test_file_persistence()
        test_message_handlers()
        
        print("=== 测试完成 ===")
        print("如果所有测试都通过，说明消息队列系统工作正常")
        print("现在可以启动main.py和UI.py来测试完整的集成")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
