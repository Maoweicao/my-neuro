#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的唱歌API测试脚本
"""

import requests
import json
import base64
import io
import wave
import numpy as np

def create_test_audio():
    """创建测试音频"""
    # 生成简单的正弦波
    sample_rate = 44100
    duration = 2.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # 创建WAV
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    wav_data = buffer.getvalue()
    return base64.b64encode(wav_data).decode('utf-8')

def test_singing():
    """测试唱歌接口"""
    url = "http://127.0.0.1:8888/api/sing"

    # 创建测试音频
    audio_base64 = create_test_audio()

    data = {
        "audio_base64": audio_base64,
        "volume": 0.8,
        "loop": False,
        "singing_motion": "唱歌"
    }

    try:
        print("发送唱歌请求...")
        response = requests.post(url, json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_singing()
