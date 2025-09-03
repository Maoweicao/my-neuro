#!/usr/bin/env python3
"""
测试修复后的interrupt功能和音频数据处理
"""

import sys
import os
import asyncio
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_manager import AppManager

async def test_audio_data_callback():
    """测试音频数据回调功能"""
    print("开始测试音频数据回调功能...")

    # 创建AppManager实例
    app_manager = AppManager()

    # 模拟音频数据
    test_audio_data = {
        'num_frames': 4410,  # 0.1秒的音频数据
        'framerate': 44100,
        'sample_width': 2,
        'channels': 1,
        'frames': b'\x00\x01' * 4410,  # 模拟音频帧数据
        'pcm_data': np.random.rand(4410).astype(np.float32) * 0.1  # 模拟PCM数据
    }

    # 测试_on_audio_data方法
    print("测试_on_audio_data方法...")
    try:
        await app_manager._on_audio_data(test_audio_data)
        print("✓ _on_audio_data方法调用成功")
    except Exception as e:
        print(f"✗ _on_audio_data方法调用失败: {e}")
        return False

    # 测试没有Live2D模型的情况
    print("测试没有Live2D模型的情况...")
    app_manager.live2d_model = None
    try:
        await app_manager._on_audio_data(test_audio_data)
        print("✓ 没有Live2D模型时处理正常")
    except Exception as e:
        print(f"✗ 没有Live2D模型时出错: {e}")
        return False

    print("音频数据回调测试完成！")
    return True

if __name__ == "__main__":
    asyncio.run(test_audio_data_callback())
