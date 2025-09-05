#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LRC歌词功能完整示例
演示如何创建LRC文件并与音频同步播放
"""

import os
import hashlib
import base64
import json
import time

def create_complete_example():
    """创建完整的LRC歌词示例"""
    print("🎵 创建LRC歌词功能完整示例")
    print("=" * 50)
    
    # 1. 创建示例音频数据（实际使用中这里是真实的音频文件）
    print("1️⃣  创建示例音频数据...")
    
    # 模拟音频数据
    example_audio_data = b"Example audio data for LRC demo - replace with real audio file content"
    
    # 编码为base64
    audio_base64 = base64.b64encode(example_audio_data).decode('utf-8')
    
    # 计算音频哈希
    audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
    
    print(f"   音频哈希: {audio_hash}")
    print(f"   Base64长度: {len(audio_base64)} 字符")
    
    # 2. 创建lyrics目录
    print("\n2️⃣  创建lyrics目录...")
    lyrics_dir = "lyrics"
    if not os.path.exists(lyrics_dir):
        os.makedirs(lyrics_dir)
        print(f"   ✅ 创建目录: {lyrics_dir}")
    else:
        print(f"   📁 目录已存在: {lyrics_dir}")
    
    # 3. 创建对应的LRC文件
    print("\n3️⃣  创建LRC歌词文件...")
    lrc_filename = os.path.join(lyrics_dir, f"{audio_hash}.lrc")
    
    lrc_content = f"""[ar:示例歌手]
[ti:LRC功能演示歌曲]
[al:AI桌面宠物演示专辑]
[by:系统自动生成]
[offset:0]

