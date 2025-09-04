#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
字幕显示功能测试脚本
"""

import socket
import json
import time

def test_subtitle_display():
    """测试字幕显示功能"""
    print("🧪 测试字幕显示功能...")

    try:
        # 测试台词字幕
        print("📝 测试台词字幕...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "show_subtitle",
            "text": "你好，这是一个测试台词！",
            "source": "dialogue",
            "timestamp": time.time()
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()
        print("✅ 台词字幕测试完成")

        time.sleep(2)  # 等待2秒

        # 测试唱歌字幕
        print("🎵 测试唱歌字幕...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "show_subtitle",
            "text": "♪ 唱歌中 ♫",
            "source": "singing",
            "timestamp": time.time()
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()
        print("✅ 唱歌字幕测试完成")

        print("🎉 字幕显示功能测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_subtitle_display()
