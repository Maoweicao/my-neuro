#!/usr/bin/env python3
"""
豆包TTS配置更新脚本
"""

import json
import os
import sys

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

def save_config(config):
    """保存配置文件"""
    config_path = "config.json"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print("✅ 配置文件已保存")
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False

def update_doubao_config():
    """更新豆包TTS配置"""
    print("🔧 豆包TTS配置更新工具")
    print("=" * 50)

    config = load_config()
    if not config:
        return False

    # 显示当前配置
    tts_config = config.get('tts', {})
    current_app_id = tts_config.get('doubao_app_id', '')
    current_token = tts_config.get('doubao_access_token', '')

    print("📋 当前豆包TTS配置:")
    print(f"   APP ID: {current_app_id}")
    print(f"   Access Token: {current_token[:20]}..." if current_token else "   Access Token: 未设置")

    print("\n🔑 请输入新的豆包TTS配置:")

    # 获取新的APP ID
    new_app_id = input(f"   APP ID [{current_app_id}]: ").strip()
    if not new_app_id:
        new_app_id = current_app_id

    # 获取新的Access Token
    new_token = input("   Access Token: ").strip()
    if not new_token and current_token:
        use_current = input("   使用当前Access Token? (y/n): ").strip().lower()
        if use_current == 'y':
            new_token = current_token

    if not new_app_id or not new_token:
        print("❌ APP ID和Access Token都不能为空")
        return False

    # 更新配置
    if 'tts' not in config:
        config['tts'] = {}

    config['tts']['doubao_app_id'] = new_app_id
    config['tts']['doubao_access_token'] = new_token

    # 保存配置
    if save_config(config):
        print("\n✅ 豆包TTS配置已更新！")
        print(f"   新APP ID: {new_app_id}")
        print(f"   新Access Token: {new_token[:20]}...")
        return True
    else:
        return False

def show_help():
    """显示帮助信息"""
    print("📖 豆包TTS配置帮助:")
    print("1. 访问豆包TTS控制台: https://console.volcengine.com/speech")
    print("2. 创建或选择应用，获取APP ID")
    print("3. 在应用设置中获取Access Token")
    print("4. 确保应用已开通TTS服务权限")
    print("5. 运行此脚本更新配置")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_help()
    else:
        success = update_doubao_config()
        if success:
            print("\n🎉 配置更新完成！现在可以运行测试脚本验证配置。")
            sys.exit(0)
        else:
            print("\n💥 配置更新失败！")
            sys.exit(1)