[00:00.00]🎵 LRC歌词功能演示开始
[00:04.00]这是第一句演示歌词
[00:08.00]歌词会按照时间轴显示
[00:12.00]支持中文、English和🎼符号
[00:16.00]
[00:18.00]现在演示间奏效果
[00:22.00]空行代表没有歌词的时间段
[00:26.00]系统会自动处理时间同步
[00:30.00]
[00:32.00]音频哈希: {audio_hash}
[00:36.00]文件路径: {lrc_filename}
[00:40.00]配置要求: subtitle_enabled = true
[00:44.00]
[00:46.00]API接口: POST /api/sing
[00:50.00]参数包含: audio_data (base64)
[00:54.00]系统自动: 查找并解析LRC
[00:58.00]
[01:00.00]🎉 演示即将结束
[01:04.00]感谢使用AI桌面宠物系统
[01:08.00]LRC歌词功能演示完成！"""
    
    with open(lrc_filename, 'w', encoding='utf-8') as f:
        f.write(lrc_content)
    
    print(f"   ✅ 创建LRC文件: {lrc_filename}")
    
    # 4. 检查config.json配置
    print("\n4️⃣  检查配置文件...")
    config_file = "config.json"
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            subtitle_enabled = config.get('setting', {}).get('subtitle_enabled', False)
            
            if subtitle_enabled:
                print("   ✅ 字幕功能已启用")
            else:
                print("   ⚠️  字幕功能未启用")
                print("   💡 请在config.json中设置:")
                print('      "setting": {"subtitle_enabled": true}')
        
        except Exception as e:
            print(f"   ❌ 读取配置文件失败: {e}")
    else:
        print("   ⚠️  未找到config.json文件")
        print("   💡 请确保配置文件存在并包含字幕设置")
    
    # 5. 显示使用说明
    print("\n5️⃣  使用说明")
    print("   📝 配置要求:")
    print("      - 在config.json中启用字幕: \"subtitle_enabled\": true")
    print("      - 重启main.py程序")
    
    print("\n   🎵 播放方式:")
    print("      - 通过WebAPI发送音频数据")
    print("      - 系统自动查找对应的LRC文件")
    print("      - 歌词按时间轴实时显示")
    
    print("\n   🔧 API请求示例:")
    print("      POST /api/sing")
    print("      {")
    print(f'        "audio_data": "{audio_base64[:50]}..."')
    print('        "volume": 1.0,')
    print('        "loop": false,')
    print('        "singing_motion": "唱歌"')
    print("      }")
    
    # 6. 显示文件信息
    print("\n6️⃣  生成的文件:")
    print(f"   📄 LRC文件: {lrc_filename}")
    print(f"   🏷️  音频哈希: {audio_hash}")
    print(f"   📏 歌词行数: {len([l for l in lrc_content.split(chr(10)) if l.strip() and '[' in l])}")
    
    # 7. 验证功能
    print("\n7️⃣  功能验证:")
    
    try:
        # 导入LRC管理器
        from utils.lrc_manager import LRCParser
        
        # 解析LRC内容
        lyrics, metadata = LRCParser.parse_lrc_content(lrc_content)
        
        print(f"   ✅ LRC解析成功: {len(lyrics)}行歌词")
        print(f"   📊 歌曲信息: {metadata.get('ti', '未知')} - {metadata.get('ar', '未知')}")
        
        # 显示前几行歌词
        print("   🎤 歌词预览:")
        for i, lyric in enumerate(lyrics[:3]):
            minutes = lyric.time_ms // 60000
            seconds = (lyric.time_ms % 60000) // 1000
            print(f"      [{minutes:02d}:{seconds:02d}] {lyric.text}")
        
        if len(lyrics) > 3:
            print(f"      ... 还有 {len(lyrics) - 3} 行歌词")
    
    except ImportError:
        print("   ⚠️  LRC管理器未找到，请确保utils/lrc_manager.py存在")
    except Exception as e:
        print(f"   ❌ 验证失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ LRC歌词功能示例创建完成！")
    
    return {
        "audio_hash": audio_hash,
        "lrc_file": lrc_filename,
        "audio_base64": audio_base64
    }

def test_integration():
    """测试与现有系统的集成"""
    print("\n🔗 测试系统集成...")
    
    try:
        # 测试UI.py的_get_lrc_lyrics方法
        print("1️⃣  测试LRC文件查找功能...")
        
        # 创建示例
        example_info = create_complete_example()
        
        # 模拟UI.py中的查找逻辑
        audio_hash = example_info["audio_hash"]
        possible_paths = [
            f"lyrics/{audio_hash}.lrc",
            f"lrc/{audio_hash}.lrc",
            f"{audio_hash}.lrc"
        ]
        
        found_lrc = None
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    found_lrc = f.read()
                print(f"   ✅ 找到LRC文件: {path}")
                break
        
        if found_lrc:
            print(f"   📏 歌词长度: {len(found_lrc)} 字符")
        else:
            print("   ❌ 未找到LRC文件")
        
        print("\n2️⃣  测试消息队列集成...")
        try:
            from utils.message_queue import MessageQueue
            
            # 模拟发送播放请求
            play_audio_data = {
                "audio_data": example_info["audio_base64"],
                "volume": 1.0,
                "loop": False,
                "singing_motion": "唱歌",
                "lrc_content": found_lrc if found_lrc else "",
                "timestamp": time.time(),
                "source": "integration_test"
            }
            
            print("   ✅ 消息队列数据构造成功")
            print(f"   🎵 包含LRC内容: {'是' if found_lrc else '否'}")
            
        except ImportError:
            print("   ⚠️  消息队列模块未找到")
        
    except Exception as e:
        print(f"   ❌ 集成测试失败: {e}")

def main():
    """主函数"""
    print("🚀 LRC歌词功能完整示例")
    print("本示例将演示如何创建和使用LRC歌词功能\n")
    
    try:
        # 创建示例
        example_info = create_complete_example()
        
        # 测试集成
        test_integration()
        
        print("\n📖 下一步操作:")
        print("1. 确保config.json中启用了字幕功能")
        print("2. 启动main.py程序")
        print("3. 通过WebAPI发送音频数据")
        print("4. 观察LRC歌词的时间同步显示")
        
        print("\n🛠️  调试提示:")
        print("- 查看pet_system.log中的LRC相关日志")
        print("- 运行 python test_lrc_lyrics.py 进行功能测试")
        print("- 确保LRC文件使用UTF-8编码")
        
    except Exception as e:
        print(f"\n❌ 示例创建失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
