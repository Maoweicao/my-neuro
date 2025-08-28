#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试WebAPI Live2D控制功能
"""

import requests
import json
import time

def test_live2d_motion(motion_index=0):
    """测试Live2D动作控制"""
    try:
        url = "http://127.0.0.1:8888/api/live2d/motion"
        data = {
            "motion": motion_index
        }
        
        print(f"发送动作请求: {json.dumps(data, indent=2)}")
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"动作控制成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"动作控制失败 - 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"动作控制异常: {e}")
        return False

def test_live2d_expression(expression_name="happy"):
    """测试Live2D表情控制"""
    try:
        url = "http://127.0.0.1:8888/api/live2d/expression"
        data = {
            "expression": expression_name
        }
        
        print(f"发送表情请求: {json.dumps(data, indent=2)}")
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"表情控制成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"表情控制失败 - 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"表情控制异常: {e}")
        return False

def test_webapi_status():
    """测试WebAPI状态"""
    try:
        url = "http://127.0.0.1:8888/api/status"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"WebAPI状态: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"WebAPI状态检查失败 - 状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"WebAPI状态检查异常: {e}")
        return False

def main():
    """主测试函数"""
    print("=== Live2D WebAPI 控制测试 ===")
    
    # 1. 测试WebAPI状态
    print("\n1. 测试WebAPI状态...")
    if not test_webapi_status():
        print("WebAPI服务未启动，请先启动UI.py")
        return
    
    # 2. 测试动作控制
    print("\n2. 测试动作控制...")
    for i in range(3):
        print(f"\n测试动作 {i}:")
        test_live2d_motion(i)
        time.sleep(2)
    
    # 3. 测试表情控制
    print("\n3. 测试表情控制...")
    expressions = ["happy", "sad", "angry", "surprised", "normal"]
    for expr in expressions:
        print(f"\n测试表情 {expr}:")
        test_live2d_expression(expr)
        time.sleep(2)
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
