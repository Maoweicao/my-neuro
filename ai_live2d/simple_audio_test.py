#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单音频测试
"""

import base64
import numpy as np
import io
import wave

def test_audio():
    print("=== 简单音频测试 ===")

    # 创建测试音频
    duration = 2.0
    frequency = 440.0
    sample_rate = 44100

    print("1. 创建测试音频...")
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # 创建WAV文件
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    wav_data = buffer.getvalue()
    print(f"   WAV数据大小: {len(wav_data)} bytes")
    print(f"   前16字节: {wav_data[:16]}")

    # 编码为base64
    print("\n2. 编码为base64...")
    base64_data = base64.b64encode(wav_data).decode('utf-8')
    print(f"   Base64长度: {len(base64_data)} 字符")

    # 解码base64
    print("\n3. 解码base64...")
    decoded = base64.b64decode(base64_data)
    print(f"   解码后大小: {len(decoded)} bytes")
    print(f"   解码后前16字节: {decoded[:16]}")

    # 验证是否以RIFF开头
    print("\n4. 验证WAV格式...")
    if decoded[:4] == b'RIFF':
        print("   ✅ 解码后数据以RIFF开头，是有效的WAV格式")
    else:
        print("   ❌ 解码后数据不以RIFF开头，不是有效的WAV格式")

    # 测试wave.open
    print("\n5. 测试wave.open...")
    try:
        with io.BytesIO(decoded) as wav_io:
            with wave.open(wav_io, 'rb') as wave_file:
                print(f"   声道数: {wave_file.getnchannels()}")
                print(f"   采样率: {wave_file.getframerate()}")
                print(f"   帧数: {wave_file.getnframes()}")
        print("   ✅ wave.open成功")
    except Exception as e:
        print(f"   ❌ wave.open失败: {e}")

if __name__ == "__main__":
    test_audio()
