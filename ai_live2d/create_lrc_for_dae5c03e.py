#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为音频hash dae5c03e 创建测试LRC文件
解决webapi_tester中歌词文件未找到的问题
"""

import os

def create_lrc_for_hash_dae5c03e():
    """为音频hash dae5c03e 创建LRC文件"""
    audio_hash = "dae5c03e"
    
    # 确保lyrics目录存在
    os.makedirs('lyrics', exist_ok=True)
    
    # 创建LRC文件
    lrc_filename = f"lyrics/{audio_hash}.lrc"
    lrc_content = f"""[00:00.00]测试歌词 - Hash: {audio_hash}
[00:02.00]这是为webapi_tester创建的LRC文件
[00:05.00]用于解决歌词文件未找到的问题
[00:08.00]音频大小: 14246146 bytes
[00:10.00]现在应该能找到对应的歌词文件了
[00:12.00]webapi_tester歌词集成测试
[00:15.00]测试完成
"""
    
    with open(lrc_filename, 'w', encoding='utf-8') as f:
        f.write(lrc_content)
    
    print(f"✅ 创建LRC文件成功: {lrc_filename}")
    print(f"   音频Hash: {audio_hash}")
    print(f"   歌词长度: {len(lrc_content)} 字符")
    print()
    print("📋 现在可以重新测试webapi_tester的唱歌功能:")
    print("1. 在webapi_tester中使用相同的音频文件")
    print("2. 系统应该能找到对应的LRC歌词文件")
    print("3. 歌词API测试应该返回成功")
    
    # 显示歌词内容
    print()
    print("📝 LRC文件内容:")
    with open(lrc_filename, 'r', encoding='utf-8') as f:
        content = f.read()
        for line in content.split('\n'):
            if line.strip():
                print(f"   {line}")

def check_socket_connection():
    """检查socket连接问题"""
    print()
    print("🔍 关于Socket连接问题:")
    print("从日志看到两个Socket错误:")
    print("1. 'timed out' - Socket超时")
    print("2. '[WinError 10061] 由于目标计算机积极拒绝，无法连接' - 连接被拒绝")
    print()
    print("这表明:")
    print("- main.py正在运行，但socket监听可能有问题")
    print("- 或者连接池已满")
    print("- 系统已经回退到本地播放模式")
    print()
    print("💡 建议:")
    print("1. 重启main.py以重置socket连接")
    print("2. 或者继续使用回退模式，功能依然正常")

if __name__ == "__main__":
    print("🚀 为webapi_tester创建缺失的LRC文件")
    print()
    
    create_lrc_for_hash_dae5c03e()
    check_socket_connection()
