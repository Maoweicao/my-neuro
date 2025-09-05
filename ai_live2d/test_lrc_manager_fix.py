#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LRC歌词管理器修复效果
"""

import time
import logging
from utils.lrc_manager import LRCManager, LRCParser

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

def test_lrc_time_parsing():
    """测试LRC时间戳解析"""
    print("=== 测试LRC时间戳解析 ===")
    
    test_cases = [
        ("00:07:00", 7000),    # 7秒
        ("00:12:00", 12000),   # 12秒
        ("00:18:00", 18000),   # 18秒
        ("00:24:00", 24000),   # 24秒
        ("00:29:00", 29000),   # 29秒
        ("00:33:00", 33000),   # 33秒
        ("00:35:00", 35000),   # 35秒
        ("00:39:00", 39000),   # 39秒
        ("00:43:00", 43000),   # 43秒
        ("02:15.30", 135300),  # 2分15.30秒
        ("01:23", 83000),      # 1分23秒
    ]
    
    for time_str, expected_ms in test_cases:
        parsed_ms = LRCParser.parse_time(time_str)
        status = "✓" if parsed_ms == expected_ms else "✗"
        print(f"{status} {time_str} -> {parsed_ms}ms (期望: {expected_ms}ms)")

def test_lrc_content_parsing():
    """测试LRC内容解析"""
    print("\n=== 测试LRC内容解析 ===")
    
    # 使用义勇军进行曲的LRC内容进行测试
    test_lrc = """[00:00:00] 义勇军进行曲的LRC歌词，下载歌词请复制下面的内容保存为.lrc文件
[00:07:00] 起来 不愿做奴隶的人们
[00:12:00] 把我们的血肉 筑成我们新的长城
[00:18:00] 中华民族到了最危险的时候
[00:24:00] 每个人被迫着发出最后的吼声
[00:29:00] 起来 起来 起来
[00:33:00] 我们万众一心
[00:35:00] 冒着敌人的炮火前进
[00:39:00] 冒着敌人的炮火前进
[00:43:00] 前进前进进"""
    
    lyrics, metadata = LRCParser.parse_lrc_content(test_lrc)
    
    print(f"解析结果:")
    print(f"- 歌词行数: {len(lyrics)}")
    print(f"- 元数据: {metadata}")
    print("\n歌词列表:")
    
    for i, lyric in enumerate(lyrics):
        time_formatted = f"{lyric.time_ms//60000:02d}:{(lyric.time_ms%60000)//1000:02d}.{lyric.time_ms%1000:03d}"
        print(f"  {i+1}. [{time_formatted}] {lyric.text}")
    
    return lyrics

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

def test_lrc_playback():
    """测试LRC歌词播放"""
    print("\n=== 测试LRC歌词播放 ===")
    
    # 创建模拟字幕管理器
    subtitle_manager = MockSubtitleManager()
    
    # 创建LRC管理器
    lrc_manager = LRCManager(subtitle_manager)
    
    # 加载测试歌词
    test_lrc = """[00:00:00] 义勇军进行曲的LRC歌词，下载歌词请复制下面的内容保存为.lrc文件
[00:07:00] 起来 不愿做奴隶的人们
[00:12:00] 把我们的血肉 筑成我们新的长城
[00:18:00] 中华民族到了最危险的时候
[00:24:00] 每个人被迫着发出最后的吼声
[00:29:00] 起来 起来 起来
[00:33:00] 我们万众一心
[00:35:00] 冒着敌人的炮火前进
[00:39:00] 冒着敌人的炮火前进
[00:43:00] 前进前进进"""
    
    if not lrc_manager.load_lrc_content(test_lrc):
        print("❌ LRC歌词加载失败")
        return
    
    print("✓ LRC歌词加载成功")
    
    # 开始播放
    print("\n开始测试播放（播放20秒）...")
    lrc_manager.start_playback()
    
    # 模拟播放20秒
    for i in range(20):
        time.sleep(1)
        info = lrc_manager.get_lyric_info()
        print(f"播放 {i+1}s - 索引: {info['current_index']}/{info['total_lines']}, "
              f"当前歌词: '{info['current_lyric'] or ''}', "
              f"播放状态: {info['is_playing']}")
    
    # 停止播放
    lrc_manager.stop_playback()
    print("\n✓ 播放测试完成")

if __name__ == "__main__":
    try:
        # 测试时间戳解析
        test_lrc_time_parsing()
        
        # 测试歌词内容解析
        test_lrc_content_parsing()
        
        # 测试歌词播放
        test_lrc_playback()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
