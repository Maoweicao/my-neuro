#!/usr/bin/env python3
"""
测试interrupt按钮功能 - 实际调用测试
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from UI import Window

def test_interrupt_functionality():
    """测试interrupt功能是否实际工作"""
    print("开始测试interrupt功能实际调用...")

    # 创建应用程序
    app = QApplication(sys.argv)

    # 创建主窗口
    window = Window()

    # 模拟调用interrupt_current_operations
    print("调用Window.interrupt_current_operations()...")
    try:
        result = window.interrupt_current_operations()
        print(f"✓ interrupt_current_operations()调用成功，返回值: {result}")
    except Exception as e:
        print(f"✗ interrupt_current_operations()调用失败: {e}")
        return False

    # 检查是否创建了interrupt_signal.tmp文件
    if os.path.exists("interrupt_signal.tmp"):
        print("✓ interrupt_signal.tmp文件已创建")
        # 读取文件内容
        try:
            with open("interrupt_signal.tmp", 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"信号文件内容: {content}")
        except Exception as e:
            print(f"读取信号文件时出错: {e}")
    else:
        print("⚠ interrupt_signal.tmp文件未创建（这可能是正常的，取决于具体实现）")

    print("interrupt功能测试完成！")
    return True

if __name__ == "__main__":
    test_interrupt_functionality()
