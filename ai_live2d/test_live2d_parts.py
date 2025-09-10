#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Live2D部件透明度功能测试脚本
"""
import json
import os

def test_live2d_parts_config():
    """测试Live2D部件透明度配置功能"""
    print("=== Live2D部件透明度功能测试 ===\n")

    # 测试配置结构
    config_path = "config.json"

    # 读取现有配置
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✓ 成功读取配置文件")
    else:
        config = {}
        print("⚠ 配置文件不存在，将创建新配置")

    # 测试Live2D配置结构
    if 'live2d' not in config:
        config['live2d'] = {}
        print("✓ 创建Live2D配置节点")

    # 测试模型特定配置
    model_name = "test_model"
    if model_name not in config['live2d']:
        config['live2d'][model_name] = {}
        print(f"✓ 创建模型 {model_name} 的配置节点")

    # 测试部件透明度配置
    test_parts_opacity = {
        'body': 80,
        'head': 90,
        'face': 100,
        'eyes': 95,
        'mouth': 85,
        'hair': 75,
        'clothes': 70
    }

    config['live2d'][model_name]['parts_opacity'] = test_parts_opacity
    print(f"✓ 设置部件透明度: {test_parts_opacity}")

    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print("✓ 成功保存配置到config.json")

    # 验证配置
    with open(config_path, 'r', encoding='utf-8') as f:
        saved_config = json.load(f)

    saved_parts = saved_config.get('live2d', {}).get(model_name, {}).get('parts_opacity', {})
    if saved_parts == test_parts_opacity:
        print("✓ 配置验证成功：保存的透明度设置与预期一致")
    else:
        print("⚠ 配置验证失败：保存的设置与预期不一致")
        print(f"  预期: {test_parts_opacity}")
        print(f"  实际: {saved_parts}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_live2d_parts_config()
