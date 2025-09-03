#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI测试脚本
用于测试WebAPI服务是否正常工作
"""

import requests
import json
import time

def test_webapi_status(host='127.0.0.1', port=8888):
    """测试WebAPI状态"""
    url = f"http://{host}:{port}/api/status"
    try:
        response = requests.get(url, timeout=5)
        print(f"状态检查: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return True
    except Exception as e:
        print(f"状态检查失败: {e}")
        return False

def test_webapi_chat(host='127.0.0.1', port=8888, api_key=None):
    """测试WebAPI聊天功能"""
    url = f"http://{host}:{port}/api/chat"
    
    # 测试数据
    test_messages = [
        "你好",
        "今天天气怎么样？",
        "请介绍一下你自己",
        "1+1等于几？"
    ]
    
    for message in test_messages:
        print(f"\n发送消息: {message}")
        
        data = {"message": message}
        if api_key:
            data["api_key"] = api_key
        
        try:
            response = requests.post(
                url, 
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"响应代码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"回复: {result.get('response', 'No response')}")
                print(f"状态: {result.get('status', 'Unknown')}")
            else:
                print(f"错误响应: {response.text}")
                
        except Exception as e:
            print(f"请求失败: {e}")
        
        time.sleep(1)  # 避免请求过于频繁

def test_webapi_dialogue(host='127.0.0.1', port=8888, api_key=None):
    """测试WebAPI台词转换功能"""
    url = f"http://{host}:{port}/api/dialogue"
    
    print("\n=== 测试台词转换功能 ===")
    
    # 测试台词
    test_dialogues = [
        "你好，我是小明",
        "今天天气真不错",
        "我喜欢吃苹果",
        "谢谢你的帮助"
    ]
    
    for dialogue in test_dialogues:
        print(f"\n转换台词: {dialogue}")
        
        data = {"dialogue": dialogue}
        if api_key:
            data["api_key"] = api_key
        
        try:
            response = requests.post(
                url, 
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15  # 台词转换可能需要更长时间
            )
            
            print(f"响应代码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"原始台词: {result.get('original_dialogue', 'N/A')}")
                print(f"转换后: {result.get('converted_dialogue', 'No response')}")
                print(f"状态: {result.get('status', 'Unknown')}")
            else:
                print(f"错误响应: {response.text}")
                
        except Exception as e:
            print(f"请求失败: {e}")
        
        time.sleep(2)  # 台词转换需要更多时间，避免请求过于频繁

def test_webapi_interrupt(host='127.0.0.1', port=8888, api_key=None):
    """测试WebAPI打断功能"""
    url = f"http://{host}:{port}/api/interrupt"
    
    print("\n=== 测试打断功能 ===")
    
    data = {}
    if api_key:
        data["api_key"] = api_key
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"响应代码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"消息: {result.get('message', 'No message')}")
            print(f"状态: {result.get('status', 'Unknown')}")
        else:
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

def test_webapi_errors(host='127.0.0.1', port=8888):
    """测试WebAPI错误处理"""
    chat_url = f"http://{host}:{port}/api/chat"
    dialogue_url = f"http://{host}:{port}/api/dialogue"
    
    print("\n=== 测试错误处理 ===")
    
    # 测试聊天API错误
    print("\n测试聊天API错误:")
    
    # 测试空消息
    print("\n测试空消息:")
    try:
        response = requests.post(chat_url, json={"message": ""}, timeout=5)
        print(f"响应代码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试缺少消息字段
    print("\n测试缺少消息字段:")
    try:
        response = requests.post(chat_url, json={"text": "hello"}, timeout=5)
        print(f"响应代码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试台词API错误
    print("\n测试台词API错误:")
    
    # 测试空台词
    print("\n测试空台词:")
    try:
        response = requests.post(dialogue_url, json={"dialogue": ""}, timeout=5)
        print(f"响应代码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试缺少台词字段
    print("\n测试缺少台词字段:")
    try:
        response = requests.post(dialogue_url, json={"text": "hello"}, timeout=5)
        print(f"响应代码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试无效JSON
    print("\n测试无效JSON:")
    try:
        response = requests.post(
            chat_url, 
            data="invalid json",
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        print(f"响应代码: {response.status_code}")
        print(f"响应内容: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")

def main():
    """主函数"""
    print("WebAPI 测试脚本")
    print("=" * 50)
    
    host = input("请输入服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port = input("请输入端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("请输入API密钥 (可选，直接回车跳过): ").strip() or None
    
    try:
        port = int(port)
    except ValueError:
        print("端口号必须是数字！")
        return
    
    print(f"\n开始测试 {host}:{port}")
    
    # 测试状态
    print("\n1. 测试服务状态")
    if not test_webapi_status(host, port):
        print("服务不可用，请检查WebAPI服务是否启动！")
        return
    
    # 测试聊天
    print("\n2. 测试聊天功能")
    test_webapi_chat(host, port, api_key)
    
    # 测试台词转换
    print("\n3. 测试台词转换功能")
    test_webapi_dialogue(host, port, api_key)
    
    # 测试打断功能
    print("\n4. 测试打断功能")
    test_webapi_interrupt(host, port, api_key)
    
    # 测试错误处理
    print("\n5. 测试错误处理")
    test_webapi_errors(host, port)
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()
