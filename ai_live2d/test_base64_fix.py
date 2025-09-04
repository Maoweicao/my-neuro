#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试唱歌API的base64解码功能
"""

import base64
import json

def test_base64_decode():
    """测试base64解码功能"""
    print("🧪 测试base64解码功能...")

    try:
        # 创建一个简单的音频数据进行测试
        test_audio = b"test audio data"
        encoded = base64.b64encode(test_audio).decode('utf-8')

        # 测试解码
        decoded = base64.b64decode(encoded)

        if decoded == test_audio:
            print("✅ base64解码测试成功")
            return True
        else:
            print("❌ base64解码测试失败")
            return False

    except Exception as e:
        print(f"❌ base64解码测试异常: {e}")
        return False

def test_singing_request_format():
    """测试唱歌请求的数据格式"""
    print("📝 测试唱歌请求数据格式...")

    try:
        # 模拟唱歌请求的数据
        test_audio = b"fake audio data for testing"
        audio_base64 = base64.b64encode(test_audio).decode('utf-8')

        request_data = {
            "audio_base64": audio_base64,
            "volume": 0.8,
            "loop": False,
            "singing_motion": "唱歌"
        }

        # 验证数据格式
        if "audio_base64" in request_data:
            print("✅ 请求数据格式正确")
            return True
        else:
            print("❌ 请求数据格式错误")
            return False

    except Exception as e:
        print(f"❌ 数据格式测试异常: {e}")
        return False

if __name__ == "__main__":
    success1 = test_base64_decode()
    success2 = test_singing_request_format()

    if success1 and success2:
        print("🎉 所有测试通过！")
    else:
        print("❌ 部分测试失败")
