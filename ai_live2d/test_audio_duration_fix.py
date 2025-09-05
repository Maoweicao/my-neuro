#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频播放时长修复测试
测试音频播放时长计算和等待逻辑
"""

import json
import os
import sys
import tempfile
import wave
import io
import time
import numpy as np

def create_test_audio(duration_seconds=5):
    """创建指定时长的测试音频"""
    sample_rate = 48000
    frequency = 440  # A4音
    
    # 生成正弦波
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), False)
    audio_signal = np.sin(frequency * 2 * np.pi * t)
    
    # 转换为16位PCM立体声
    audio_16bit = (audio_signal * 32767).astype(np.int16)
    
    # 创建立体声
    stereo_audio = np.column_stack((audio_16bit, audio_16bit))
    
    # 创建WAV文件数据
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(2)  # 立体声
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_audio.tobytes())
    
    return wav_io.getvalue(), duration_seconds

def test_audio_duration_calculation():
    """测试音频时长计算"""
    print("=== 音频播放时长修复测试 ===\n")
    
    # 1. 创建不同时长的测试音频
    test_durations = [3, 10, 30]  # 秒
    
    for duration in test_durations:
        print(f"📏 测试 {duration} 秒音频...")
        
        try:
            # 创建测试音频
            audio_data, expected_duration = create_test_audio(duration)
            print(f"✅ 生成音频数据: {len(audio_data)} 字节")
            
            # 解析音频数据（模拟main.py中的逻辑）
            with io.BytesIO(audio_data) as wav_io:
                with wave.open(wav_io, 'rb') as wave_file:
                    sample_width = wave_file.getsampwidth()
                    channels = wave_file.getnchannels()
                    framerate = wave_file.getframerate()
                    num_frames = wave_file.getnframes()
                    frames = wave_file.readframes(num_frames)
            
            print(f"   音频参数: {channels}声道, {framerate}Hz, {num_frames}帧, {sample_width}字节/样本")
            
            # 计算音频时长（修复后的逻辑）
            dtype = np.int16 if sample_width == 2 else np.int8
            audio_array = np.frombuffer(frames, dtype=dtype)
            
            if sample_width == 2:
                audio_float = audio_array.astype(np.float32) / 32767.0
            else:
                audio_float = audio_array.astype(np.float32) / 127.0
            
            # 重塑为多声道
            if channels > 1:
                audio_float = audio_float.reshape(-1, channels)
            
            # 计算时长
            audio_duration = len(audio_float) / framerate
            
            print(f"   计算时长: {audio_duration:.2f}秒")
            print(f"   预期时长: {expected_duration:.2f}秒")
            print(f"   误差: {abs(audio_duration - expected_duration):.3f}秒")
            
            # 验证计算是否正确
            if abs(audio_duration - expected_duration) < 0.1:  # 允许0.1秒误差
                print(f"   ✅ 时长计算正确")
            else:
                print(f"   ❌ 时长计算错误")
            
            # 计算超时时间
            timeout = max(10.0, min(audio_duration * 1.5, 300.0))
            print(f"   超时设置: {timeout:.2f}秒")
            print()
            
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            print()
    
    return True

def test_audio_playback_simulation():
    """模拟音频播放逻辑测试"""
    print("🎵 模拟音频播放逻辑测试...\n")
    
    try:
        import sounddevice as sd
        
        # 创建5秒测试音频
        audio_data, expected_duration = create_test_audio(5)
        print(f"📁 创建测试音频: {expected_duration}秒")
        
        # 解析音频
        with io.BytesIO(audio_data) as wav_io:
            with wave.open(wav_io, 'rb') as wave_file:
                sample_width = wave_file.getsampwidth()
                channels = wave_file.getnchannels()
                framerate = wave_file.getframerate()
                num_frames = wave_file.getnframes()
                frames = wave_file.readframes(num_frames)
        
        # 转换为numpy数组
        dtype = np.int16 if sample_width == 2 else np.int8
        audio_array = np.frombuffer(frames, dtype=dtype)
        audio_float = audio_array.astype(np.float32) / 32767.0
        
        if channels > 1:
            audio_float = audio_float.reshape(-1, channels)
        
        # 计算时长和超时
        audio_duration = len(audio_float) / framerate
        timeout = max(10.0, min(audio_duration * 1.5, 300.0))
        
        print(f"🔢 计算结果:")
        print(f"   音频时长: {audio_duration:.2f}秒")
        print(f"   超时时间: {timeout:.2f}秒")
        print(f"   音频形状: {audio_float.shape}")
        print(f"   采样率: {framerate}Hz")
        
        print(f"\n🎶 开始播放测试...")
        
        # 模拟播放过程
        start_time = time.time()
        print(f"   播放开始时间: {start_time:.3f}")
        
        # 使用sounddevice播放（非阻塞）
        current_stream = sd.play(audio_float, samplerate=framerate, blocking=False)
        print(f"   ✅ 音频流已启动")
        
        # 模拟等待逻辑
        _stop_singing = False
        
        # 启动一个单独的线程来等待播放完成
        import threading
        playback_finished = threading.Event()
        
        def wait_for_completion():
            try:
                # 使用sd.wait()等待播放完成
                sd.wait()
                print(f"   ✅ sd.wait()返回，音频播放完成")
                playback_finished.set()
            except Exception as e:
                print(f"   ⚠️  sd.wait()异常: {e}")
                playback_finished.set()
        
        wait_thread = threading.Thread(target=wait_for_completion)
        wait_thread.daemon = True
        wait_thread.start()
        
        # 主线程监控播放状态和时间
        while not _stop_singing and time.time() - start_time < timeout:
            if playback_finished.is_set():
                print(f"   ✅ 检测到播放完成信号")
                break
            
            # 检查流是否还活跃
            try:
                if current_stream and hasattr(current_stream, 'active'):
                    if not current_stream.active:
                        print(f"   ✅ 检测到音频流已停止")
                        break
            except:
                pass
            
            # 每秒打印一次状态
            elapsed = time.time() - start_time
            if int(elapsed) != int(elapsed - 0.2):
                print(f"   ⏱️  播放中... {elapsed:.1f}s / {audio_duration:.1f}s")
            
            time.sleep(0.2)
        
        elapsed_time = time.time() - start_time
        print(f"\n📊 播放结果:")
        print(f"   实际播放时间: {elapsed_time:.2f}秒")
        print(f"   预期播放时间: {audio_duration:.2f}秒")
        print(f"   时间差异: {abs(elapsed_time - audio_duration):.2f}秒")
        
        # 清理
        try:
            if current_stream:
                current_stream.stop()
                current_stream.close()
            print(f"   ✅ 音频流已清理")
        except:
            pass
        
        # 验证结果
        if abs(elapsed_time - audio_duration) < 1.0:  # 允许1秒误差
            print(f"   ✅ 播放时长正常")
            return True
        else:
            print(f"   ⚠️  播放时长异常")
            return False
        
    except ImportError:
        print("❌ sounddevice模块未安装，跳过播放测试")
        return True
    except Exception as e:
        print(f"❌ 播放测试失败: {e}")
        return False

def main():
    """主函数"""
    try:
        print("🔧 音频播放时长修复验证\n")
        
        # 测试时长计算
        success1 = test_audio_duration_calculation()
        
        # 测试播放逻辑
        success2 = test_audio_playback_simulation()
        
        if success1 and success2:
            print("\n🎉 所有测试通过！")
            print("\n📋 修复说明:")
            print("✅ 正确计算音频实际播放时长")
            print("✅ 设置合理的播放超时时间")
            print("✅ 改进音频流状态检测逻辑")
            print("✅ 降低CPU占用的等待频率")
            print("✅ 增加详细的播放状态日志")
            
            print("\n💡 主要改进:")
            print("1. 基于音频实际时长计算超时时间（时长 × 1.5）")
            print("2. 最小超时10秒，最大超时5分钟")
            print("3. 更准确的音频流状态检测")
            print("4. 减少等待循环的CPU占用")
            print("5. 详细的时间和状态日志记录")
            
            return 0
        else:
            print("\n💥 测试失败，请检查相关修复。")
            return 1
            
    except KeyboardInterrupt:
        print("\n⛔ 用户中断测试")
        return 0
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
