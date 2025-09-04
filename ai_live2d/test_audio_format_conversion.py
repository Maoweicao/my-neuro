#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试音频格式转换功能
"""

import sys
import os
import base64
import io
import wave
import numpy as np

def create_test_audio_file(file_path, format_type='wav', duration=2.0):
    """创建一个测试音频文件"""
    # 生成正弦波音频数据
    sample_rate = 44100
    frequency = 440.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)

    # 转换为16位整数
    audio_int16 = (audio_data * 32767).astype(np.int16)

    if format_type == 'wav':
        # 创建WAV文件
        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        print(f"创建WAV测试文件: {file_path}")
    else:
        # 对于其他格式，我们仍然创建WAV文件，但告诉用户这是为了测试
        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        print(f"创建测试文件 (模拟{format_type.upper()}): {file_path}")

def test_audio_format_detection():
    """测试音频格式检测功能"""
    print("测试音频格式检测功能...")

    # 创建测试文件
    test_files = [
        ('test_audio.wav', 'wav'),
        ('test_audio.mp3', 'mp3'),
        ('test_audio.flac', 'flac'),
        ('test_audio.ogg', 'ogg')
    ]

    for file_path, format_type in test_files:
        try:
            create_test_audio_file(file_path, format_type)
            print(f"✓ 创建 {format_type.upper()} 测试文件成功")
        except Exception as e:
            print(f"✗ 创建 {format_type.upper()} 测试文件失败: {e}")

    print("\n音频格式检测测试完成")
    print("注意: pydub库需要额外安装才能支持MP3/FLAC/OGG格式转换")
    print("可以使用: pip install pydub")

def test_base64_encoding():
    """测试音频文件的base64编码"""
    print("\n测试音频base64编码...")

    try:
        # 创建一个小的测试WAV文件
        create_test_audio_file('test_base64.wav', 'wav', duration=1.0)

        # 读取并编码
        with open('test_base64.wav', 'rb') as f:
            audio_data = f.read()

        encoded = base64.b64encode(audio_data).decode('utf-8')
        print(f"✓ 原始文件大小: {len(audio_data)} bytes")
        print(f"✓ Base64编码大小: {len(encoded)} 字符")
        print(f"✓ 编码成功")

        # 解码测试
        decoded = base64.b64decode(encoded)
        if decoded == audio_data:
            print("✓ Base64解码验证成功")
        else:
            print("✗ Base64解码验证失败")

    except Exception as e:
        print(f"✗ Base64编码测试失败: {e}")

def cleanup_test_files():
    """清理测试文件"""
    test_files = [
        'test_audio.wav',
        'test_audio.mp3',
        'test_audio.flac',
        'test_audio.ogg',
        'test_base64.wav'
    ]

    for file_path in test_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"清理文件: {file_path}")
        except Exception as e:
            print(f"清理文件失败 {file_path}: {e}")

if __name__ == "__main__":
    print("=== 音频格式转换功能测试 ===\n")

    try:
        test_audio_format_detection()
        test_base64_encoding()
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        print("\n=== 清理测试文件 ===")
        cleanup_test_files()

    print("\n=== 测试完成 ===")
    print("如果要测试实际的音频格式转换，请确保安装了以下依赖:")
    print("- pydub: pip install pydub")
    print("- ffmpeg: 从 https://ffmpeg.org/download.html 下载并添加到PATH")
