#!/usr/bin/env python3
"""
测试interrupt按钮功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from UI import Window
from interface.action_buttons import ActionButtonsWindow

def test_interrupt_button():
    """测试interrupt按钮功能"""
    print("开始测试interrupt按钮功能...")

    # 创建应用程序
    app = QApplication(sys.argv)

    # 创建主窗口
    window = Window()

    # 检查Window是否有interrupt_current_operations方法
    if hasattr(window, 'interrupt_current_operations'):
        print("✓ Window类有interrupt_current_operations方法")
    else:
        print("✗ Window类缺少interrupt_current_operations方法")
        return False

    # 检查MainInterface是否有interrupt_current_operations方法
    if hasattr(window.MainInterface, 'interrupt_current_operations'):
        print("✓ MainInterface类有interrupt_current_operations方法")
    else:
        print("✗ MainInterface类缺少interrupt_current_operations方法")
        return False

    # 检查ActionButtonsWindow是否正确创建
    if hasattr(window, 'actionButtonsWindow') and window.actionButtonsWindow:
        print("✓ ActionButtonsWindow已创建")
    else:
        print("✗ ActionButtonsWindow未创建")
        return False

    # 检查ActionButtonsWindow是否有interrupt_current_operations方法
    if hasattr(window.actionButtonsWindow, 'interrupt_current_operations'):
        print("✓ ActionButtonsWindow有interrupt_current_operations方法")
    else:
        print("✗ ActionButtonsWindow缺少interrupt_current_operations方法")
        return False

    # 检查ActionButtonsWindow的main_window引用是否正确
    if window.actionButtonsWindow.main_window == window:
        print("✓ ActionButtonsWindow的main_window引用正确")
    else:
        print("✗ ActionButtonsWindow的main_window引用不正确")
        return False

    print("所有检查通过！interrupt按钮功能应该正常工作。")
    return True

if __name__ == "__main__":
    test_interrupt_button()
