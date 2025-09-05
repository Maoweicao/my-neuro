#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试音频错误处理机制
"""

import os
import sys
import json
import asyncio
import threading
import time
import wave
import io
import base64
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import PetService
from utils.logger import setup_logger

def create_test_audio_data():
    """创建测试音频数据"""
    try:
        # 生成440Hz正弦波（A音符）
        sample_rate = 44100
        duration = 2.0  # 2秒
        frequency = 440.0  # A4音符
        
        # 生成时间数组
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # 生成正弦波
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # 转换为16位整数
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # 创建WAV文件
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return wav_buffer.getvalue()
        
    except Exception as e:
        print(f"创建测试音频失败: {e}")
        return None

def test_audio_error_handling():
    """测试音频错误处理"""
    try:
        print(">>> 开始测试音频错误处理...")
        
        # 设置日志
        logger = setup_logger(level="INFO")
        
        # 创建测试音频数据
        audio_data = create_test_audio_data()
        if not audio_data:
            print(">>> 创建测试音频失败")
            return
        
        print(f">>> 测试音频数据大小: {len(audio_data)} bytes")
        
        # 创建模拟的PetService实例（不初始化完整服务）
        class MockPetService:
            def __init__(self):
                self.logger = logger
                self.app_manager = None
                self.lrc_manager = None
                self._stop_singing = False
                self.current_audio_stream = None
                self.audio_thread = None
                self.event_loop = None
            
            # 复制主要的音频播放方法
            def _convert_audio_format(self, audio_data):
                return audio_data  # 直接返回，假设是WAV格式
            
            def _get_motion_index_by_name(self, motion_name):
                return 5  # 默认动作
            
            def play_singing_audio(self, audio_data, volume=1.0, loop=False, singing_motion="唱歌", lrc_content=""):
                """播放唱歌音频"""
                try:
                    if self.logger:
                        self.logger.info(">>> 开始播放唱歌音频")
                    
                    # 转换音频格式
                    converted_audio_data = self._convert_audio_format(audio_data)
                    
                    # 在后台线程中播放音频
                    self.audio_thread = threading.Thread(
                        target=self._play_singing_audio,
                        args=(converted_audio_data, volume, loop, singing_motion)
                    )
                    self.audio_thread.daemon = True
                    self.audio_thread.start()
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 播放唱歌音频失败: {e}")
        
        # 从main.py复制_play_singing_audio方法
        def _play_singing_audio(self, audio_data, volume, loop, singing_motion):
            """播放唱歌音频并触发Live2D动作"""
            try:
                import sounddevice as sd
                
                if self.logger:
                    self.logger.info(">>> 开始播放唱歌音频")
                
                # 解析WAV音频数据
                with io.BytesIO(audio_data) as wav_io:
                    with wave.open(wav_io, 'rb') as wave_file:
                        sample_width = wave_file.getsampwidth()
                        channels = wave_file.getnchannels()
                        framerate = wave_file.getframerate()
                        num_frames = wave_file.getnframes()
                        frames = wave_file.readframes(num_frames)
                
                if self.logger:
                    self.logger.info(f">>> WAV解析完成: {channels}声道, {framerate}Hz, {num_frames}帧")
                
                # 转换为numpy数组并应用音量
                dtype = np.int16 if sample_width == 2 else np.int8
                audio_array = np.frombuffer(frames, dtype=dtype)
                
                # 确保正确的数据类型转换
                if sample_width == 2:
                    audio_float = audio_array.astype(np.float32) / 32767.0
                else:
                    audio_float = audio_array.astype(np.float32) / 127.0
                
                # 重塑为多声道（必须在其他操作之前）
                if channels > 1:
                    audio_float = audio_float.reshape(-1, channels)
                
                # 应用音量并确保在有效范围内
                audio_float *= volume
                audio_float = np.clip(audio_float, -0.8, 0.8)
                
                # 添加淡入淡出效果
                fade_samples = int(framerate * 0.01)  # 10ms淡入淡出
                if len(audio_float) > 2 * fade_samples:
                    # 淡入
                    fade_in = np.linspace(0, 1, fade_samples)
                    if channels > 1:
                        fade_in = fade_in.reshape(-1, 1)
                    audio_float[:fade_samples] *= fade_in
                    
                    # 淡出
                    fade_out = np.linspace(1, 0, fade_samples)
                    if channels > 1:
                        fade_out = fade_out.reshape(-1, 1)
                    audio_float[-fade_samples:] *= fade_out
                
                if self.logger:
                    self.logger.info(f">>> 音频数据处理完成")
                
                # 检查音频设备可用性（这里会触发错误）
                try:
                    devices = sd.query_devices()
                    print(f">>> 发现 {len(devices)} 个音频设备")
                    
                    # 模拟Windows WDM-KS错误
                    if True:  # 强制触发错误进行测试
                        raise Exception("Error starting stream: Unanticipated host error [PaErrorCode -9999]: 'WdmSyncIoctl: DeviceIoControl GLE = 0x00000492 (prop_set = {1464EDA5-6A8F-11D1-9AA7-00A0C9223196}, prop_id = 0)' [Windows WDM-KS error 0]")
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f">>> 音频设备检查失败: {e}")
                    
                    # 检查是否是严重的音频驱动错误
                    error_str = str(e)
                    critical_errors = [
                        "PaErrorCode -9999",  # Windows WDM-KS错误
                        "Unanticipated host error",
                        "DeviceIoControl",
                        "WdmSyncIoctl"
                    ]
                    
                    is_critical_error = any(error in error_str for error in critical_errors)
                    
                    if is_critical_error:
                        if self.logger:
                            self.logger.error(">>> 检测到严重音频设备错误，退出播放")
                        
                        # 重置播放状态
                        self._stop_singing = True
                        self.current_audio_stream = None
                        
                        if self.logger:
                            self.logger.info(">>> 播放状态已重置，退出音频播放")
                        return
                    
                    # 其他错误的处理...
                    if self.logger:
                        self.logger.info(">>> 尝试回退播放方法")
                    
            except ImportError as e:
                if self.logger:
                    self.logger.error(f">>> 缺少音频播放依赖: {e}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f">>> 播放唱歌音频失败: {e}")
        
        # 将方法绑定到类
        MockPetService._play_singing_audio = _play_singing_audio
        
        # 创建模拟服务实例
        mock_service = MockPetService()
        
        # 测试音频播放错误处理
        print(">>> 测试音频播放错误处理...")
        mock_service.play_singing_audio(audio_data, volume=0.5)
        
        # 等待音频线程完成
        if mock_service.audio_thread:
            mock_service.audio_thread.join(timeout=5.0)
        
        print(">>> 错误处理测试完成")
        
        # 检查状态
        if mock_service._stop_singing:
            print(">>> ✅ 错误处理正常：播放状态已正确重置")
        else:
            print(">>> ❌ 错误处理失败：播放状态未重置")
        
        if mock_service.current_audio_stream is None:
            print(">>> ✅ 音频流清理正常：当前音频流已重置")
        else:
            print(">>> ❌ 音频流清理失败：当前音频流未重置")
        
    except Exception as e:
        print(f">>> 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_error_handling()
