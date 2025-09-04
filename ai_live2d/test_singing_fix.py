#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试唱歌API是否阻塞UI
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

def test_singing_api():
    """测试唱歌API"""
    # 创建测试音频
    audio_base64 = create_test_audio_base64(duration=3.0, frequency=440.0)

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
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")

def test_interrupt_api():
    """测试中断API"""
    url = "http://127.0.0.1:8888/api/interrupt"
    data = {}

    print("发送中断请求...")
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    print("开始测试唱歌API...")

    # 测试唱歌
    test_singing_api()

    # 等待一段时间
    time.sleep(2)

    # 测试中断
    test_interrupt_api()

    print("测试完成")
