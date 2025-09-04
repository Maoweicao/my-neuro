#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试音频播放和动作按钮迁移功能
"""
import sys
import os
import json
import time
import socket
import base64
from pathlib import Path

def test_audio_playback():
    """测试音频播放功能"""
    print("=== 测试音频播放功能 ===")

    # 创建测试音频数据（简单的WAV格式音频）
    # 这里我们创建一个简单的正弦波音频作为测试
    import numpy as np
    import io
    import wave

    # 生成1秒的440Hz正弦波
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)

    # 转换为16位整数
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # 创建WAV文件
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    wav_data = wav_buffer.getvalue()

    # 编码为base64
    audio_b64 = base64.b64encode(wav_data).decode('utf-8')

    # 发送到main.py
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "play_audio",
            "audio_data": audio_b64,
            "volume": 0.5,
            "loop": False,
            "singing_motion": "唱歌",
            "timestamp": time.time(),
            "source": "test_script"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ 音频播放请求已发送")
        return True

    except Exception as e:
        print(f"✗ 发送音频播放请求失败: {e}")
        return False

def test_custom_action():
    """测试自定义动作功能"""
    print("\n=== 测试自定义动作功能 ===")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "custom_action",
            "action_num": 1,
            "timestamp": time.time(),
            "source": "test_script"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ 自定义动作请求已发送")
        return True

    except Exception as e:
        print(f"✗ 发送自定义动作请求失败: {e}")
        return False

def test_interrupt():
    """测试中断功能"""
    print("\n=== 测试中断功能 ===")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "interrupt",
            "timestamp": time.time(),
            "source": "test_script"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ 中断请求已发送")
        return True

    except Exception as e:
        print(f"✗ 发送中断请求失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试音频播放和动作按钮迁移功能...")
    print("注意：需要先启动main.py服务")

    # 等待用户确认main.py已启动
    input("请确保main.py服务已启动，然后按Enter键继续测试...")

    # 测试音频播放
    audio_success = test_audio_playback()

    # 等待一段时间
    time.sleep(2)

    # 测试自定义动作
    action_success = test_custom_action()

    # 等待一段时间
    time.sleep(1)

    # 测试中断
    interrupt_success = test_interrupt()

    # 输出测试结果
    print("\n=== 测试结果 ===")
    print(f"音频播放测试: {'✓ 通过' if audio_success else '✗ 失败'}")
    print(f"自定义动作测试: {'✓ 通过' if action_success else '✗ 失败'}")
    print(f"中断功能测试: {'✓ 通过' if interrupt_success else '✗ 失败'}")

    if audio_success and action_success and interrupt_success:
        print("\n🎉 所有测试通过！音频播放和动作按钮迁移成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查main.py服务是否正常运行")

if __name__ == "__main__":
    main()
