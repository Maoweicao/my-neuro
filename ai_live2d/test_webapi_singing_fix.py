#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI歌曲循环播放和歌词发送功能测试脚本
"""

import requests
import json
import base64
import time
import os
import threading

# WebAPI服务器配置
API_BASE_URL = "http://127.0.0.1:8888"
API_KEY = "your_api_key_here"  # 如果设置了API密钥，请在这里填写

def create_test_audio():
    """创建一个简单的测试音频文件（WAV格式）"""
    import wave
    import numpy as np
    
    # 生成一个1秒的440Hz正弦波
    sample_rate = 44100
    duration = 1.0  # 1秒
    frequency = 440.0  # A音符
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(frequency * 2 * np.pi * t)
    
    # 转换为16位整数
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # 创建WAV文件
    with wave.open('test_audio.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(wave_data.tobytes())
    
    return 'test_audio.wav'

def create_test_lrc():
    """创建测试LRC歌词文件"""
    # 确保lyrics目录存在
    os.makedirs('lyrics', exist_ok=True)
    
    # 创建简单的LRC歌词
    lrc_content = """[00:00.00]测试歌曲
[00:05.00]这是一个测试歌词
[00:10.00]用来验证歌词显示功能
[00:15.00]歌词结束
"""
    
    return lrc_content

def test_singing_api(audio_base64, volume=1.0, loop=False, singing_motion="唱歌"):
    """测试唱歌API"""
    url = f"{API_BASE_URL}/api/sing"
    
    payload = {
        "audio_base64": audio_base64,
        "volume": volume,
        "loop": loop,
        "singing_motion": singing_motion,
        "api_key": API_KEY
    }
    
    try:
        print(f"🎵 发送唱歌请求...")
        print(f"   音量: {volume}")
        print(f"   循环: {loop}")
        print(f"   动作: {singing_motion}")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 唱歌请求成功: {result}")
            return True
        else:
            print(f"❌ 唱歌请求失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 唱歌请求异常: {e}")
        return False

def test_lyrics_api(audio_base64):
    """测试歌词API"""
    url = f"{API_BASE_URL}/api/lyrics"
    
    payload = {
        "audio_base64": audio_base64,
        "api_key": API_KEY
    }
    
    try:
        print(f"📝 发送歌词请求...")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 歌词请求成功: {result}")
            return True
        else:
            print(f"❌ 歌词请求失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 歌词请求异常: {e}")
        return False

def test_interrupt_api():
    """测试中断API"""
    url = f"{API_BASE_URL}/api/interrupt"
    
    payload = {
        "action": "stop",
        "api_key": API_KEY
    }
    
    try:
        print(f"⏹️ 发送中断请求...")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 中断请求成功: {result}")
            return True
        else:
            print(f"❌ 中断请求失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 中断请求异常: {e}")
        return False

def test_server_status():
    """测试服务器状态"""
    url = f"{API_BASE_URL}/"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ WebAPI服务器运行正常")
            return True
        else:
            print(f"❌ WebAPI服务器状态异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到WebAPI服务器: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始WebAPI歌曲循环播放和歌词发送功能测试")
    print("=" * 60)
    
    # 1. 检查服务器状态
    print("1. 检查WebAPI服务器状态...")
    if not test_server_status():
        print("❌ 服务器未运行，请先启动WebAPI服务器")
        return
    print()
    
    # 2. 创建测试音频
    print("2. 创建测试音频...")
    try:
        audio_file = create_test_audio()
        print(f"✅ 测试音频文件创建成功: {audio_file}")
        
        # 读取音频文件并转换为base64
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        print(f"✅ 音频数据编码完成，长度: {len(audio_base64)} 字符")
    except Exception as e:
        print(f"❌ 创建测试音频失败: {e}")
        return
    print()
    
    # 3. 创建测试歌词文件
    print("3. 创建测试歌词...")
    try:
        lrc_content = create_test_lrc()
        
        # 使用音频base64生成歌词文件名
        import hashlib
        audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
        lrc_filename = f"lyrics/{audio_hash}.lrc"
        
        with open(lrc_filename, 'w', encoding='utf-8') as f:
            f.write(lrc_content)
        print(f"✅ 测试歌词文件创建成功: {lrc_filename}")
    except Exception as e:
        print(f"❌ 创建测试歌词失败: {e}")
        lrc_filename = None
    print()
    
    # 4. 测试歌词API
    print("4. 测试歌词API...")
    test_lyrics_api(audio_base64)
    print()
    
    # 5. 测试单次播放
    print("5. 测试单次播放...")
    test_singing_api(audio_base64, volume=0.5, loop=False, singing_motion="唱歌")
    time.sleep(3)  # 等待播放完成
    print()
    
    # 6. 测试循环播放
    print("6. 测试循环播放...")
    test_singing_api(audio_base64, volume=0.3, loop=True, singing_motion="唱歌")
    
    # 等待5秒后停止循环播放
    print("   等待5秒后测试停止循环播放...")
    time.sleep(5)
    
    # 7. 测试中断功能
    print("7. 测试中断功能...")
    test_interrupt_api()
    print()
    
    # 8. 清理测试文件
    print("8. 清理测试文件...")
    try:
        if os.path.exists('test_audio.wav'):
            os.remove('test_audio.wav')
            print("✅ 删除测试音频文件")
        
        if lrc_filename and os.path.exists(lrc_filename):
            os.remove(lrc_filename)
            print("✅ 删除测试歌词文件")
            
        # 如果lyrics目录为空，则删除它
        if os.path.exists('lyrics') and not os.listdir('lyrics'):
            os.rmdir('lyrics')
            print("✅ 删除lyrics目录")
    except Exception as e:
        print(f"⚠️ 清理文件时出现错误: {e}")
    
    print()
    print("🎉 测试完成！")

if __name__ == "__main__":
    try:
        import numpy as np
        main()
    except ImportError:
        print("❌ 缺少numpy依赖，请安装: pip install numpy")
