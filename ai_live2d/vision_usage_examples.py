#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Live2D 视觉模型使用示例
演示如何通过代码调用视觉识别功能
"""

import requests
import json
import base64
from pathlib import Path

class VisionAPI:
    """视觉API客户端"""
    
    def __init__(self, base_url="http://127.0.0.1:8888", api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.chat_endpoint = f"{self.base_url}/chat"
    
    def chat_with_image(self, message, image_path=None, image_data=None):
        """
        发送包含图片的聊天请求
        
        Args:
            message: 文本消息
            image_path: 图片文件路径（与image_data二选一）
            image_data: base64编码的图片数据（与image_path二选一）
        
        Returns:
            响应文本或错误信息
        """
        try:
            # 准备图片数据
            if image_path and not image_data:
                image_data = self._encode_image(image_path)
            
            # 构建请求数据
            request_data = {
                "message": message
            }
            
            if image_data:
                request_data["image_data"] = image_data
            
            if self.api_key:
                request_data["api_key"] = self.api_key
            
            # 发送请求
            response = requests.post(
                self.chat_endpoint, 
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '未获取到响应')
            else:
                return f"请求失败: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"请求异常: {str(e)}"
    
    def _encode_image(self, image_path):
        """将图片文件编码为base64"""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            raise Exception(f"图片编码失败: {e}")

def example_1_basic_chat():
    """示例1: 基础聊天（无图片）"""
    print("=== 示例1: 基础聊天 ===")
    
    api = VisionAPI()
    response = api.chat_with_image("你好，请介绍一下你自己")
    
    print(f"用户: 你好，请介绍一下你自己")
    print(f"AI: {response}")
    print()

def example_2_image_description():
    """示例2: 图片描述"""
    print("=== 示例2: 图片描述 ===")
    
    # 创建一个测试图片（如果不存在）
    test_image_path = create_test_image_file()
    
    if not test_image_path:
        print("无法创建测试图片，跳过此示例")
        return
    
    api = VisionAPI()
    response = api.chat_with_image(
        "请详细描述这张图片的内容", 
        image_path=test_image_path
    )
    
    print(f"用户: [上传图片] 请详细描述这张图片的内容")
    print(f"AI: {response}")
    print()

def example_3_image_analysis():
    """示例3: 图片分析"""
    print("=== 示例3: 图片分析 ===")
    
    # 如果有真实的图片文件，可以这样使用
    # 这里我们创建一个简单的示例
    
    api = VisionAPI()
    
    # 模拟一个简单的图片数据
    simple_image_data = create_simple_image_base64()
    
    if simple_image_data:
        response = api.chat_with_image(
            "这张图片中有什么颜色？请分析图片的主要特征。",
            image_data=simple_image_data
        )
        
        print(f"用户: [上传图片] 这张图片中有什么颜色？请分析图片的主要特征。")
        print(f"AI: {response}")
    else:
        print("无法创建示例图片数据")
    
    print()

def example_4_batch_processing():
    """示例4: 批量处理（模拟）"""
    print("=== 示例4: 批量处理 ===")
    
    api = VisionAPI()
    
    # 模拟多个问题
    questions = [
        "这张图片的主要内容是什么？",
        "图片中有多少个对象？",
        "请识别图片中的文字内容"
    ]
    
    test_image_data = create_simple_image_base64()
    
    if test_image_data:
        for i, question in enumerate(questions, 1):
            print(f"问题 {i}: {question}")
            response = api.chat_with_image(question, image_data=test_image_data)
            print(f"回答 {i}: {response[:100]}...")
            print()
    else:
        print("无法创建示例图片数据")

def create_test_image_file():
    """创建一个测试图片文件"""
    try:
        import tempfile
        
        # 创建一个简单的测试图片
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00,
            0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
            0xE2, 0x21, 0xBC, 0x33, 0x00, 0x00, 0x00, 0x00,
            0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_file.write(png_data)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        print(f"创建测试图片文件失败: {e}")
        return None

def create_simple_image_base64():
    """创建简单的图片base64数据"""
    try:
        # 1x1像素的红色PNG图片
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00,
            0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
            0xE2, 0x21, 0xBC, 0x33, 0x00, 0x00, 0x00, 0x00,
            0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        return base64.b64encode(png_data).decode('utf-8')
        
    except Exception as e:
        print(f"创建简单图片数据失败: {e}")
        return None

def main():
    """主函数"""
    print("AI Live2D 视觉模型使用示例\n")
    print("注意: 在运行示例前，请确保：")
    print("1. AI Live2D UI程序正在运行")
    print("2. 已在UI中启用并配置视觉模型")
    print("3. WebAPI服务正常工作")
    print()
    
    # 运行示例
    example_1_basic_chat()
    example_2_image_description()
    example_3_image_analysis()
    example_4_batch_processing()
    
    print("=== 高级用法提示 ===")
    print("1. 使用真实图片:")
    print("   api = VisionAPI()")
    print("   response = api.chat_with_image('描述图片', image_path='your_image.jpg')")
    print()
    print("2. 配置API Key:")
    print("   api = VisionAPI(api_key='your-api-key')")
    print()
    print("3. 自定义提示词:")
    print("   response = api.chat_with_image('请识别图片中的所有文字并保持格式')")
    print()

if __name__ == "__main__":
    main()
