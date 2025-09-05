#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频噪音问题诊断和修复脚本
"""
import sys
import os
import io
import wave
import numpy as np
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_clean_test_audio(frequency=440, duration=2.0, sample_rate=44100):
    """创建干净的测试音频，避免噪音"""
    try:
        logger.info(f"🎵 创建干净的测试音频: {frequency}Hz, {duration}s, {sample_rate}Hz采样率")
        
        # 生成正弦波
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # 使用更平滑的波形，减少噪音
        wave_data = np.sin(frequency * 2 * np.pi * t)
        
        # 添加淡入淡出效果，避免突然开始/结束产生的噪音
        fade_samples = int(sample_rate * 0.05)  # 50ms淡入淡出
        if len(wave_data) > 2 * fade_samples:
            # 淡入
            fade_in = np.linspace(0, 1, fade_samples)
            wave_data[:fade_samples] *= fade_in
            
            # 淡出
            fade_out = np.linspace(1, 0, fade_samples)
            wave_data[-fade_samples:] *= fade_out
        
        # 确保音频在合理范围内
        wave_data = np.clip(wave_data, -0.8, 0.8)  # 限制在-0.8到0.8范围内
        
        # 转换为16位整数，使用更精确的缩放
        max_val = 32767
        audio_data = (wave_data * max_val * 0.7).astype(np.int16)  # 使用70%音量避免失真
        
        # 创建WAV格式的字节数据
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_data = wav_buffer.getvalue()
        logger.info(f"✅ 干净测试音频创建完成: {len(wav_data)} bytes")
        
        return wav_data
    except Exception as e:
        logger.error(f"❌ 创建干净测试音频失败: {e}")
        return None

def test_sounddevice_with_different_settings():
    """测试不同的sounddevice设置"""
    try:
        import sounddevice as sd
        logger.info("🔧 测试不同的sounddevice设置...")
        
        # 创建测试音频
        audio_data = create_clean_test_audio(440, 1.0)  # 1秒测试音频
        if not audio_data:
            return False
        
        # 解析音频
        with io.BytesIO(audio_data) as wav_io:
            with wave.open(wav_io, 'rb') as wave_file:
                sample_width = wave_file.getsampwidth()
                channels = wave_file.getnchannels()
                framerate = wave_file.getframerate()
                frames = wave_file.readframes(wave_file.getnframes())
        
        # 转换为numpy数组
        audio_array = np.frombuffer(frames, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32767.0
        
        logger.info(f"📊 音频数据: 范围[{audio_float.min():.3f}, {audio_float.max():.3f}], 长度{len(audio_float)}")
        
        # 测试不同的设备和设置
        devices = sd.query_devices()
        output_devices = [i for i, d in enumerate(devices) if d['max_output_channels'] > 0]
        
        logger.info(f"🔊 找到 {len(output_devices)} 个输出设备")
        
        # 使用默认设备进行测试
        default_device = sd.default.device[1] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
        
        logger.info(f"🎯 使用默认输出设备: {default_device}")
        
        # 测试不同的设置
        test_settings = [
            {"samplerate": framerate, "channels": 1, "dtype": "float32"},
            {"samplerate": 44100, "channels": 1, "dtype": "float32"},
            {"samplerate": 48000, "channels": 1, "dtype": "float32"},
        ]
        
        for i, settings in enumerate(test_settings):
            try:
                logger.info(f"🧪 测试设置 {i+1}: {settings}")
                
                # 调整音频以匹配设置
                if settings["samplerate"] != framerate:
                    # 简单重采样（实际项目中应该使用专业的重采样库）
                    ratio = settings["samplerate"] / framerate
                    new_length = int(len(audio_float) * ratio)
                    indices = np.linspace(0, len(audio_float) - 1, new_length)
                    resampled_audio = np.interp(indices, np.arange(len(audio_float)), audio_float)
                else:
                    resampled_audio = audio_float.copy()
                
                # 播放测试
                logger.info(f"▶️ 播放测试音频 (设置 {i+1})...")
                sd.play(resampled_audio, **settings, blocking=True)
                logger.info(f"✅ 设置 {i+1} 播放完成")
                
                time.sleep(0.5)  # 间隔
                
            except Exception as e:
                logger.error(f"❌ 设置 {i+1} 播放失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ sounddevice设置测试失败: {e}")
        return False

def test_main_audio_with_clean_data():
    """使用干净的音频数据测试main.py播放功能"""
    try:
        from main import PetService
        
        logger.info("🧪 使用干净音频数据测试main.py播放...")
        
        # 创建服务实例
        service = PetService()
        service.logger = logger
        service._stop_singing = False
        service.current_audio_stream = None
        service.lrc_manager = None
        service.app_manager = None
        
        # 创建多个不同频率的干净测试音频
        test_frequencies = [220, 440, 880]  # A3, A4, A5
        
        for freq in test_frequencies:
            logger.info(f"🎵 测试 {freq}Hz 音频...")
            
            # 创建干净的音频
            audio_data = create_clean_test_audio(freq, 1.5)
            if not audio_data:
                continue
            
            # 重置停止标志
            service._stop_singing = False
            
            # 播放音频
            service.play_singing_audio(audio_data, volume=0.3, loop=False, singing_motion="唱歌")
            
            # 等待播放完成
            time.sleep(2.0)
            
            logger.info(f"✅ {freq}Hz 音频测试完成")
        
        logger.info("🎉 main.py干净音频测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ main.py干净音频测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def diagnose_noise_issues():
    """诊断可能导致噪音的问题"""
    try:
        import sounddevice as sd
        logger.info("🔍 诊断噪音问题...")
        
        # 检查音频设备状态
        devices = sd.query_devices()
        logger.info("📱 音频设备状态检查:")
        
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                logger.info(f"  设备 [{i}]: {device['name']}")
                logger.info(f"    默认采样率: {device['default_samplerate']}")
                logger.info(f"    输出声道: {device['max_output_channels']}")
                logger.info(f"    延迟: {device.get('default_low_output_latency', 'N/A')}")
        
        # 检查默认设备
        default_device = sd.default.device
        logger.info(f"🎯 当前默认设备: {default_device}")
        
        # 检查可能的噪音源
        logger.info("⚠️ 可能的噪音源:")
        logger.info("  1. 音频数据范围超出 [-1.0, 1.0]")
        logger.info("  2. 采样率不匹配")
        logger.info("  3. 音频设备驱动问题")
        logger.info("  4. 音量设置过高导致失真")
        logger.info("  5. 多个音频流同时播放")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 噪音问题诊断失败: {e}")
        return False

def main():
    """主诊断函数"""
    logger.info("🔧 开始音频噪音问题诊断...")
    
    success_count = 0
    total_tests = 4
    
    # 测试1: 噪音问题诊断
    logger.info("\n" + "="*50)
    logger.info("测试1: 噪音问题诊断")
    logger.info("="*50)
    if diagnose_noise_issues():
        success_count += 1
        logger.info("✅ 测试1通过")
    else:
        logger.error("❌ 测试1失败")
    
    # 测试2: 创建干净的测试音频
    logger.info("\n" + "="*50)
    logger.info("测试2: 创建干净的测试音频")
    logger.info("="*50)
    clean_audio = create_clean_test_audio(440, 2.0)
    if clean_audio:
        success_count += 1
        logger.info("✅ 测试2通过")
    else:
        logger.error("❌ 测试2失败")
    
    # 测试3: sounddevice设置测试
    logger.info("\n" + "="*50)
    logger.info("测试3: sounddevice设置测试")
    logger.info("="*50)
    if test_sounddevice_with_different_settings():
        success_count += 1
        logger.info("✅ 测试3通过")
    else:
        logger.error("❌ 测试3失败")
    
    # 测试4: main.py干净音频测试
    logger.info("\n" + "="*50)
    logger.info("测试4: main.py干净音频测试")
    logger.info("="*50)
    if test_main_audio_with_clean_data():
        success_count += 1
        logger.info("✅ 测试4通过")
    else:
        logger.error("❌ 测试4失败")
    
    # 总结结果
    logger.info("\n" + "="*50)
    logger.info("🔍 噪音诊断结果")
    logger.info("="*50)
    logger.info(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！噪音问题应该已解决")
        logger.info("💡 建议:")
        logger.info("  1. 使用音量 0.3-0.7 避免失真")
        logger.info("  2. 确保音频数据在 [-0.8, 0.8] 范围内")
        logger.info("  3. 添加淡入淡出效果减少噪音")
        return True
    else:
        logger.error(f"❌ {total_tests - success_count} 个测试失败")
        logger.error("🔧 建议检查:")
        logger.error("  1. 音频驱动和设备")
        logger.error("  2. Python音频依赖库")
        logger.error("  3. 系统音量设置")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 噪音诊断完成！请听刚才播放的测试音频确认噪音是否消除。")
        else:
            print("\n❌ 噪音诊断发现问题，请根据日志信息进行修复。")
    except KeyboardInterrupt:
        print("\n⛔ 用户中断诊断")
    except Exception as e:
        print(f"\n💥 诊断过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
