#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试WebAPI详细日志功能
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
    buffer.seek(0)  # 重置缓冲区位置
    wav_data = buffer.getvalue()

    # 验证WAV数据的有效性
    print(f"创建的WAV数据大小: {len(wav_data)} bytes")
    if len(wav_data) > 16:
        print(f"WAV文件头: {wav_data[:16]}")
        if wav_data[:4] == b'RIFF':
            print("✅ WAV文件头正确")
        else:
            print("❌ WAV文件头不正确")

    return base64.b64encode(wav_data).decode('utf-8')

def test_webapi_with_logging():
    """测试WebAPI的详细日志功能"""
    print("=== 测试WebAPI详细日志功能 ===\n")

    # 测试状态
    print("1. 测试WebAPI状态...")
    try:
        response = requests.get("http://127.0.0.1:8888/api/status", timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.json()}")
            print("   ✅ WebAPI服务器运行正常")
        else:
            print(f"   错误响应: {response.text}")
            return False
    except Exception as e:
        print(f"   连接失败: {e}")
        return False

    time.sleep(1)

    # 测试聊天API
    print("\n2. 测试聊天API...")
    try:
        data = {"message": "你好，测试一下详细日志功能"}
        response = requests.post("http://127.0.0.1:8888/api/chat", json=data, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   响应: {result}")
            print("   ✅ 聊天API测试成功")
        else:
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")

    time.sleep(1)

    # 测试台词转换API
    print("\n3. 测试台词转换API...")
    try:
        data = {"dialogue": "我喜欢唱歌"}
        response = requests.post("http://127.0.0.1:8888/api/dialogue", json=data, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   原始台词: {result.get('original_dialogue', '')}")
            print(f"   转换后: {result.get('converted_dialogue', '')}")
            print("   ✅ 台词转换API测试成功")
        else:
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")

    time.sleep(1)

    # 测试唱歌API（重点测试详细日志）
    print("\n4. 测试唱歌API（详细日志）...")
    try:
        audio_base64 = create_test_audio_base64(duration=2.0, frequency=440.0)
        print(f"   创建了 {len(audio_base64)} 字符的测试音频")

        data = {
            "audio_base64": audio_base64,
            "volume": 0.8,
            "loop": False,
            "singing_motion": "唱歌"
        }

        print("   发送唱歌请求...")
        response = requests.post("http://127.0.0.1:8888/api/sing", json=data, timeout=15)
        print(f"   状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   响应: {result}")
            print("   ✅ 唱歌API测试成功")
            print("   等待音频播放完成...")
            time.sleep(3)  # 等待音频播放
        else:
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")

    time.sleep(1)

    # 测试中断API
    print("\n5. 测试中断API...")
    try:
        data = {}
        response = requests.post("http://127.0.0.1:8888/api/interrupt", json=data, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   响应: {result}")
            print("   ✅ 中断API测试成功")
        else:
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")

    print("\n🎉 所有测试完成！")
    print("\n请检查 logs/webapi_interactions.log 文件查看详细日志记录")
    print("唱歌功能的每一步处理都会有详细的日志记录")

    return True

if __name__ == "__main__":
    test_webapi_with_logging()
