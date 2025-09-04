#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试音频播放停止功能
"""

import socket
import json
import time

def test_audio_stop():
    """测试音频停止功能"""
    print("🧪 测试音频停止功能...")

    try:
        # 发送中断信号
        print("📤 发送中断信号...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "interrupt",
            "timestamp": time.time()
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()
        print("✅ 中断信号发送成功")

        print("🎉 音频停止功能测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_audio_stop()
