#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试唱歌接口的多格式音频支持
"""

import requests
import base64
import json
import os

def test_singing_api():
    """测试唱歌API的多格式支持"""

    # 测试用的音频文件路径（需要用户提供）
    test_files = {
        'wav': 'test_audio.wav',
        'mp3': 'test_audio.mp3',
        'flac': 'test_audio.flac'
    }

    api_url = 'http://127.0.0.1:8888/api/sing'

    for format_name, file_path in test_files.items():
        if os.path.exists(file_path):
            print(f"\n测试 {format_name.upper()} 格式...")

            # 读取音频文件
            with open(file_path, 'rb') as f:
                audio_data = f.read()

            # 转换为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # 构建请求数据
            request_data = {
                'audio_base64': audio_base64,
                'format': format_name,
                'volume': 1.0,
                'loop': False,
                'singing_motion': '唱歌'
            }

            try:
                # 发送请求
                response = requests.post(api_url, json=request_data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {format_name.upper()} 格式测试成功: {result.get('message', 'OK')}")
                else:
                    print(f"❌ {format_name.upper()} 格式测试失败: HTTP {response.status_code}")
                    print(f"错误信息: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"❌ {format_name.upper()} 格式网络请求失败: {e}")
        else:
            print(f"⚠️  测试文件不存在: {file_path}")

if __name__ == '__main__':
    print("唱歌接口多格式音频支持测试")
    print("=" * 40)
    test_singing_api()
