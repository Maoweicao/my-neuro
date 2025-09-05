#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试webapi_tester的歌词集成功能
验证在唱歌测试中上传LRC文件时会同时测试/api/lyrics接口
"""

import sys
import os
import hashlib
import base64
import io
import wave
import numpy as np

def create_test_audio_base64(duration=2.0, frequency=440.0, sample_rate=44100):
    """创建测试音频并返回base64"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    wav_data = buffer.getvalue()
    return base64.b64encode(wav_data).decode('utf-8')

def create_test_lrc_file():
    """创建测试LRC文件"""
    # 生成测试音频
    audio_base64 = create_test_audio_base64()
    
    # 计算hash
    audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
    
    # 确保lyrics目录存在
    os.makedirs('lyrics', exist_ok=True)
    
    # 创建LRC文件
    lrc_filename = f"lyrics/{audio_hash}.lrc"
    lrc_content = f"""[00:00.00]测试歌词 - webapi_tester集成测试
[00:02.00]音频Hash: {audio_hash}
[00:05.00]这是用于测试歌词集成功能的LRC文件
[00:08.00]当在webapi_tester中选择此LRC文件时
[00:10.00]应该会同时测试 /api/lyrics 接口
[00:12.00]测试完成
"""
    
    with open(lrc_filename, 'w', encoding='utf-8') as f:
        f.write(lrc_content)
    
    print(f"✅ 创建测试LRC文件: {lrc_filename}")
    print(f"   音频Hash: {audio_hash}")
    print(f"   歌词长度: {len(lrc_content)} 字符")
    
    # 同时创建测试音频文件
    audio_filename = f"test_audio_{audio_hash}.wav"
    wav_data = base64.b64decode(audio_base64)
    with open(audio_filename, 'wb') as f:
        f.write(wav_data)
    
    print(f"✅ 创建测试音频文件: {audio_filename}")
    
    return lrc_filename, audio_filename, audio_hash

def test_webapi_tester_integration():
    """测试webapi_tester的歌词集成功能"""
    print("🚀 开始测试webapi_tester的歌词集成功能")
    print()
    
    try:
        # 创建测试文件
        lrc_file, audio_file, audio_hash = create_test_lrc_file()
        
        print()
        print("📋 测试说明:")
        print("1. 启动webapi_tester.py")
        print("2. 进入'唱歌测试'标签页")
        print(f"3. 选择音频文件: {audio_file}")
        print(f"4. 选择LRC文件: {lrc_file}")
        print("5. 点击'发送唱歌请求'")
        print()
        print("✅ 预期结果:")
        print("- 应该先看到 '=== 测试歌词API (/api/lyrics) ===' 部分")
        print(f"- 显示音频Hash: {audio_hash}")
        print("- 显示歌词API的测试结果")
        print("- 然后看到 '=== 测试唱歌API (/api/sing) ===' 部分")
        print("- 最后执行正常的唱歌功能")
        print()
        
        # 检查文件是否创建成功
        if os.path.exists(lrc_file) and os.path.exists(audio_file):
            print("🎉 测试文件创建成功！")
            print()
            print("现在可以在webapi_tester中使用这些文件测试歌词集成功能")
        else:
            print("❌ 测试文件创建失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

def cleanup_test_files():
    """清理测试文件"""
    print("🧹 清理测试文件...")
    
    # 清理lyrics目录中的测试文件
    if os.path.exists('lyrics'):
        for file in os.listdir('lyrics'):
            if file.endswith('.lrc'):
                file_path = os.path.join('lyrics', file)
                try:
                    os.remove(file_path)
                    print(f"   删除: {file_path}")
                except Exception as e:
                    print(f"   删除失败 {file_path}: {e}")
        
        # 如果lyrics目录为空，删除它
        try:
            if not os.listdir('lyrics'):
                os.rmdir('lyrics')
                print("   删除空的lyrics目录")
        except Exception as e:
            print(f"   删除lyrics目录失败: {e}")
    
    # 清理测试音频文件
    for file in os.listdir('.'):
        if file.startswith('test_audio_') and file.endswith('.wav'):
            try:
                os.remove(file)
                print(f"   删除: {file}")
            except Exception as e:
                print(f"   删除失败 {file}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_test_files()
    else:
        test_webapi_tester_integration()
        print()
        print("💡 提示: 运行 'python test_webapi_tester_lyrics_integration.py cleanup' 可清理测试文件")
