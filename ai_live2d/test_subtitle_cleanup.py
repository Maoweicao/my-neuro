#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试音频播放停止时的字幕清理功能
"""

import os
import sys
import logging
import time
import threading

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 设置UTF-8编码
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_subtitle_cleanup():
    """测试字幕清理功能"""
    print("=== 测试音频播放停止时的字幕清理功能 ===")
    
    try:
        # 导入PetService
        from main import PetService
        
        # 创建服务实例
        service = PetService("config.json")
        
        # 模拟初始化
        service.logger = logging.getLogger("test")
        service._running = True
        service._stop_singing = False
        
        # 模拟app_manager和subtitle_manager
        class MockSubtitleManager:
            def __init__(self):
                self.text = ""
                self.cleared = False
            
            def add_text(self, text, stream=False):
                self.text = text
                self.cleared = False
                print(f">>> 模拟显示字幕: {text[:50]}...")
            
            def clear_text(self):
                self.text = ""
                self.cleared = True
                print(">>> 模拟清理字幕")
        
        class MockLive2DModel:
            def __init__(self):
                self.motion = 5  # 默认唱歌动作
            
            def set_motion(self, motion_index):
                self.motion = motion_index
                print(f">>> 模拟设置Live2D动作: {motion_index}")
        
        class MockLRCManager:
            def __init__(self):
                self.playing = False
            
            def start_playback(self):
                self.playing = True
                print(">>> 模拟启动LRC歌词播放")
            
            def stop_playback(self):
                self.playing = False
                print(">>> 模拟停止LRC歌词播放")
            
            def stop(self):
                self.playing = False
                print(">>> 模拟停止LRC歌词播放（stop方法）")
        
        class MockAppManager:
            def __init__(self):
                self.subtitle_manager = MockSubtitleManager()
                self.live2d_model = MockLive2DModel()
        
        # 设置模拟对象
        service.app_manager = MockAppManager()
        service.lrc_manager = MockLRCManager()
        
        print("\n1. 测试显示字幕...")
        service.show_subtitle("这是一首测试歌曲的歌词", "singing")
        
        print(f"字幕内容: {service.app_manager.subtitle_manager.text}")
        print(f"字幕是否已清理: {service.app_manager.subtitle_manager.cleared}")
        
        print("\n2. 测试stop_audio_playback方法...")
        service.stop_audio_playback()
        
        print(f"字幕内容: {service.app_manager.subtitle_manager.text}")
        print(f"字幕是否已清理: {service.app_manager.subtitle_manager.cleared}")
        print(f"LRC播放状态: {service.lrc_manager.playing}")
        print(f"Live2D动作: {service.app_manager.live2d_model.motion}")
        
        # 测试中断操作
        print("\n3. 重新显示字幕并测试中断操作...")
        service.show_subtitle("另一首歌的歌词", "singing")
        service.lrc_manager.start_playback()
        service.app_manager.live2d_model.set_motion(5)  # 唱歌动作
        
        print(f"重新显示后 - 字幕内容: {service.app_manager.subtitle_manager.text}")
        print(f"重新显示后 - 字幕是否已清理: {service.app_manager.subtitle_manager.cleared}")
        print(f"重新显示后 - LRC播放状态: {service.lrc_manager.playing}")
        print(f"重新显示后 - Live2D动作: {service.app_manager.live2d_model.motion}")
        
        # 模拟中断操作
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def test_interrupt():
            await service._perform_interrupt()
        
        loop.run_until_complete(test_interrupt())
        loop.close()
        
        print(f"中断后 - 字幕内容: {service.app_manager.subtitle_manager.text}")
        print(f"中断后 - 字幕是否已清理: {service.app_manager.subtitle_manager.cleared}")
        print(f"中断后 - LRC播放状态: {service.lrc_manager.playing}")
        print(f"中断后 - Live2D动作: {service.app_manager.live2d_model.motion}")
        
        print("\n✅ 字幕清理功能测试完成！")
        
        # 验证结果
        if service.app_manager.subtitle_manager.cleared:
            print("✅ 字幕清理功能正常工作")
        else:
            print("❌ 字幕清理功能存在问题")
        
        if not service.lrc_manager.playing:
            print("✅ LRC歌词停止功能正常工作")
        else:
            print("❌ LRC歌词停止功能存在问题")
        
        if service.app_manager.live2d_model.motion == 0:
            print("✅ Live2D动作重置功能正常工作")
        else:
            print("❌ Live2D动作重置功能存在问题")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_subtitle_cleanup()
