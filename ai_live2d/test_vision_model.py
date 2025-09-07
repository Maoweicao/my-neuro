#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Live2D 视觉模型功能测试脚本
"""

import requests
import json
import base64
import sys
import os
from pathlib import Path

def test_vision_api():
    """测试视觉API功能"""
    
    # WebAPI配置
    base_url = "http://127.0.0.1:8888"
    chat_endpoint = f"{base_url}/chat"
    
    print("=== AI Live2D 视觉模型测试 ===\n")
    
    # 1. 测试基础聊天功能
    print("1. 测试基础聊天功能...")
    basic_test_data = {
        "message": "你好，请介绍一下你自己"
    }
    
    try:
        response = requests.post(chat_endpoint, json=basic_test_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 基础聊天测试成功")
            print(f"  响应: {result['response'][:100]}...")
        else:
            print(f"✗ 基础聊天测试失败: HTTP {response.status_code}")
            print(f"  错误: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 基础聊天测试异常: {e}")
        return False
    
    print()
    
    # 2. 测试视觉功能（需要用户提供图片）
    print("2. 测试视觉识别功能...")
    
    # 创建一个简单的测试图片（1x1像素的红色PNG）
    test_image_b64 = create_test_image()
    
    if not test_image_b64:
        print("⚠ 无法创建测试图片，跳过视觉测试")
        return True
    
    vision_test_data = {
        "message": "请描述这张图片的内容",
        "image_data": test_image_b64
    }
    
    try:
        print("  发送视觉识别请求...")
        response = requests.post(chat_endpoint, json=vision_test_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 视觉识别测试成功")
            print(f"  响应: {result['response'][:200]}...")
            
            # 检查响应是否包含视觉相关内容
            response_text = result['response'].lower()
            if any(keyword in response_text for keyword in ['图片', '图像', '看到', '识别', 'image', 'picture']):
                print("✓ 响应包含视觉相关内容，视觉功能可能正常工作")
            else:
                print("⚠ 响应未包含明显的视觉相关内容，请检查视觉模型配置")
                
        else:
            print(f"✗ 视觉识别测试失败: HTTP {response.status_code}")
            print(f"  错误: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 视觉识别测试异常: {e}")
        return False
    
    print()
    print("=== 测试完成 ===")
    return True

def create_test_image():
    """创建一个简单的测试图片"""
    try:
        # 创建一个1x1像素的红色PNG图片的base64数据
        # 这是一个最小的PNG图片数据
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR chunk size
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # width: 1
            0x00, 0x00, 0x00, 0x01,  # height: 1
            0x08, 0x02,              # bit depth: 8, color type: 2 (RGB)
            0x00, 0x00, 0x00,        # compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT chunk size
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,  # compressed data
            0xE2, 0x21, 0xBC, 0x33,  # CRC
            0x00, 0x00, 0x00, 0x00,  # IEND chunk size
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82   # CRC
        ])
        
        return base64.b64encode(png_data).decode('utf-8')
    except Exception as e:
        print(f"创建测试图片失败: {e}")
        return None

def check_config():
    """检查配置文件中的视觉模型配置"""
    print("=== 检查配置 ===\n")
    
    config_path = Path("config.json")
    if not config_path.exists():
        print("✗ 配置文件 config.json 不存在")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        vision_config = config.get('vision', {})
        
        print("视觉模型配置:")
        print(f"  启用状态: {vision_config.get('enabled', False)}")
        print(f"  API URL: {vision_config.get('api_url', '未配置')}")
        print(f"  API Key: {'已配置' if vision_config.get('api_key') else '未配置'}")
        print(f"  模型: {vision_config.get('model', '未配置')}")
        print(f"  仅回退模式: {vision_config.get('fallback_only', True)}")
        
        if not vision_config.get('enabled', False):
            print("\n⚠ 视觉模式未启用，请在UI中启用视觉模式")
            return False
        
        if not vision_config.get('api_url') or not vision_config.get('api_key'):
            print("\n⚠ 视觉模型配置不完整，请配置API URL和API Key")
            return False
        
        print("\n✓ 视觉模型配置看起来正常")
        return True
        
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        return False

def main():
    """主函数"""
    print("AI Live2D 视觉模型功能测试\n")
    
    # 检查配置
    config_ok = check_config()
    print()
    
    if not config_ok:
        print("配置检查失败，建议：")
        print("1. 在UI中打开'大语言模型'标签页")
        print("2. 在'视觉模型配置'部分启用视觉模式")
        print("3. 配置API URL、API Key和模型")
        print("4. 保存配置后重新运行测试")
        return
    
    # 运行API测试
    test_ok = test_vision_api()
    
    if test_ok:
        print("\n🎉 测试完成！视觉模型功能基本正常")
        print("\n使用建议：")
        print("1. 通过UI的'视觉功能测试'按钮测试真实图片")
        print("2. 通过WebAPI发送包含image_data的请求")
        print("3. 查看详细文档: VISION_MODEL_README.md")
    else:
        print("\n❌ 测试失败，请检查：")
        print("1. WebAPI服务是否正常运行")
        print("2. 视觉模型配置是否正确")
        print("3. 网络连接是否正常")
        print("4. API Key是否有效")

if __name__ == "__main__":
    main()
