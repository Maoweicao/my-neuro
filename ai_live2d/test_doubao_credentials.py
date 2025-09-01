#!/usr/bin/env python3
"""
豆包TTS凭据验证脚本
"""

import json
import requests
import sys
import os

def load_config():
    """加载配置文件"""
    config_path = "config.json"
    if not os.path.exists(config_path):
        print("❌ 配置文件不存在")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None

def validate_credentials():
    """验证豆包TTS凭据"""
    print("🔍 开始验证豆包TTS凭据...")

    config = load_config()
    if not config:
        return False

    tts_config = config.get('tts', {})
    app_id = tts_config.get('doubao_app_id', '')
    access_token = tts_config.get('doubao_access_token', '')

    if not app_id or not access_token:
        print("❌ APP ID或Access Token未配置")
        return False

    print(f"📋 APP ID: {app_id}")
    print(f"🔑 Access Token: {access_token[:20]}...")

    # 测试基本的认证请求
    url = "https://openspeech.bytedance.com/api/v1/tts"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "app": {
            "appid": app_id,
            "token": access_token,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "test_user"
        },
        "audio": {
            "voice_type": "清晰小雪",
            "encoding": "wav"
        },
        "request": {
            "reqid": "test_req_123",
            "text": "测试",
            "text_type": "plain",
            "operation": "query"
        }
    }

    try:
        print("📡 发送测试请求...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"📊 HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"📄 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

            if result.get('code') == 3000:
                print("✅ 凭据验证成功！")
                return True
            else:
                print(f"❌ API返回错误: {result.get('message', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            try:
                error_result = response.json()
                print(f"📄 错误详情: {json.dumps(error_result, ensure_ascii=False, indent=2)}")
            except:
                print(f"📄 错误详情: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

if __name__ == "__main__":
    success = validate_credentials()
    if success:
        print("\n🎉 豆包TTS凭据验证通过！")
        sys.exit(0)
    else:
        print("\n💥 豆包TTS凭据验证失败！")
        sys.exit(1)
