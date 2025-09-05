#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终噪音修复验证脚本
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

def create_test_music_audio():
    """创建更复杂的音乐测试音频"""
    try:
        logger.info("🎵 创建音乐测试音频...")
        
        sample_rate = 44100
        duration = 3.0
        
        # 创建和弦 (C大调)
        frequencies = [261.63, 329.63, 392.00]  # C-E-G
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # 混合多个频率
        audio_data = np.zeros(len(t))
        for i, freq in enumerate(frequencies):
            wave_component = np.sin(freq * 2 * np.pi * t) * (0.3 / len(frequencies))
            audio_data += wave_component
        
        # 添加包络调制（音量变化）
        envelope = np.exp(-t * 0.5)  # 指数衰减
        audio_data *= envelope
        
        # 确保在安全范围内
        audio_data = np.clip(audio_data, -0.6, 0.6)
        
        # 添加淡入淡出
        fade_samples = int(sample_rate * 0.05)  # 50ms
        if len(audio_data) > 2 * fade_samples:
            fade_in = np.linspace(0, 1, fade_samples)
            audio_data[:fade_samples] *= fade_in
            
            fade_out = np.linspace(1, 0, fade_samples)
            audio_data[-fade_samples:] *= fade_out
        
        # 转换为16位整数
        max_val = 32767
        audio_int = (audio_data * max_val * 0.8).astype(np.int16)
        
        # 创建WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int.tobytes())
        
        wav_data = wav_buffer.getvalue()
        logger.info(f"✅ 音乐测试音频创建完成: {len(wav_data)} bytes")
        
        return wav_data
    except Exception as e:
        logger.error(f"❌ 创建音乐测试音频失败: {e}")
        return None

def test_final_audio_quality():
    """测试修复后的音频质量"""
    try:
        from main import PetService
        
        logger.info("🎭 最终音频质量测试...")
        
        # 创建服务
        service = PetService()
        service.logger = logger
        service._stop_singing = False
        service.current_audio_stream = None
        service.lrc_manager = None
        service.app_manager = None
        
        # 测试不同类型的音频
        test_cases = [
            {"name": "纯音调", "freq": 440, "duration": 2.0, "volume": 0.4},
            {"name": "低音", "freq": 220, "duration": 1.5, "volume": 0.5},
            {"name": "高音", "freq": 880, "duration": 1.5, "volume": 0.3},
        ]
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"🧪 测试 {i+1}: {test_case['name']} ({test_case['freq']}Hz)")
            
            # 创建测试音频
            sample_rate = 44100
            duration = test_case['duration']
            frequency = test_case['freq']
            volume = test_case['volume']
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave_data = np.sin(frequency * 2 * np.pi * t)
            
            # 添加淡入淡出
            fade_samples = int(sample_rate * 0.02)  # 20ms
            if len(wave_data) > 2 * fade_samples:
                fade_in = np.linspace(0, 1, fade_samples)
                wave_data[:fade_samples] *= fade_in
                
                fade_out = np.linspace(1, 0, fade_samples)
                wave_data[-fade_samples:] *= fade_out
            
            # 限制范围
            wave_data = np.clip(wave_data, -0.7, 0.7)
            
            # 转换为WAV
            audio_int = (wave_data * 32767 * 0.8).astype(np.int16)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int.tobytes())
            
            audio_data = wav_buffer.getvalue()
            
            # 重置停止标志
            service._stop_singing = False
            
            # 播放测试
            service.play_singing_audio(audio_data, volume, False, "唱歌")
            
            # 等待播放完成
            time.sleep(duration + 0.5)
            
            logger.info(f"✅ 测试 {i+1} 完成")
        
        # 测试音乐音频
        logger.info("🎼 测试复杂音乐音频...")
        music_audio = create_test_music_audio()
        if music_audio:
            service._stop_singing = False
            service.play_singing_audio(music_audio, 0.4, False, "唱歌")
            time.sleep(3.5)
            logger.info("✅ 音乐音频测试完成")
        
        logger.info("🎉 所有音频质量测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 音频质量测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主验证函数"""
    logger.info("🔧 开始最终噪音修复验证...")
    
    logger.info("📝 修复内容总结:")
    logger.info("  1. ✅ 移除了重复的线程创建代码")
    logger.info("  2. ✅ 优化了音频数据范围限制 (-0.8 到 0.8)")
    logger.info("  3. ✅ 添加了淡入淡出效果减少噪音")
    logger.info("  4. ✅ 改进了音频设备选择逻辑")
    logger.info("  5. ✅ 选择延迟最低的设备减少噪音")
    
    logger.info("\n🎵 开始播放测试音频，请仔细听是否还有噪音...")
    
    success = test_final_audio_quality()
    
    if success:
        logger.info("\n🎉 噪音修复验证完成！")
        logger.info("💡 如果您听到的是清晰的音调而不是噪音，说明修复成功！")
        logger.info("🔧 修复要点:")
        logger.info("  • 音量控制在0.3-0.7之间")
        logger.info("  • 音频数据限制在[-0.8, 0.8]范围内")
        logger.info("  • 添加了淡入淡出效果")
        logger.info("  • 自动选择最佳音频设备")
        return True
    else:
        logger.error("❌ 噪音修复验证失败")
        logger.error("🔧 如果仍有噪音，请检查:")
        logger.error("  1. 音频驱动程序")
        logger.error("  2. 系统音量设置")
        logger.error("  3. 音频设备连接")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 噪音修复验证完成！如果听到清晰音调，说明问题已解决。")
        else:
            print("\n❌ 验证过程中发现问题，请检查日志信息。")
    except KeyboardInterrupt:
        print("\n⛔ 用户中断验证")
    except Exception as e:
        print(f"\n💥 验证过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
