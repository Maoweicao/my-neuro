#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI 快速测试脚本
简单快速测试WebAPI功能
"""

import requests
import json

def quick_test():
    """快速测试WebAPI"""
    
    # 配置
    host = "127.0.0.1"
    port = 8888
    api_key = None  # 如果设置了密钥，请在这里填入
    
    base_url = f"http://{host}:{port}"
    
    print("🚀 WebAPI 快速测试")
    print("=" * 40)
    
    # 1. 测试服务状态
    print("1️⃣ 检查服务状态...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ 服务运行正常")
            print(f"   响应: {response.json()}")
        else:
            print(f"⚠️ 服务异常 (状态码: {response.status_code})")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return
    
    # 2. 测试聊天功能
    print("\n2️⃣ 测试聊天功能...")
    
    # 构建请求数据
    data = {
        "message": "你好，这是一个测试消息"
    }
    
    # 如果设置了API密钥，添加到请求中
    if api_key:
        data["api_key"] = api_key
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📤 发送消息: {data['message']}")
        
        response = requests.post(
            f"{base_url}/api/chat",
            json=data,
            headers=headers,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 聊天测试成功")
            print(f"📥 AI回复: {result.get('response', '无回复')}")
            print(f"🔖 状态: {result.get('status', '未知')}")
            
            if 'timestamp' in result:
                import time
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp']))
                print(f"⏰ 时间: {timestamp}")
        else:
            print("❌ 聊天测试失败")
            try:
                error_info = response.json()
                print(f"   错误: {error_info.get('error', '未知错误')}")
            except:
                print(f"   响应内容: {response.text}")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n🎉 快速测试完成!")

def custom_test():
    """自定义测试"""
    
    host = input("服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port = input("端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("API密钥 (可选): ").strip() or None
    message = input("测试消息 (默认: 你好): ").strip() or "你好"
    
    try:
        port = int(port)
    except ValueError:
        print("❌ 端口号必须是数字！")
        return
    
    # 构建请求
    url = f"http://{host}:{port}/api/chat"
    data = {"message": message}
    if api_key:
        data["api_key"] = api_key
    
    headers = {"Content-Type": "application/json"}
    
    print(f"\n🔄 发送请求到: {url}")
    print(f"📤 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"\n📊 响应状态码: {response.status_code}")
        print(f"📥 响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    print("WebAPI 测试工具")
    print("请选择测试模式:")
    print("1. 快速测试 (使用默认配置)")
    print("2. 自定义测试")
    
    choice = input("\n请输入选项 (1-2): ").strip()
    
    if choice == "1":
        quick_test()
    elif choice == "2":
        custom_test()
    else:
        print("❌ 无效选项")
