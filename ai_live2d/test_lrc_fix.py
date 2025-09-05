#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LRC歌词解析修复
"""

import sys
import os
import logging

# 添加项目路径到 sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.lrc_manager import LRCManager, LRCParser

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_lrc_parsing():
    """测试LRC歌词解析"""
    
    # 测试用的LRC内容
    test_lrc_content = """[00:00:00] 义勇军进行曲的LRC歌词，下载歌词请复制下面的内容 保存为.lrc文件
[00:01:00] 起来！不愿做奴隶的人们！
[00:03:00] 把我们的血肉，筑成我们新的长城！
[00:06:00] 中华民族到了最危险的时候，
[00:09:00] 每个人被迫着发出最后的吼声。
[00:13:00] 起来！起来！起来！
[00:16:00] 我们万众一心，
[00:18:00] 冒着敌人的炮火，前进！
[00:21:00] 冒着敌人的炮火，前进！
[00:24:00] 前进！前进、进！"""
    
    print("=== 测试LRC歌词解析 ===")
    print(f"测试内容长度: {len(test_lrc_content)} 字符")
    print(f"测试内容前200字符: {test_lrc_content[:200]}")
    print()
    
    # 测试解析器
    print("=== 测试LRCParser ===")
    lyrics, metadata = LRCParser.parse_lrc_content(test_lrc_content)
    print(f"解析结果: {len(lyrics)} 行歌词")
    print(f"元数据: {metadata}")
    
    if lyrics:
        print("\n前5行歌词:")
        for i, lyric in enumerate(lyrics[:5]):
            print(f"  {i+1}. {lyric}")
    else:
        print("ERROR: 没有解析到任何歌词!")
        return False
    
    # 测试LRCManager
    print("\n=== 测试LRCManager ===")
    lrc_manager = LRCManager()
    success = lrc_manager.load_lrc_content(test_lrc_content)
    print(f"LRCManager加载结果: {success}")
    print(f"LRCManager歌词数量: {len(lrc_manager.lyrics)}")
    
    if success and lrc_manager.lyrics:
        print("\nLRCManager中的前3行歌词:")
        for i, lyric in enumerate(lrc_manager.lyrics[:3]):
            print(f"  {i+1}. {lyric}")
    
    return success

if __name__ == "__main__":
    success = test_lrc_parsing()
    if success:
        print("\n✅ LRC歌词解析测试成功!")
        sys.exit(0)
    else:
        print("\n❌ LRC歌词解析测试失败!")
        sys.exit(1)
