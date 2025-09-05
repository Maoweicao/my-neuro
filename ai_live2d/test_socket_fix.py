#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Socket通信修复验证脚本
"""

import socket
import json
import base64
import time

def test_socket_communication():
    """测试socket通信"""
    print("🔌 测试Socket通信修复...")
    
    # 创建测试音频数据
    test_audio = b"RIFF\x24\x00\x00\x00WAVE"  # 简单的WAV头
    audio_base64 = base64.b64encode(test_audio).decode('utf-8')
    
    # 测试数据
    signal_data = {
        "type": "play_audio",
        "audio_data": audio_base64,
        "volume": 0.5,
        "loop": False,
        "singing_motion": "唱歌",
        "timestamp": time.time(),
        "source": "test"
    }
    
    try:
        # 创建socket连接
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))
        
        # 将数据编码为JSON字节
        json_data = json.dumps(signal_data).encode('utf-8')
        data_length = len(json_data)
        
        print(f"📦 发送数据长度: {data_length} 字节")
        
        # 先发送数据长度（4字节，大端序）
        length_bytes = data_length.to_bytes(4, byteorder='big')
        client_socket.send(length_bytes)
        
        # 然后发送实际数据
        sent = 0
        while sent < data_length:
            chunk_size = min(8192, data_length - sent)
            chunk = json_data[sent:sent + chunk_size]
            bytes_sent = client_socket.send(chunk)
            sent += bytes_sent
            print(f"📤 已发送: {sent}/{data_length} 字节")
        
        client_socket.close()
        print("✅ Socket通信测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ Socket通信测试失败: {e}")
        return False

def test_small_data():
    """测试小数据传输"""
    print("\n📝 测试小数据传输...")
    
    signal_data = {
        "type": "show_subtitle",
        "text": "测试字幕",
        "source": "test",
        "timestamp": time.time()
    }
    
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3.0)
        client_socket.connect(('127.0.0.1', 8889))
        
        json_data = json.dumps(signal_data).encode('utf-8')
        data_length = len(json_data)
        
        print(f"📦 发送小数据长度: {data_length} 字节")
        
        # 发送长度和数据
        length_bytes = data_length.to_bytes(4, byteorder='big')
        client_socket.send(length_bytes)
        client_socket.send(json_data)
        
        client_socket.close()
        print("✅ 小数据传输测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 小数据传输测试失败: {e}")
        return False

def main():
    print("🚀 Socket通信修复验证")
    print("=" * 40)
    
    print("请确保main.py正在运行...")
    time.sleep(1)
    
    # 测试小数据
    test_small_data()
    
    # 测试大数据（音频）
    test_socket_communication()
    
    print("\n🎉 Socket通信测试完成！")
    print("如果看到成功消息，说明socket通信修复有效")

if __name__ == "__main__":
    main()
