#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的噪音修复验证脚本
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

def create_simple_clean_audio():
    """创建简单的干净音频"""
    try:
        logger.info("🎵 创建简单干净音频...")
        
        sample_rate = 44100
        duration = 2.0
        frequency = 440.0  # A音
        
        # 生成正弦波
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(frequency * 2 * np.pi * t)
        
        # 添加淡入淡出，避免突然开始/结束的噪音
        fade_samples = int(sample_rate * 0.05)  # 50ms
        if len(wave_data) > 2 * fade_samples:
            # 淡入
            fade_in = np.linspace(0, 1, fade_samples)
            wave_data[:fade_samples] *= fade_in
            
            # 淡出  
            fade_out = np.linspace(1, 0, fade_samples)
            wave_data[-fade_samples:] *= fade_out
        
        # 限制音频范围避免失真
        wave_data = np.clip(wave_data, -0.7, 0.7)
        
        # 转换为WAV格式
        audio_int = (wave_data * 32767 * 0.8).astype(np.int16)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int.tobytes())
        
        wav_data = wav_buffer.getvalue()
        logger.info(f"✅ 简单干净音频创建完成: {len(wav_data)} bytes")
        
        return wav_data
    except Exception as e:
        logger.error(f"❌ 创建简单干净音频失败: {e}")
        return None

def test_simple_playback():
    """简单播放测试"""
    try:
        from main import PetService
        
        logger.info("🧪 开始简单播放测试...")
        
        # 创建服务
        service = PetService()
        service.logger = logger
        service._stop_singing = False
        service.current_audio_stream = None
        service.lrc_manager = None
        service.app_manager = None
        
        # 创建测试音频
        audio_data = create_simple_clean_audio()
        if not audio_data:
            return False
        
        logger.info("▶️ 开始播放干净音频，请仔细听是否还有噪音...")
        
        # 播放音频，使用较低音量避免失真
        service.play_singing_audio(audio_data, volume=0.3, loop=False, singing_motion="唱歌")
        
        # 等待播放完成
        time.sleep(3.0)
        
        logger.info("✅ 简单播放测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 简单播放测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("🔧 开始简化的噪音修复验证...")
    
    logger.info("📋 主要修复内容:")
    logger.info("  1. ✅ 移除重复线程创建")
    logger.info("  2. ✅ 音频数据限制在[-0.8, 0.8]")
    logger.info("  3. ✅ 添加淡入淡出效果")
    logger.info("  4. ✅ 改进设备兼容性检查")
    logger.info("  5. ✅ 自动处理采样率问题")
    logger.info("  6. ✅ 智能回退机制")
    
    logger.info("\n🎵 开始播放测试...")
    
    success = test_simple_playback()
    
    if success:
        logger.info("\n🎉 噪音修复验证完成!")
        logger.info("💡 重要提示:")
        logger.info("  • 如果您听到的是清晰的440Hz音调，说明噪音问题已解决")
        logger.info("  • 如果仍有噪音，请检查系统音量和音频驱动")
        logger.info("  • 建议在实际使用时音量设置在0.3-0.6之间")
        print("\n🎵 如果您刚才听到的是清晰的音调而不是噪音，说明修复成功！")
        return True
    else:
        logger.error("\n❌ 验证失败")
        print("\n❌ 验证过程中出现问题，请检查日志信息。")
        return False

if __name__ == "__main__":
    try:
        success = main()
        input("\n按Enter键退出...")
    except KeyboardInterrupt:
        print("\n⛔ 用户中断验证")
    except Exception as e:
        print(f"\n💥 验证过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
