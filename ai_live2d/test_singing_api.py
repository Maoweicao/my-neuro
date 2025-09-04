#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
唱歌功能WebAPI测试脚本
用于测试唱歌WebAPI功能是否正常工作
"""

import requests
import json
import base64
import io
import wave
import numpy as np
import time

def create_test_audio_base64(duration=2.0, frequency=440.0, sample_rate=44100):
    """创建一个简单的测试音频（正弦波）并转换为base64"""
    # 生成正弦波音频数据
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
    audio_base64 = base64.b64encode(wav_data).decode('utf-8')

    return audio_base64

def test_singing_api(host='127.0.0.1', port=8888, api_key=None):
    """测试唱歌API功能"""
    url = f"http://{host}:{port}/api/sing"

    # 创建测试音频
    print("生成测试音频...")
    audio_base64 = create_test_audio_base64(duration=3.0, frequency=440.0)

    # 测试数据
    test_cases = [
        {
            "name": "基本唱歌测试",
            "data": {
                "audio_base64": audio_base64,
                "volume": 0.8,
                "loop": False,
                "singing_motion": "唱歌"
            }
        },
        {
            "name": "循环播放测试",
            "data": {
                "audio_base64": audio_base64,
                "volume": 1.0,
                "loop": True,
                "singing_motion": "唱歌"
            }
        },
        {
            "name": "自定义动作测试",
            "data": {
                "audio_base64": audio_base64,
                "volume": 0.6,
                "loop": False,
                "singing_motion": "开始唱歌"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")

        data = test_case['data'].copy()
        if api_key:
            data["api_key"] = api_key

        try:
            print("发送唱歌请求...")
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("响应内容:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

                if result.get('status') == 'success':
                    print("✅ 唱歌请求成功")
                else:
                    print("❌ 唱歌请求失败")
            else:
                print(f"❌ 请求失败: {response.text}")

        except requests.exceptions.Timeout:
            print("⏰ 请求超时 - 可能是因为音频播放需要时间")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

        # 等待一段时间再进行下一个测试
        time.sleep(1)

def test_invalid_requests(host='127.0.0.1', port=8888, api_key=None):
    """测试无效请求的错误处理"""
    url = f"http://{host}:{port}/api/sing"

    print("\n=== 测试无效请求 ===")

    # 测试缺少audio_base64字段
    print("\n测试缺少audio_base64字段:")
    data = {"volume": 0.8}
    if api_key:
        data["api_key"] = api_key

    try:
        response = requests.post(
            url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求异常: {e}")

    # 测试无效的音量值
    print("\n测试无效音量值:")
    audio_base64 = create_test_audio_base64(duration=1.0)
    data = {
        "audio_base64": audio_base64,
        "volume": 1.5  # 无效的音量值
    }
    if api_key:
        data["api_key"] = api_key

    try:
        response = requests.post(
            url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求异常: {e}")

def main():
    """主函数"""
    print("🎵 唱歌功能WebAPI测试脚本")
    print("=" * 50)

    # 配置参数
    host = '127.0.0.1'
    port = 8888
    api_key = None  # 如果需要API密钥，请设置这里

    print(f"目标服务器: http://{host}:{port}")
    print(f"API密钥: {'已设置' if api_key else '未设置'}")
    print()

    # 首先检查服务状态
    print("检查WebAPI服务状态...")
    try:
        response = requests.get(f"http://{host}:{port}/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ WebAPI服务正在运行")
        else:
            print("❌ WebAPI服务状态异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到WebAPI服务: {e}")
        print("请确保应用程序已启动且WebAPI功能已启用")
        return

    # 测试唱歌功能
    test_singing_api(host, port, api_key)

    # 测试错误处理
    test_invalid_requests(host, port, api_key)

    print("\n" + "=" * 50)
    print("🎵 测试完成")

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">f:\my-neuro\ai_live2d\test_singing_api.py
