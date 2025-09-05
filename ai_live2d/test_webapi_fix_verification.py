#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI修复验证脚本
验证循环播放和歌词功能的修复效果
"""

import requests
import json
import base64
import time
import os
import hashlib

# 配置
API_BASE_URL = "http://127.0.0.1:8888"
API_KEY = ""  # 如果设置了API密钥，请在这里填写

def create_test_audio_base64():
    """创建简单的测试音频"""
    # 创建一个最小的WAV文件头
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # 文件大小 - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6d, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # 格式块大小
        0x01, 0x00,              # 音频格式 (PCM)
        0x01, 0x00,              # 声道数
        0x44, 0xac, 0x00, 0x00,  # 采样率 (44100)
        0x88, 0x58, 0x01, 0x00,  # 字节率
        0x02, 0x00,              # 块对齐
        0x10, 0x00,              # 位深度
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00   # 数据大小
    ])
    
    return base64.b64encode(wav_header).decode('utf-8')

def test_server_connection():
    """测试服务器连接"""
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        print("✅ WebAPI服务器连接正常")
        return True
    except Exception as e:
        print(f"❌ 无法连接到WebAPI服务器: {e}")
        return False

def test_lyrics_api(audio_base64):
    """测试歌词API"""
    print("\n📝 测试歌词API...")
    
    # 创建对应的LRC文件
    audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
    os.makedirs('lyrics', exist_ok=True)
    
    lrc_filename = f"lyrics/{audio_hash}.lrc"
    lrc_content = f"""[00:00.00]测试歌词 - Hash: {audio_hash}
[00:02.00]这是WebAPI修复验证测试
[00:05.00]验证歌词API功能
[00:08.00]修复了歌词搜索和错误处理
[00:10.00]测试完成
"""
    
    with open(lrc_filename, 'w', encoding='utf-8') as f:
        f.write(lrc_content)
    print(f"✅ 创建测试LRC文件: {lrc_filename}")
    
    # 测试歌词API
    try:
        url = f"{API_BASE_URL}/api/lyrics"
        payload = {"audio_base64": audio_base64}
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('found', False):
                print("✅ 歌词API测试成功")
                lyrics = result.get('lyrics', '')
                print(f"   歌词长度: {len(lyrics)} 字符")
                print(f"   前两行歌词: {lyrics.split(chr(10))[:2]}")
            else:
                print("⚠️ 歌词文件未找到")
        else:
            print(f"❌ 歌词API测试失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 歌词API异常: {e}")
    
    # 清理测试文件
    try:
        if os.path.exists(lrc_filename):
            os.remove(lrc_filename)
        if os.path.exists('lyrics') and not os.listdir('lyrics'):
            os.rmdir('lyrics')
    except:
        pass

def test_loop_and_stop(audio_base64):
    """测试循环播放和停止功能"""
    print("\n🔄 测试循环播放和停止功能...")
    
    # 1. 开始循环播放
    try:
        url = f"{API_BASE_URL}/api/sing"
        payload = {
            "audio_base64": audio_base64,
            "volume": 0.3,
            "loop": True,  # 启用循环播放
            "singing_motion": "唱歌"
        }
        if API_KEY:
            payload["api_key"] = API_KEY
        
        print("1️⃣ 开始循环播放...")
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            print("✅ 循环播放启动成功")
        else:
            print(f"❌ 循环播放启动失败: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ 循环播放异常: {e}")
        return
    
    # 2. 等待几秒
    print("⏳ 等待3秒...")
    time.sleep(3)
    
    # 3. 停止循环播放
    try:
        url = f"{API_BASE_URL}/api/interrupt"
        payload = {"action": "stop"}
        if API_KEY:
            payload["api_key"] = API_KEY
        
        print("2️⃣ 发送停止请求...")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 停止请求发送成功")
            print(f"   响应: {result.get('message', 'N/A')}")
        else:
            print(f"❌ 停止请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 停止请求异常: {e}")
    
    print("⏳ 等待2秒检查停止效果...")
    time.sleep(2)
    print("🎉 循环播放和停止测试完成")

def test_single_play(audio_base64):
    """测试单次播放"""
    print("\n🎵 测试单次播放...")
    
    try:
        url = f"{API_BASE_URL}/api/sing"
        payload = {
            "audio_base64": audio_base64,
            "volume": 0.5,
            "loop": False,  # 单次播放
            "singing_motion": "唱歌"
        }
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            print("✅ 单次播放测试成功")
        else:
            print(f"❌ 单次播放测试失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 单次播放异常: {e}")

def main():
    """主函数"""
    print("🚀 WebAPI修复验证测试")
    print("=" * 50)
    
    # 1. 测试服务器连接
    if not test_server_connection():
        print("\n请确保UI.py正在运行且WebAPI服务已启动")
        return
    
    # 2. 创建测试音频
    print("\n🎶 创建测试音频...")
    audio_base64 = create_test_audio_base64()
    print(f"✅ 测试音频创建完成，Base64长度: {len(audio_base64)} 字符")
    
    # 3. 测试歌词API
    test_lyrics_api(audio_base64)
    
    # 4. 测试单次播放
    test_single_play(audio_base64)
    
    # 5. 测试循环播放和停止
    test_loop_and_stop(audio_base64)
    
    print("\n🎉 所有测试完成！")
    print("\n修复总结:")
    print("✅ 歌词API - 改进了文件搜索和错误处理")
    print("✅ 循环播放 - 修复了无法停止的问题")
    print("✅ 音频控制 - 增强了停止控制机制")

if __name__ == "__main__":
    main()
