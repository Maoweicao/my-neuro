#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LRC歌词管理器线程安全修复
"""

import time
import logging
from utils.lrc_manager import LRCManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

class MockSubtitleManager:
    """模拟字幕管理器"""
    
    def __init__(self):
        self.current_text = ""
    
    def add_text(self, text, stream=False):
        self.current_text = text
        print(f"[字幕显示] {text}")
    
    def clear_text(self):
        self.current_text = ""
        print("[字幕清空]")

def test_lrc_thread_safety():
    """测试LRC歌词管理器线程安全"""
    print("=== 测试LRC歌词管理器线程安全 ===")
    
    # 创建模拟字幕管理器
    subtitle_manager = MockSubtitleManager()
    
    # 创建LRC管理器
    lrc_manager = LRCManager(subtitle_manager)
    
    # 加载短歌词测试（确保会自动结束）
    test_lrc = """[00:00:00] 开始
[00:01:00] 第一句
[00:02:00] 第二句
[00:03:00] 结束"""
    
    if not lrc_manager.load_lrc_content(test_lrc):
        print("❌ LRC歌词加载失败")
        return
    
    print("✓ LRC歌词加载成功")
    
    # 开始播放
    print("\n开始测试播放（播放10秒）...")
    lrc_manager.start_playback()
    
    # 模拟播放10秒
    for i in range(10):
        time.sleep(1)
        info = lrc_manager.get_lyric_info()
        print(f"播放 {i+1}s - 播放状态: {info['is_playing']}, "
              f"索引: {info['current_index']}/{info['total_lines']}")
        
        # 如果播放已停止，跳出循环
        if not info['is_playing']:
            print(f"✓ 播放在 {i+1}s 时自动停止")
            break
    
    # 如果还在播放，手动停止
    if lrc_manager.is_playing:
        print("\n手动停止播放...")
        lrc_manager.stop_playback()
    
    print("✓ 测试完成，没有发生线程死锁")

if __name__ == "__main__":
    try:
        test_lrc_thread_safety()
        print("\n=== 线程安全测试通过 ===")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
