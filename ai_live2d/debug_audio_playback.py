#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频播放调试脚本 - 诊断main.py中的音频播放问题
"""
import sys
import os
import io
import wave
import tempfile
import numpy as np
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sounddevice():
    """测试sounddevice模块"""
    try:
        import sounddevice as sd
        logger.info("✅ sounddevice模块导入成功")
        
        # 检查音频设备
        devices = sd.query_devices()
        logger.info(f"📱 检测到音频设备数量: {len(devices)}")
        
        # 显示默认设备
        default_device = sd.default.device
        logger.info(f"🔊 默认音频设备: {default_device}")
        
        # 显示所有可用设备
        logger.info("📋 可用音频设备列表:")
        for i, device in enumerate(devices):
            device_type = "输入" if device['max_input_channels'] > 0 else ""
            device_type += "输出" if device['max_output_channels'] > 0 else ""
            logger.info(f"  [{i}] {device['name']} - {device_type} - 采样率: {device['default_samplerate']}")
        
        return True
    except ImportError as e:
        logger.error(f"❌ sounddevice模块导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ sounddevice测试失败: {e}")
        return False

def create_test_audio():
    """创建测试音频数据"""
    try:
        logger.info("🎵 创建测试音频...")
        
        # 生成440Hz正弦波（A音）
        sample_rate = 44100
        duration = 2.0  # 2秒
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
        logger.info(f"✅ 测试音频创建完成: {len(wav_data)} bytes")
        
        return wav_data
    except Exception as e:
        logger.error(f"❌ 创建测试音频失败: {e}")
        return None

def test_sounddevice_playback(audio_data):
    """测试sounddevice播放"""
    try:
        import sounddevice as sd
        logger.info("🔊 测试sounddevice播放...")
        
        # 解析WAV音频数据
        with io.BytesIO(audio_data) as wav_io:
            with wave.open(wav_io, 'rb') as wave_file:
                sample_width = wave_file.getsampwidth()
                channels = wave_file.getnchannels()
                framerate = wave_file.getframerate()
                num_frames = wave_file.getnframes()
                frames = wave_file.readframes(num_frames)
        
        logger.info(f"📊 音频参数: {channels}声道, {framerate}Hz, {num_frames}帧")
        
        # 转换为numpy数组
        dtype = np.int16 if sample_width == 2 else np.int8
        audio_array = np.frombuffer(frames, dtype=dtype)
        audio_float = audio_array.astype(np.float32) / 32767.0
        
        logger.info(f"🎛️ 音频数组形状: {audio_float.shape}, 范围: [{audio_float.min():.3f}, {audio_float.max():.3f}]")
        
        # 播放音频
        logger.info("▶️ 开始播放测试音频...")
        sd.play(audio_float, samplerate=framerate, blocking=True)
        logger.info("✅ sounddevice播放完成")
        
        return True
    except Exception as e:
        logger.error(f"❌ sounddevice播放失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_system_playback(audio_data):
    """测试系统播放器"""
    try:
        logger.info("🖥️ 测试系统播放器...")
        
        # 保存为临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        if sys.platform == 'win32':
            import winsound
            logger.info("🎵 使用Windows winsound播放...")
            winsound.PlaySound(temp_path, winsound.SND_FILENAME)
            logger.info("✅ Windows播放完成")
        else:
            # Linux/Mac
            import subprocess
            logger.info("🎵 使用aplay播放...")
            result = subprocess.run(['aplay', temp_path], capture_output=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ Linux播放完成")
            else:
                logger.error(f"❌ Linux播放失败: {result.stderr}")
                return False
        
        # 清理临时文件
        os.unlink(temp_path)
        return True
        
    except Exception as e:
        logger.error(f"❌ 系统播放器测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_volume_levels():
    """测试不同音量级别"""
    try:
        import sounddevice as sd
        logger.info("🔊 测试音量级别...")
        
        # 创建简短的测试音频
        sample_rate = 44100
        duration = 0.5  # 0.5秒
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(frequency * 2 * np.pi * t)
        
        # 测试不同音量
        volumes = [0.1, 0.3, 0.5, 0.7, 1.0]
        for volume in volumes:
            logger.info(f"🎚️ 测试音量: {volume}")
            audio_with_volume = wave_data * volume
            sd.play(audio_with_volume, samplerate=sample_rate, blocking=True)
            time.sleep(0.2)  # 间隔
        
        logger.info("✅ 音量测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 音量测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始音频播放诊断...")
    
    # 1. 测试sounddevice模块
    if not test_sounddevice():
        logger.error("❌ sounddevice模块不可用，无法继续测试")
        return False
    
    # 2. 创建测试音频
    audio_data = create_test_audio()
    if not audio_data:
        logger.error("❌ 无法创建测试音频")
        return False
    
    # 3. 测试sounddevice播放
    logger.info("\n" + "="*50)
    logger.info("测试1: sounddevice播放")
    logger.info("="*50)
    sd_success = test_sounddevice_playback(audio_data)
    
    # 4. 测试系统播放器
    logger.info("\n" + "="*50)
    logger.info("测试2: 系统播放器")
    logger.info("="*50)
    sys_success = test_system_playback(audio_data)
    
    # 5. 测试音量级别（如果sounddevice可用）
    if sd_success:
        logger.info("\n" + "="*50)
        logger.info("测试3: 音量级别")
        logger.info("="*50)
        test_volume_levels()
    
    # 6. 总结结果
    logger.info("\n" + "="*50)
    logger.info("🔍 诊断结果")
    logger.info("="*50)
    logger.info(f"sounddevice播放: {'✅ 成功' if sd_success else '❌ 失败'}")
    logger.info(f"系统播放器: {'✅ 成功' if sys_success else '❌ 失败'}")
    
    if not sd_success and not sys_success:
        logger.error("❌ 所有播放方法都失败，可能的原因:")
        logger.error("   1. 音频驱动问题")
        logger.error("   2. 音频设备被占用")
        logger.error("   3. 系统音量被静音")
        logger.error("   4. Python环境缺少音频依赖")
        return False
    elif not sd_success:
        logger.warning("⚠️ sounddevice播放失败，但系统播放器可用")
        logger.warning("   建议: 在main.py中使用系统播放器作为备选方案")
        return True
    else:
        logger.info("✅ 音频播放正常，问题可能在main.py的具体实现中")
        return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 诊断完成！请检查输出日志了解详细信息。")
        else:
            print("\n❌ 诊断发现问题，请根据日志信息进行修复。")
    except KeyboardInterrupt:
        print("\n⛔ 用户中断测试")
    except Exception as e:
        print(f"\n💥 诊断过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
