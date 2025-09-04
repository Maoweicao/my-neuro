#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试唱歌音频解码问题
"""

import base64
import numpy as np
import io
import wave
import sounddevice as sd

def create_test_audio_base64(duration=2.0, frequency=440.0, sample_rate=44100):
    """创建测试音频的base64编码"""
    print(f"创建测试音频: 持续时间={duration}s, 频率={frequency}Hz, 采样率={sample_rate}Hz")

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
    print(f"WAV数据大小: {len(wav_data)} bytes")

    # 验证WAV数据的有效性
    buffer.seek(0)
    with wave.open(buffer, 'rb') as verify_wav:
        print(f"验证WAV: 声道={verify_wav.getnchannels()}, 采样率={verify_wav.getframerate()}, 帧数={verify_wav.getnframes()}")

    base64_data = base64.b64encode(wav_data).decode('utf-8')
    print(f"Base64数据长度: {len(base64_data)} 字符")
    return base64_data

def test_audio_decode_and_play(audio_base64):
    """测试音频解码和播放"""
    print("\n=== 测试音频解码和播放 ===")

    try:
        # 解码base64
        print("1. 解码base64数据...")
        audio_data = base64.b64decode(audio_base64)
        print(f"   解码后大小: {len(audio_data)} bytes")

        # 检查前几个字节（应该以RIFF开头）
        print(f"   前16字节: {audio_data[:16]}")
        if audio_data[:4] == b'RIFF':
            print("   ✅ 数据以RIFF开头，是有效的WAV格式")
        else:
            print("   ❌ 数据不以RIFF开头，不是有效的WAV格式")
            return False

        # 尝试用wave模块打开
        print("\n2. 尝试用wave模块解析...")
        with io.BytesIO(audio_data) as wav_io:
            with wave.open(wav_io, 'rb') as wave_file:
                sample_width = wave_file.getsampwidth()
                channels = wave_file.getnchannels()
                framerate = wave_file.getframerate()
                num_frames = wave_file.getnframes()
                frames = wave_file.readframes(num_frames)

                print(f"   声道数: {channels}")
                print(f"   采样宽度: {sample_width} bytes")
                print(f"   采样率: {framerate} Hz")
                print(f"   帧数: {num_frames}")
                print(f"   音频数据大小: {len(frames)} bytes")

        # 转换为numpy数组进行播放测试
        print("\n3. 转换为numpy数组...")
        dtype = np.int16 if sample_width == 2 else np.int8
        audio_array = np.frombuffer(frames, dtype=dtype)
        audio_float = audio_array.astype(np.float32) / 32767.0

        if channels > 1:
            audio_float = audio_float.reshape(-1, channels)

        print(f"   音频数组形状: {audio_float.shape}")
        print(f"   音频数据类型: {audio_float.dtype}")
        print(f"   音频数据范围: {audio_float.min():.3f} 到 {audio_float.max():.3f}")

        # 测试播放（可选）
        print("\n4. 测试音频播放...")
        try:
            sd.play(audio_float, samplerate=framerate, blocking=False)
            print("   播放开始...")
            import time
            time.sleep(1.0)  # 播放1秒
            sd.stop()
            print("   播放停止")
        except Exception as e:
            print(f"   播放失败: {e}")

        print("\n✅ 音频解码和播放测试成功")
        return True

    except Exception as e:
        print(f"❌ 音频解码测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 创建测试音频
    audio_base64 = create_test_audio_base64()

    # 测试解码和播放
    success = test_audio_decode_and_play(audio_base64)

    if success:
        print("\n🎉 所有测试通过！音频处理逻辑正确。")
    else:
        print("\n❌ 测试失败！需要修复音频处理逻辑。")
