#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动作按钮功能测试脚本
测试新添加的动作按钮功能
"""

import json
import os
import sys

def test_action_buttons_config():
    """测试动作按钮配置"""
    print("=" * 60)
    print("🧪 动作按钮功能测试")
    print("=" * 60)

    # 检查配置文件
    config_path = "config.json"
    if not os.path.exists(config_path):
        print("❌ 配置文件不存在")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("✅ 配置文件加载成功")

        # 检查动作按钮开关
        action_buttons_enabled = config.get('setting', {}).get('action_buttons_enabled', True)
        print(f"📋 动作按钮开关: {'启用' if action_buttons_enabled else '禁用'}")

        # 检查动作绑定配置
        action_config = config.get('action_buttons', {})
        print("📋 动作绑定配置:")
        for i in [1, 2]:
            action_name = action_config.get(f'action_{i}', '未绑定')
            print(f"   动作{i}: {action_name}")

        # 检查WebAPI打断功能
        webapi_config = config.get('webapi', {})
        webapi_enabled = webapi_config.get('enabled', False)
        print(f"📋 WebAPI功能: {'启用' if webapi_enabled else '禁用'}")

        if webapi_enabled:
            port = webapi_config.get('port', 8888)
            host = webapi_config.get('host', '127.0.0.1')
            print(f"   WebAPI地址: http://{host}:{port}")
            print("   可用端点:")
            print("   - POST /api/chat (聊天)")
            print("   - POST /api/interrupt (打断)")

        print("\n" + "=" * 60)
        print("🎉 配置检查完成")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False

def create_sample_action_config():
    """创建示例动作配置"""
    print("\n📝 创建示例动作配置...")

    config_path = "config.json"
    if not os.path.exists(config_path):
        print("❌ 配置文件不存在，无法创建示例配置")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 启用动作按钮
        config.setdefault('setting', {})['action_buttons_enabled'] = True

        # 设置示例动作绑定
        action_config = config.setdefault('action_buttons', {})
        action_config['action_1'] = 'Idle'  # 动作一绑定到Idle
        action_config['action_2'] = 'Tap'   # 动作二绑定到Tap

        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print("✅ 示例配置创建成功")
        print("   动作一: Idle")
        print("   动作二: Tap")

        return True

    except Exception as e:
        print(f"❌ 创建示例配置失败: {e}")
        return False

def main():
    """主函数"""
    print("动作按钮功能测试工具")
    print("=" * 40)

    # 测试配置
    if not test_action_buttons_config():
        print("❌ 配置测试失败")
        return

    # 询问是否创建示例配置
    response = input("\n是否创建示例动作配置? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        create_sample_action_config()

    print("\n📖 使用说明:")
    print("1. 在UI的'设置'标签页中启用'动作按钮开关'")
    print("2. 在UI的'Live2D'标签页中设置动作一和动作二的绑定")
    print("3. 在UI的'动画操控'标签页中使用新添加的动作按钮")
    print("4. 或者通过WebAPI的 /api/interrupt 端点进行打断操作")

    print("\n🔗 WebAPI使用示例:")
    print("POST http://127.0.0.1:8888/api/interrupt")
    print('Content-Type: application/json')
    print('{"api_key": "your_key"}  # 如果设置了API密钥')

if __name__ == "__main__":
    main()
