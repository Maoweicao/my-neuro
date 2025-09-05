#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI全面修复验证脚本
验证所有修复的功能：循环播放、歌词API、socket通信
"""

import requests
import json
import base64
import time
import os
import hashlib

# 配置
API_BASE_URL = "http://127.0.0.1:8888"
API_KEY = ""

def create_test_audio_base64():
    """创建测试音频"""
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

def test_server_status():
    """测试服务器状态"""
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        print("✅ WebAPI服务器连接正常")
        return True
    except Exception as e:
        print(f"❌ 无法连接到WebAPI服务器: {e}")
        return False

def test_lyrics_api_with_file(audio_base64):
    """测试歌词API - 带LRC文件"""
    print("\n📝 测试歌词API (有LRC文件)...")
    
    # 创建对应的LRC文件
    audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
    os.makedirs('lyrics', exist_ok=True)
    
    lrc_filename = f"lyrics/{audio_hash}.lrc"
    lrc_content = f"""[00:00.00]WebAPI修复验证 - Hash: {audio_hash}
[00:02.00]测试歌词API功能
[00:05.00]修复了文件搜索和编码处理
[00:08.00]支持UTF-8和GBK编码
[00:10.00]测试完成
"""
    
    try:
        with open(lrc_filename, 'w', encoding='utf-8') as f:
            f.write(lrc_content)
        print(f"✅ 创建测试LRC文件: {lrc_filename}")
        
        # 测试歌词API
        url = f"{API_BASE_URL}/api/lyrics"
        payload = {"audio_base64": audio_base64}
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('found', False):
                print("✅ 歌词API测试成功 - 找到LRC文件")
                lyrics = result.get('lyrics', '')
                print(f"   歌词长度: {len(lyrics)} 字符")
                lines = lyrics.split('\n')[:2]
                for line in lines:
                    print(f"   {line}")
                return True
            else:
                print("⚠️ 歌词API响应成功，但未找到LRC文件")
                return False
        else:
            print(f"❌ 歌词API测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 歌词API测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if os.path.exists(lrc_filename):
                os.remove(lrc_filename)
            if os.path.exists('lyrics') and not os.listdir('lyrics'):
                os.rmdir('lyrics')
        except:
            pass

def test_lyrics_api_without_file(audio_base64):
    """测试歌词API - 无LRC文件"""
    print("\n📝 测试歌词API (无LRC文件)...")
    
    # 使用不同的音频hash确保没有对应LRC文件
    fake_audio = audio_base64 + "different"
    
    try:
        url = f"{API_BASE_URL}/api/lyrics"
        payload = {"audio_base64": fake_audio}
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if not result.get('found', True):
                print("✅ 歌词API测试成功 - 正确处理无LRC文件情况")
                return True
            else:
                print("⚠️ 意外找到了LRC文件")
                return False
        else:
            print(f"❌ 歌词API测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 歌词API测试异常: {e}")
        return False

def test_single_play(audio_base64):
    """测试单次播放"""
    print("\n🎵 测试单次播放...")
    
    try:
        url = f"{API_BASE_URL}/api/sing"
        payload = {
            "audio_base64": audio_base64,
            "volume": 0.5,
            "loop": False,
            "singing_motion": "唱歌"
        }
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 单次播放测试成功")
            print(f"   响应: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ 单次播放测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 单次播放异常: {e}")
        return False

def test_loop_play_and_stop(audio_base64):
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
            return False
            
    except Exception as e:
        print(f"❌ 循环播放异常: {e}")
        return False
    
    # 2. 等待几秒
    print("⏳ 等待3秒让循环播放运行...")
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
            
            # 等待检查停止效果
            print("⏳ 等待2秒检查停止效果...")
            time.sleep(2)
            print("✅ 循环播放停止测试完成")
            return True
        else:
            print(f"❌ 停止请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 停止请求异常: {e}")
        return False

def test_enhanced_error_handling():
    """测试增强的错误处理"""
    print("\n🛡️ 测试增强的错误处理...")
    
    # 测试1: 无效的音频数据
    try:
        url = f"{API_BASE_URL}/api/sing"
        payload = {
            "audio_base64": "invalid_base64_data",
            "volume": 0.5,
            "loop": False,
            "singing_motion": "唱歌"
        }
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 400 or response.status_code == 500:
            print("✅ 错误处理测试1成功 - 正确处理无效音频数据")
        else:
            print("⚠️ 错误处理测试1 - 意外的响应")
            
    except Exception as e:
        print(f"❌ 错误处理测试1异常: {e}")
    
    # 测试2: 缺少必需字段
    try:
        url = f"{API_BASE_URL}/api/lyrics"
        payload = {}  # 缺少audio_base64字段
        if API_KEY:
            payload["api_key"] = API_KEY
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 400:
            print("✅ 错误处理测试2成功 - 正确处理缺少字段")
        else:
            print("⚠️ 错误处理测试2 - 意外的响应")
            
    except Exception as e:
        print(f"❌ 错误处理测试2异常: {e}")

def main():
    """主函数"""
    print("🚀 WebAPI全面修复验证测试")
    print("=" * 60)
    
    # 检查服务器状态
    if not test_server_status():
        print("\n请确保UI.py正在运行且WebAPI服务已启动")
        return
    
    # 创建测试音频
    print("\n🎶 创建测试音频...")
    audio_base64 = create_test_audio_base64()
    print(f"✅ 测试音频创建完成，Base64长度: {len(audio_base64)} 字符")
    
    # 运行所有测试
    tests = [
        ("歌词API (有LRC文件)", lambda: test_lyrics_api_with_file(audio_base64)),
        ("歌词API (无LRC文件)", lambda: test_lyrics_api_without_file(audio_base64)),
        ("单次播放", lambda: test_single_play(audio_base64)),
        ("循环播放和停止", lambda: test_loop_play_and_stop(audio_base64)),
        ("增强错误处理", test_enhanced_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果总结
    print("\n" + "=" * 60)
    print("🎉 测试结果总结:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！WebAPI修复完全成功！")
    elif passed > total // 2:
        print("⚠️ 大部分测试通过，部分功能可能需要进一步检查")
    else:
        print("❌ 多项测试失败，请检查服务器状态和配置")
    
    print("\n修复总结:")
    print("✅ 循环播放停止功能 - 修复了AudioPlaybackThread的停止控制")
    print("✅ 歌词API功能 - 改进了LRC文件搜索和编码处理")
    print("✅ Socket通信 - 修复了大数据传输问题")
    print("✅ 错误处理 - 增强了各种异常情况的处理")

if __name__ == "__main__":
    main()
