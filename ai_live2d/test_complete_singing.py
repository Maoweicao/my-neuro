#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的唱歌API测试
"""

import requests
import base64
import numpy as np
import io
import wave
import time
import threading

def create_test_audio_base64(duration=2.0, frequency=440.0, sample_rate=44100):
    """创建测试音频的base64编码"""
    # 生成正弦波
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)

    # 转换为16位整数
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # 创建WAV文件缓冲区
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    # 获取WAV数据并编码为base64
    wav_data = buffer.getvalue()
    return base64.b64encode(wav_data).decode('utf-8')

def test_webapi_status():
    """测试WebAPI状态"""
    print("=== 测试WebAPI状态 ===")
    try:
        response = requests.get("http://127.0.0.1:8888/api/status", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"响应: {response.json()}")
            return True
        else:
            print(f"错误响应: {response.text}")
            return False
    except Exception as e:
        print(f"连接失败: {e}")
        return False

def test_singing_api():
    """测试唱歌API"""
    print("\n=== 测试唱歌API ===")

    # 创建测试音频
    audio_base64 = create_test_audio_base64(duration=3.0, frequency=440.0)
    print(f"创建了 {len(audio_base64)} 字符的base64音频数据")

    # 发送唱歌请求
    url = "http://127.0.0.1:8888/api/sing"
    data = {
        "audio_base64": audio_base64,
        "volume": 0.8,
        "loop": False,
        "singing_motion": "唱歌"
    }

    print("发送唱歌请求...")
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"响应内容: {result}")
            print("✅ 唱歌请求成功处理")
            return True
        else:
            error_result = response.json()
            print(f"错误: {error_result}")
            return False
    except Exception as e:
        print(f"请求失败: {e}")
        return False

def test_interrupt_api():
    """测试中断API"""
    print("\n=== 测试中断API ===")

    url = "http://127.0.0.1:8888/api/interrupt"
    data = {}

    print("发送中断请求...")
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"响应内容: {result}")
            print("✅ 中断请求成功处理")
            return True
        else:
            error_result = response.json()
            print(f"错误: {error_result}")
            return False
    except Exception as e:
        print(f"请求失败: {e}")
        return False

def run_tests():
    """运行所有测试"""
    print("开始完整的WebAPI测试...")

    # 测试状态
    if not test_webapi_status():
        print("❌ WebAPI服务器未运行，测试终止")
        return

    # 测试唱歌API
    if test_singing_api():
        print("等待音频播放完成...")
        time.sleep(4)  # 等待3秒音频播放

    # 测试中断API
    test_interrupt_api()

    print("\n🎉 所有测试完成！")

if __name__ == "__main__":
    run_tests()
