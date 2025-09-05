#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的消息队列测试
验证消息队列基本功能和与main.py的集成
"""

import time
import threading
import json
from utils.message_queue import MessageQueue

def test_main_py_integration():
    """测试与main.py的集成"""
    print("=== 测试与main.py类似的集成 ===")
    
    # 模拟main.py的消息处理
    def interrupt_handler(data):
        print(f"🛑 中断处理器: {data}")
        return True
    
    def audio_handler(data):
        print(f"🔊 音频处理器: {data}")
        return True
    
    def subtitle_handler(data):
        print(f"📝 字幕处理器: {data}")
        return True
    
    # 创建消息队列并注册处理器
    mq = MessageQueue()
    mq.register_handler("interrupt", interrupt_handler)
    mq.register_handler("play_audio", audio_handler)
    mq.register_handler("show_subtitle", subtitle_handler)
    
    # 启动监听器（模拟main.py）
    print("启动消息监听器...")
    listener_thread = threading.Thread(target=mq.start_listener, daemon=True)
    listener_thread.start()
    
    time.sleep(0.2)  # 等待监听器启动
    
    # 模拟UI.py发送的消息
    print("\n模拟UI.py发送消息:")
    
    # 1. 发送中断请求
    mq.send_message("interrupt", {"action": "stop_audio"}, priority=1)
    time.sleep(0.1)
    
    # 2. 发送音频播放请求
    mq.send_message("play_audio", {
        "audio_data": "base64_encoded_audio_data",
        "audio_format": "wav"
    }, priority=2)
    time.sleep(0.1)
    
    # 3. 发送字幕显示请求
    mq.send_message("show_subtitle", {
        "text": "这是一条测试字幕",
        "duration": 3000
    }, priority=2)
    time.sleep(0.1)
    
    print("\n等待消息处理完成...")
    time.sleep(1)

def test_ui_py_integration():
    """测试UI.py类型的消息发送"""
    print("\n=== 测试UI.py类型的消息发送 ===")
    
    mq = MessageQueue()
    
    # 模拟对话响应
    dialogue_message = {
        "type": "play_audio",
        "audio_data": "假设的音频数据",
        "audio_format": "wav",
        "source": "dialogue_api"
    }
    
    success = mq.send_message("play_audio", dialogue_message, priority=1)
    print(f"发送对话音频消息: {'✓ 成功' if success else '✗ 失败'}")
    
    # 模拟唱歌响应
    singing_message = {
        "type": "play_audio", 
        "audio_data": "假设的唱歌音频数据",
        "audio_format": "wav",
        "source": "singing_api"
    }
    
    success = mq.send_message("play_audio", singing_message, priority=1)
    print(f"发送唱歌音频消息: {'✓ 成功' if success else '✗ 失败'}")
    
    # 检查消息是否在队列中
    msg1 = mq.receive_message(timeout=0.1)
    msg2 = mq.receive_message(timeout=0.1)
    
    if msg1:
        print(f"接收到消息1: {msg1['data']['source']}")
    if msg2:
        print(f"接收到消息2: {msg2['data']['source']}")

def main():
    """主测试函数"""
    print("🚀 开始测试消息队列与main.py/UI.py的集成")
    print("=" * 50)
    
    try:
        test_main_py_integration()
        test_ui_py_integration()
        
        print("\n" + "=" * 50)
        print("✅ 消息队列集成测试完成！")
        print("系统已成功从socket通信迁移到消息队列通信")
        print("现在可以启动实际的main.py和UI.py进行完整测试")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
