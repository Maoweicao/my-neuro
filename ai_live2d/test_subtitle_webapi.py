#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试webapi_tester的字幕功能
"""

import os
import tempfile

def create_test_lrc_file():
    """创建一个测试的LRC文件"""
    lrc_content = """[00:00.00]♪ 测试歌词第一行 ♪
[00:02.50]♪ 测试歌词第二行 ♪
[00:05.00]♪ 测试歌词第三行 ♪
[00:07.50]♪ 测试歌词第四行 ♪"""

    # 创建临时LRC文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lrc', delete=False, encoding='utf-8') as f:
        f.write(lrc_content)
        return f.name

def test_subtitle_functionality():
    """测试字幕功能说明"""
    print("🧪 WebAPI Tester 字幕功能测试说明")
    print("=" * 50)

    print("\n✅ 新增功能:")
    print("1. 唱歌测试标签页中添加了字幕开关")
    print("2. 支持选择LRC歌词文件")
    print("3. 批量测试包含字幕和无字幕两种模式")

    print("\n📋 使用方法:")
    print("1. 打开WebAPI Tester")
    print("2. 进入'唱歌测试'标签页")
    print("3. 设置参数:")
    print("   - 音量: 0.0-2.0")
    print("   - 循环播放: 是否循环")
    print("   - Live2D动作: 选择动作")
    print("   - 启用字幕: 开启/关闭字幕显示")
    print("4. 选择音频文件或生成测试音频")
    print("5. 可选: 选择LRC歌词文件")
    print("6. 点击'发送唱歌请求'")

    print("\n🎵 字幕显示逻辑:")
    print("- 字幕启用 + 有LRC文件: 显示歌词内容")
    print("- 字幕启用 + 无LRC文件: 显示 '♪ 唱歌中 ♫'")
    print("- 字幕禁用: 不显示字幕")

    print("\n🔄 批量测试:")
    print("- 测试1: 无字幕唱歌")
    print("- 测试2: 有字幕唱歌（无LRC文件）")

    # 创建示例LRC文件
    lrc_file = create_test_lrc_file()
    print(f"\n📄 示例LRC文件已创建: {lrc_file}")
    print("你可以将此文件用于测试字幕功能")

    print("\n🎯 测试步骤:")
    print("1. 启动main.py")
    print("2. 启动webapi_tester.py")
    print("3. 在唱歌测试中尝试不同的字幕设置")
    print("4. 观察字幕是否正确显示")

    return lrc_file

if __name__ == "__main__":
    test_file = test_subtitle_functionality()
    print(f"\n💡 提示: 测试完成后可以删除临时文件: {test_file}")
