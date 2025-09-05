#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的音频播放验证脚本
"""
import sys
import os
import io
import wave
import numpy as np
import time

def create_test_sound(frequency=440, duration=2.0):
    """创建测试音频"""
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(frequency * 2 * np.pi * t)
    audio_data = (wave_data * 32767).astype(np.int16)
    
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return wav_buffer.getvalue()

def main():
    print("🎵 测试main.py音频播放修复效果...")
    
    try:
        # 导入修复后的main模块
        from main import PetService
        
        # 创建服务实例
        service = PetService()
        service._stop_singing = False
        service.current_audio_stream = None
        service.lrc_manager = None
        service.app_manager = None
        
        # 创建简单的日志记录器
        import logging
        logging.basicConfig(level=logging.INFO)
        service.logger = logging.getLogger("test")
        
        print("🔊 创建测试音频 (440Hz A音, 2秒)...")
        audio_data = create_test_sound(440, 2.0)
        
        print("▶️ 开始播放音频...")
        service.play_singing_audio(audio_data, volume=0.7, loop=False, singing_motion="唱歌")
        
        print("⏳ 等待播放完成 (3秒)...")
        time.sleep(3)
        
        print("✅ 音频播放测试完成！")
        print("\n如果您听到了440Hz的蜂鸣声，说明音频播放修复成功！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
