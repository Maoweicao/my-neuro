#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的WebAPI服务器测试
"""

import requests
import time

def test_webapi_status():
    """测试WebAPI状态"""
    try:
        response = requests.get("http://127.0.0.1:8888/api/status", timeout=5)
        print(f"WebAPI状态: {response.status_code}")
        if response.status_code == 200:
            print(f"响应: {response.json()}")
            return True
        else:
            print(f"错误响应: {response.text}")
            return False
    except Exception as e:
        print(f"连接失败: {e}")
        return False

if __name__ == "__main__":
    print("测试WebAPI服务器状态...")
    if test_webapi_status():
        print("WebAPI服务器运行正常")
    else:
        print("WebAPI服务器未运行或有问题")
