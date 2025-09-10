#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Live2DModel配置读取
"""

import json
import sys
import os

# 添加项目路径
sys.path.append('.')

def test_config_reading():
    """测试配置读取"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("=== 配置验证 ===")
        print("UI model_path:", repr(config.get('ui', {}).get('model_path', 'NOT FOUND')))
        print("Root model_path:", repr(config.get('model_path', 'NOT FOUND')))

        # 模拟Live2DModel的配置读取逻辑
        ui_model_path = config.get('ui', {}).get('model_path', '')
        root_model_path = config.get('model_path', '')

        print("\n=== Live2DModel读取逻辑 ===")
        print("修复后的读取 (ui.model_path):", repr(ui_model_path))
        print("修复前的读取 (root.model_path):", repr(root_model_path))

        # 检查文件是否存在
        if ui_model_path and os.path.exists(ui_model_path):
            print("✅ UI中设置的模型文件存在:", ui_model_path)
        elif ui_model_path:
            print("❌ UI中设置的模型文件不存在:", ui_model_path)
        else:
            print("⚠️ UI中未设置model_path")

        return True

    except Exception as e:
        print("❌ 测试失败:", e)
        return False

if __name__ == "__main__":
    test_config_reading()
