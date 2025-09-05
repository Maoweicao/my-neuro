#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LRC歌词功能测试
测试LRC歌词解析和时间同步显示功能
"""

import os
import time
import threading
import hashlib
import base64
from utils.lrc_manager import LRCManager, LRCParser

def create_test_lrc_file():
    """创建测试LRC歌词文件"""
    print("📝 创建测试LRC歌词文件...")
    
    # 确保lyrics目录存在
    lyrics_dir = "lyrics"
    if not os.path.exists(lyrics_dir):
        os.makedirs(lyrics_dir)
    
    # 创建测试音频数据（模拟）
    test_audio_data = b"fake_audio_data_for_testing"
    audio_base64 = base64.b64encode(test_audio_data).decode('utf-8')
    audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
    
    # 创建LRC文件路径
    lrc_filename = os.path.join(lyrics_dir, f"{audio_hash}.lrc")
    
    # LRC歌词内容
    lrc_content = f"""[ar:测试歌手]
[ti:LRC歌词测试歌曲]
[al:测试专辑]
[by:AI Live2D Pet System]
[offset:0]

[00:00.00]欢迎使用LRC歌词显示功能
[00:03.50]这是第一句测试歌词
[00:07.00]现在时间同步显示歌词
[00:10.50]每一句都会按时间显示
[00:14.00]这是一句较长的歌词，用来测试长文本的显示效果
[00:17.50]支持中文和英文混合显示
[00:21.00]English lyrics are also supported
[00:24.50]可以在config.json中启用字幕功能
[00:28.00]LRC歌词会自动按时间播放
[00:31.50]
[00:33.00]空行表示间奏或停顿
[00:36.50]继续播放后面的歌词
[00:40.00]这是最后一句测试歌词
[00:43.50]感谢使用AI桌面宠物系统！"""
    
    # 写入LRC文件
    with open(lrc_filename, 'w', encoding='utf-8') as f:
        f.write(lrc_content)
    
    print(f"✅ 创建测试LRC文件: {lrc_filename}")
    print(f"   音频哈希: {audio_hash}")
    print(f"   歌词行数: {len(lrc_content.split('['))}")
    
    return lrc_filename, audio_base64, audio_hash

def test_lrc_parser():
    """测试LRC解析器"""
    print("\n🧪 测试LRC解析器...")
    
    # 创建测试LRC文件
    lrc_filename, audio_base64, audio_hash = create_test_lrc_file()
    
    # 读取LRC文件内容
    with open(lrc_filename, 'r', encoding='utf-8') as f:
        lrc_content = f.read()
    
    # 解析LRC内容
    lyrics, metadata = LRCParser.parse_lrc_content(lrc_content)
    
    print(f"📊 解析结果:")
    print(f"   元数据: {metadata}")
    print(f"   歌词行数: {len(lyrics)}")
    print(f"   歌词内容预览:")
    
    for i, lyric in enumerate(lyrics[:5]):  # 显示前5行
        print(f"     [{i+1}] {lyric.time_ms}ms: {lyric.text}")
    
    if len(lyrics) > 5:
        print(f"     ... 还有 {len(lyrics) - 5} 行歌词")
    
    return lyrics, metadata, lrc_filename

def test_lrc_manager():
    """测试LRC管理器"""
    print("\n🎵 测试LRC管理器...")
    
    # 创建LRC管理器
    lrc_manager = LRCManager()
    
    # 创建测试LRC文件
    lrc_filename, audio_base64, audio_hash = create_test_lrc_file()
    
    # 读取LRC文件内容
    with open(lrc_filename, 'r', encoding='utf-8') as f:
        lrc_content = f.read()
    
    # 加载LRC内容
    if lrc_manager.load_lrc_content(lrc_content):
        print("✅ LRC内容加载成功")
        
        # 设置歌词变化回调
        def on_lyric_changed(text):
            if text.strip():
                print(f"🎤 当前歌词: {text}")
            else:
                print("🎤 当前歌词: [间奏]")
        
        lrc_manager.lyric_changed.connect(on_lyric_changed)
        
        # 模拟播放
        print("▶️  开始模拟播放...")
        lrc_manager.start_playback()
        
        # 等待一段时间观察歌词显示
        try:
            time.sleep(15)  # 播放15秒
        except KeyboardInterrupt:
            print("\n⏹️  用户中断播放")
        
        # 停止播放
        lrc_manager.stop_playback()
        print("⏹️  播放已停止")
        
        # 显示歌词信息
        info = lrc_manager.get_lyric_info()
        print(f"📊 歌词信息: {info}")
        
    else:
        print("❌ LRC内容加载失败")

def test_seek_functionality():
    """测试跳转功能"""
    print("\n⏩ 测试跳转功能...")
    
    # 创建LRC管理器
    lrc_manager = LRCManager()
    
    # 创建测试LRC文件
    lrc_filename, audio_base64, audio_hash = create_test_lrc_file()
    
    # 读取LRC文件内容
    with open(lrc_filename, 'r', encoding='utf-8') as f:
        lrc_content = f.read()
    
    # 加载LRC内容
    if lrc_manager.load_lrc_content(lrc_content):
        # 设置歌词变化回调
        def on_lyric_changed(text):
            current_info = lrc_manager.get_lyric_info()
            current_time = current_info['current_time_ms']
            print(f"🎤 [{current_time//1000:02d}:{(current_time%1000)//10:02d}] {text}")
        
        lrc_manager.lyric_changed.connect(on_lyric_changed)
        
        # 开始播放
        lrc_manager.start_playback()
        
        # 测试跳转到不同时间点
        test_times = [5000, 15000, 25000, 35000]  # 5秒、15秒、25秒、35秒
        
        for seek_time in test_times:
            print(f"\n⏩ 跳转到 {seek_time//1000} 秒...")
            lrc_manager.seek_to_time(seek_time)
            time.sleep(3)  # 等待3秒观察效果
        
        # 停止播放
        lrc_manager.stop_playback()
        print("⏹️  跳转测试完成")
    
    else:
        print("❌ LRC内容加载失败")

def test_integration_with_ui():
    """测试与UI集成"""
    print("\n🔗 测试与UI集成...")
    
    # 创建测试LRC文件
    lrc_filename, audio_base64, audio_hash = create_test_lrc_file()
    
    print(f"📁 测试文件信息:")
    print(f"   LRC文件: {lrc_filename}")
    print(f"   音频Base64: {audio_base64[:50]}...")
    print(f"   音频哈希: {audio_hash}")
    
    # 模拟UI.py中的_get_lrc_lyrics方法
    def simulate_get_lrc_lyrics(audio_base64):
        """模拟UI.py中的获取LRC歌词方法"""
        try:
            import hashlib
            
            # 生成音频文件的哈希值
            audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
            
            # 可能的lrc文件路径
            possible_paths = [
                os.path.join("lyrics", f"{audio_hash}.lrc"),
                os.path.join("lrc", f"{audio_hash}.lrc"),
                f"{audio_hash}.lrc"
            ]
            
            for lrc_path in possible_paths:
                if os.path.exists(lrc_path):
                    with open(lrc_path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
            
            return ""
        except Exception as e:
            print(f"⚠️  获取LRC歌词失败: {e}")
            return ""
    
    # 测试获取LRC歌词
    lrc_content = simulate_get_lrc_lyrics(audio_base64)
    
    if lrc_content:
        print("✅ 成功获取LRC歌词内容")
        print(f"   歌词长度: {len(lrc_content)} 字符")
        
        # 解析歌词
        lyrics, metadata = LRCParser.parse_lrc_content(lrc_content)
        print(f"   解析得到 {len(lyrics)} 行歌词")
        print(f"   歌曲信息: {metadata.get('ti', '未知')} - {metadata.get('ar', '未知')}")
        
    else:
        print("❌ 未能获取LRC歌词内容")

def cleanup_test_files():
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    try:
        # 删除测试LRC文件
        lyrics_dir = "lyrics"
        if os.path.exists(lyrics_dir):
            for filename in os.listdir(lyrics_dir):
                if filename.endswith('.lrc'):
                    file_path = os.path.join(lyrics_dir, filename)
                    os.remove(file_path)
                    print(f"🗑️  删除文件: {file_path}")
            
            # 如果目录为空，删除目录
            if not os.listdir(lyrics_dir):
                os.rmdir(lyrics_dir)
                print(f"🗑️  删除目录: {lyrics_dir}")
        
        print("✅ 清理完成")
        
    except Exception as e:
        print(f"⚠️  清理失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始LRC歌词功能测试")
    print("=" * 50)
    
    try:
        # 1. 测试LRC解析器
        test_lrc_parser()
        
        # 2. 测试LRC管理器
        test_lrc_manager()
        
        # 3. 测试跳转功能
        test_seek_functionality()
        
        # 4. 测试与UI集成
        test_integration_with_ui()
        
        print("\n" + "=" * 50)
        print("✅ LRC歌词功能测试完成！")
        print("\n📝 使用说明:")
        print("1. 将LRC文件放入 lyrics/ 目录")
        print("2. LRC文件名格式: {音频哈希}.lrc")
        print("3. 在config.json中启用字幕功能")
        print("4. 播放音频时会自动显示LRC歌词")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 询问是否清理测试文件
        try:
            user_input = input("\n是否清理测试文件? (y/N): ").strip().lower()
            if user_input in ['y', 'yes']:
                cleanup_test_files()
            else:
                print("💾 保留测试文件用于进一步测试")
        except KeyboardInterrupt:
            print("\n💾 保留测试文件")

if __name__ == "__main__":
    main()
