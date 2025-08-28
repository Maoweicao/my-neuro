#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复后的WebAPI Live2D控制测试
"""
import requests
import json
import time

def test_webapi_status():
    """测试WebAPI状态"""
    try:
        url = "http://127.0.0.1:8888/api/status"
        response = requests.get(url, timeout=5)
        print(f"WebAPI状态: {response.status_code}")
        if response.status_code == 200:
            print(f"响应: {response.json()}")
            return True
        return False
    except Exception as e:
        print(f"WebAPI连接失败: {e}")
        return False

def test_live2d_motion_corrected():
    """测试Live2D动作控制 - 使用motion字段"""
    try:
        url = "http://127.0.0.1:8888/api/live2d/motion"
        data = {"motion": 0}  # 使用motion字段而不是motion_index
        
        print(f"\n发送动作请求 (修复版): {data}")
        response = requests.post(url, json=data, timeout=5)
        print(f"响应状态: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"动作控制失败: {e}")
        return False

def test_live2d_motion_index():
    """测试Live2D动作控制 - 使用motion_index字段"""
    try:
        url = "http://127.0.0.1:8888/api/live2d/motion"
        data = {"motion_index": 1}  # 使用motion_index字段
        
        print(f"\n发送动作请求 (motion_index版): {data}")
        response = requests.post(url, json=data, timeout=5)
        print(f"响应状态: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"动作控制失败: {e}")
        return False

def test_live2d_expression():
    """测试Live2D表情控制"""
    try:
        url = "http://127.0.0.1:8888/api/live2d/expression"
        data = {"expression": "happy"}
        
        print(f"\n发送表情请求: {data}")
        response = requests.post(url, json=data, timeout=5)
        print(f"响应状态: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"表情控制失败: {e}")
        return False

def test_multiple_motions():
    """测试多个动作"""
    print("\n=== 测试多个动作 ===")
    for i in range(3):
        print(f"\n触发动作 {i}:")
        data = {"motion": i}
        try:
            response = requests.post("http://127.0.0.1:8888/api/live2d/motion", 
                                   json=data, timeout=5)
            print(f"  状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  消息: {result.get('message', '')}")
            else:
                print(f"  错误: {response.text}")
        except Exception as e:
            print(f"  异常: {e}")
        
        time.sleep(1)  # 等待1秒

if __name__ == "__main__":
    print("=== 修复后的WebAPI Live2D 控制测试 ===")
    
    # 检查WebAPI状态
    if not test_webapi_status():
        print("请确保UI.py已启动并且WebAPI服务器已开启")
        exit(1)
    
    # 测试动作控制 (motion字段)
    test_live2d_motion_corrected()
    
    time.sleep(1)
    
    # 测试动作控制 (motion_index字段)
    test_live2d_motion_index()
    
    time.sleep(1)
    
    # 测试表情控制
    test_live2d_expression()
    
    # 测试多个动作
    test_multiple_motions()
    
    print("\n=== 测试完成 ===")
