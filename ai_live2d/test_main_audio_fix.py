#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试main.py中的音频播放功能
"""
import sys
import os
import io
import wave
import numpy as np
import base64
import json
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_wav():
    """创建测试WAV音频数据"""
    try:
        # 生成440Hz正弦波（A音）
        sample_rate = 44100
        duration = 3.0  # 3秒
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(frequency * 2 * np.pi * t)
        
        # 转换为16位整数
        audio_data = (wave_data * 32767).astype(np.int16)
        
        # 创建WAV格式的字节数据
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_data = wav_buffer.getvalue()
        logger.info(f"✅ 测试WAV音频创建完成: {len(wav_data)} bytes")
        
        return wav_data
    except Exception as e:
        logger.error(f"❌ 创建测试WAV失败: {e}")
        return None

def test_main_audio_playback():
    """测试main.py中的音频播放功能"""
    try:
        # 导入main模块中的PetService类
        from main import PetService
        
        logger.info("🚀 开始测试main.py音频播放...")
        
        # 创建测试服务（不完全初始化）
        service = PetService()
        
        # 设置基本属性
        service.logger = logger
        service._stop_singing = False
        service.current_audio_stream = None
        service.lrc_manager = None
        service.app_manager = None
        
        # 创建测试音频
        audio_data = create_test_wav()
        if not audio_data:
            logger.error("❌ 无法创建测试音频")
            return False
        
        # 测试音频播放
        logger.info("🎵 开始测试音频播放...")
        service.play_singing_audio(audio_data, volume=0.5, loop=False, singing_motion="唱歌", lrc_content="")
        
        # 等待播放完成
        logger.info("⏳ 等待播放完成...")
        time.sleep(4.0)  # 等待音频播放完成
        
        logger.info("✅ 音频播放测试完成")
        return True
        
    except ImportError as e:
        logger.error(f"❌ 导入main模块失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试音频播放失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_audio_conversion():
    """测试音频格式转换功能"""
    try:
        from main import PetService
        
        logger.info("🔄 测试音频格式转换...")
        
        service = PetService()
        service.logger = logger
        
        # 创建测试音频
        audio_data = create_test_wav()
        if not audio_data:
            return False
        
        # 测试格式转换
        converted_data = service._convert_audio_format(audio_data)
        
        if converted_data:
            logger.info(f"✅ 音频格式转换成功: {len(converted_data)} bytes")
            return True
        else:
            logger.error("❌ 音频格式转换失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试音频格式转换失败: {e}")
        return False

def test_message_queue_audio():
    """测试通过消息队列播放音频"""
    try:
        from utils.message_queue import get_message_queue
        
        logger.info("📨 测试消息队列音频播放...")
        
        # 创建测试音频
        audio_data = create_test_wav()
        if not audio_data:
            return False
        
        # 编码为base64
        audio_data_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 创建播放消息
        play_message = {
            'audio_data': audio_data_b64,
            'volume': 0.7,
            'loop': False,
            'singing_motion': '唱歌',
            'lrc_content': ''
        }
        
        # 发送消息
        message_queue = get_message_queue()
        message_queue.put_message('play_audio', play_message)
        
        logger.info("✅ 消息队列音频播放消息已发送")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试消息队列音频播放失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🎬 开始main.py音频播放测试...")
    
    success_count = 0
    total_tests = 3
    
    # 测试1: 音频格式转换
    logger.info("\n" + "="*50)
    logger.info("测试1: 音频格式转换")
    logger.info("="*50)
    if test_audio_conversion():
        success_count += 1
        logger.info("✅ 测试1通过")
    else:
        logger.error("❌ 测试1失败")
    
    # 测试2: 直接音频播放
    logger.info("\n" + "="*50)
    logger.info("测试2: 直接音频播放")
    logger.info("="*50)
    if test_main_audio_playback():
        success_count += 1
        logger.info("✅ 测试2通过")
    else:
        logger.error("❌ 测试2失败")
    
    # 测试3: 消息队列音频播放
    logger.info("\n" + "="*50)
    logger.info("测试3: 消息队列音频播放")
    logger.info("="*50)
    if test_message_queue_audio():
        success_count += 1
        logger.info("✅ 测试3通过")
    else:
        logger.error("❌ 测试3失败")
    
    # 总结结果
    logger.info("\n" + "="*50)
    logger.info("🔍 测试结果总结")
    logger.info("="*50)
    logger.info(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！main.py音频播放功能正常")
        return True
    else:
        logger.error(f"❌ {total_tests - success_count} 个测试失败")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 测试完成！音频播放功能正常。")
        else:
            print("\n❌ 测试发现问题，请检查日志信息。")
    except KeyboardInterrupt:
        print("\n⛔ 用户中断测试")
    except Exception as e:
        print(f"\n💥 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
