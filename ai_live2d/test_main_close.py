#!/usr/bin/env python3
"""
测试主窗口关闭时动作按钮悬浮窗口的关闭功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QEvent
from PyQt5.QtGui import QCloseEvent
from UI import Window

def test_close_event():
    """测试主窗口关闭事件"""
    app = QApplication(sys.argv)
    window = Window()

    def simulate_close():
        print("模拟关闭主窗口...")

        # 手动设置动作按钮窗口为可见状态（模拟正常使用状态）
        if hasattr(window, 'actionButtonsWindow') and window.actionButtonsWindow:
            window.actionButtonsWindow.show()
            print("动作按钮悬浮窗口已设置为可见状态")

        # 创建一个关闭事件
        close_event = QCloseEvent()
        # 调用 closeEvent 方法
        window.closeEvent(close_event)
        print(f"关闭事件被接受: {close_event.isAccepted()}")

        # 检查动作按钮窗口状态
        if hasattr(window, 'actionButtonsWindow') and window.actionButtonsWindow:
            if window.actionButtonsWindow.isVisible():
                print("❌ 动作按钮悬浮窗口仍然可见")
            else:
                print("✅ 动作按钮悬浮窗口已被隐藏")
        else:
            print("❌ 动作按钮悬浮窗口不存在")

        # 退出应用
        app.quit()

    # 显示窗口
    window.show()

    # 延迟2秒后模拟关闭
    QTimer.singleShot(2000, simulate_close)

    print("窗口已显示，2秒后将模拟关闭操作...")
    app.exec_()

if __name__ == "__main__":
    test_close_event()
