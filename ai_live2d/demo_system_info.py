#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示系统信息功能的简单脚本
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_system_info():
    """演示系统信息功能"""
    print("=== AI Live2D 系统信息演示 ===\n")
    
    # 模拟UI.py中的系统信息获取函数
    from UI import Widget
    
    # 创建一个临时的Widget实例来测试系统信息获取
    widget = Widget("demo", 0)
    
    print("正在获取详细系统信息...\n")
    system_info = widget._get_detailed_system_info()
    
    print("=== 详细系统信息 ===")
    print(system_info)
    
    print("\n=== 日志收集系统信息 ===")
    log_system_info = widget._collect_system_info()
    print(log_system_info)

if __name__ == "__main__":
    try:
        demo_system_info()
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
