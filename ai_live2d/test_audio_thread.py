#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试音频播放线程的脚本
"""

import sys
import os
import wave
import struct
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

# 导入AudioPlaybackThread类
from UI import AudioPlaybackThread

def create_test_audio():
    """创建一个简单的测试音频文件（1秒的440Hz正弦波）"""
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    # 生成音频数据
    frames = []
    for i in range(int(sample_rate * duration)):
        # 生成正弦波，限制在short范围内
        sample = int(32767 * 0.3 * (i * 2 * 3.14159 * frequency / sample_rate))
        # 确保在有效范围内
        sample = max(-32767, min(32767, sample))
        frames.append(struct.pack('<h', sample))

    # 创建WAV文件
    audio_data = b''
    audio_data += b'RIFF'
    audio_data += (36 + len(b''.join(frames))).to_bytes(4, 'little')
    audio_data += b'WAVE'
    audio_data += b'fmt '
    audio_data += (16).to_bytes(4, 'little')  # fmt chunk size
    audio_data += (1).to_bytes(2, 'little')   # audio format (PCM)
    audio_data += (1).to_bytes(2, 'little')   # num channels
    audio_data += sample_rate.to_bytes(4, 'little')
    audio_data += (sample_rate * 2).to_bytes(4, 'little')  # byte rate
    audio_data += (2).to_bytes(2, 'little')   # block align
    audio_data += (16).to_bytes(2, 'little')  # bits per sample
    audio_data += b'data'
    audio_data += len(b''.join(frames)).to_bytes(4, 'little')
    audio_data += b''.join(frames)

    return audio_data

class TestWidget(QObject):
    """测试用的Widget类"""

    def __init__(self):
        super().__init__()

    def trigger_live2d_motion(self, motion_index):
        print(f"触发Live2D动作: {motion_index}")

def test_audio_thread():
    """测试音频播放线程"""
    print("开始测试音频播放线程...")

    # 创建Qt应用
    app = QApplication(sys.argv)

    # 创建测试音频数据
    audio_data = create_test_audio()
    print(f"创建了 {len(audio_data)} 字节的测试音频数据")

    # 创建测试widget
    test_widget = TestWidget()

    # 创建音频播放线程
    audio_thread = AudioPlaybackThread(audio_data, 1.0, False, "唱歌", test_widget)

    # 连接信号
    audio_thread.finished.connect(lambda: print("音频播放完成"))
    audio_thread.error.connect(lambda msg: print(f"音频播放错误: {msg}"))

    # 启动播放
    print("启动音频播放...")
    audio_thread.start()

    # 等待播放完成（最多等待5秒）
    start_time = time.time()
    while audio_thread.isRunning() and (time.time() - start_time) < 5.0:
        app.processEvents()
        time.sleep(0.1)

    if audio_thread.isRunning():
        print("播放超时，停止线程")
        audio_thread.stop()
        audio_thread.wait(2000)

    print("测试完成")

if __name__ == "__main__":
    test_audio_thread()
