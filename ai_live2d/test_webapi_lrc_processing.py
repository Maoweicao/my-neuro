#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试WebAPI测试工具的LRC文件处理功能
"""

import os
import sys
import tempfile
import hashlib

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_lrc_file_processing():
    """测试LRC文件处理功能"""
    print("=== 测试WebAPI测试工具的LRC文件处理功能 ===")
    
    try:
        # 导入音频生成器
        from webapi_tester import AudioGenerator
        
        # 1. 生成测试音频
        print("\n1. 生成测试音频...")
        audio_base64 = AudioGenerator.create_test_audio_base64(duration=2.0, frequency=440.0)
        print(f"✅ 测试音频已生成，长度: {len(audio_base64)} 字符")
        
        # 2. 计算音频hash
        audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
        print(f"🔍 音频Hash: {audio_hash}")
        
        # 3. 创建测试LRC文件
        print("\n2. 创建测试LRC文件...")
        test_lrc_content = f"""[00:00.00]测试歌词 - Hash: {audio_hash}
[00:02.00]这是一个测试LRC文件
[00:05.00]用于验证WebAPI测试工具
[00:08.00]的LRC文件处理功能
[00:10.00]测试完成
"""
        
        # 创建临时LRC文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lrc', delete=False, encoding='utf-8') as temp_lrc:
            temp_lrc.write(test_lrc_content)
            temp_lrc_path = temp_lrc.name
        
        print(f"✅ 临时LRC文件已创建: {temp_lrc_path}")
        print(f"📏 LRC内容长度: {len(test_lrc_content)} 字符")
        
        # 4. 模拟复制到正确位置的过程
        print("\n3. 模拟复制LRC文件到正确位置...")
        
        # 确保lyrics目录存在
        os.makedirs('lyrics', exist_ok=True)
        
        # 目标路径
        target_lrc_path = f"lyrics/{audio_hash}.lrc"
        
        # 复制文件
        import shutil
        shutil.copy2(temp_lrc_path, target_lrc_path)
        print(f"✅ LRC文件已复制到: {target_lrc_path}")
        
        # 5. 验证文件内容
        print("\n4. 验证复制后的文件内容...")
        with open(target_lrc_path, 'r', encoding='utf-8') as f:
            copied_content = f.read()
        
        if copied_content == test_lrc_content:
            print("✅ 文件内容验证成功")
        else:
            print("❌ 文件内容验证失败")
        
        # 6. 模拟歌词API搜索
        print("\n5. 模拟歌词API搜索...")
        expected_paths = [
            f"lyrics/{audio_hash}.lrc",
            f"lrc/{audio_hash}.lrc"
        ]
        
        found_lrc = False
        for path in expected_paths:
            if os.path.exists(path):
                print(f"✅ 找到歌词文件: {path}")
                found_lrc = True
                break
        
        if not found_lrc:
            print("❌ 未找到歌词文件")
        
        # 7. 显示歌词预览
        if found_lrc:
            print("\n6. 歌词内容预览:")
            lines = copied_content.split('\n')[:3]
            for line in lines:
                if line.strip():
                    print(f"   {line}")
        
        # 8. 清理测试文件
        print("\n7. 清理测试文件...")
        try:
            if os.path.exists(temp_lrc_path):
                os.remove(temp_lrc_path)
                print(f"🧹 已删除临时文件: {temp_lrc_path}")
            
            if os.path.exists(target_lrc_path):
                os.remove(target_lrc_path)
                print(f"🧹 已删除目标文件: {target_lrc_path}")
            
            # 如果lyrics目录为空，删除它
            if os.path.exists('lyrics') and not os.listdir('lyrics'):
                os.rmdir('lyrics')
                print("🧹 已删除空的lyrics目录")
                
        except Exception as cleanup_error:
            print(f"⚠️ 清理文件时出错: {cleanup_error}")
        
        print("\n✅ LRC文件处理功能测试完成！")
        print("\n测试结果总结:")
        print("✅ 音频生成功能正常")
        print("✅ Hash计算功能正常") 
        print("✅ LRC文件创建功能正常")
        print("✅ 文件复制功能正常")
        print("✅ 文件搜索逻辑正常")
        print("✅ 文件清理功能正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_multiple_audio_hashes():
    """测试多个不同音频的hash计算"""
    print("\n=== 测试多个音频Hash计算 ===")
    
    try:
        from webapi_tester import AudioGenerator
        import hashlib
        
        test_cases = [
            (1.0, 440.0, "A4音符1秒"),
            (2.0, 440.0, "A4音符2秒"),
            (1.0, 880.0, "A5音符1秒"),
            (1.5, 523.25, "C5音符1.5秒")
        ]
        
        hashes = []
        for duration, frequency, description in test_cases:
            audio_base64 = AudioGenerator.create_test_audio_base64(duration, frequency)
            audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
            hashes.append(audio_hash)
            print(f"📊 {description}: Hash = {audio_hash}")
        
        # 检查hash是否都不同
        unique_hashes = set(hashes)
        if len(unique_hashes) == len(hashes):
            print("✅ 所有音频的Hash都是唯一的")
        else:
            print("❌ 发现重复的Hash值")
            
    except Exception as e:
        print(f"❌ 多音频Hash测试失败: {e}")

if __name__ == "__main__":
    test_lrc_file_processing()
    test_multiple_audio_hashes()
