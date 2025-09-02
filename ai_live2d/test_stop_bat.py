#!/usr/bin/env python3
"""
测试stop_bat方法关闭动作按钮悬浮窗口的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from UI import Window

def test_stop_bat_close_action_buttons():
    """测试stop_bat方法关闭动作按钮悬浮窗口"""
    app = QApplication(sys.argv)
    window = Window()

    def test_stop_bat():
        print("测试stop_bat方法关闭动作按钮悬浮窗口...")

        # 确保动作按钮悬浮窗口是可见的
        if hasattr(window, 'actionButtonsWindow') and window.actionButtonsWindow:
            window.actionButtonsWindow.show()
            print("动作按钮悬浮窗口已设置为可见")

        # 调用主界面（MainInterface）的stop_bat方法
        if hasattr(window, 'MainInterface') and hasattr(window.MainInterface, 'stop_bat'):
            print("调用MainInterface的stop_bat方法...")
            window.MainInterface.stop_bat()
            print("stop_bat方法调用完成")

        # 检查动作按钮窗口状态
        if hasattr(window, 'actionButtonsWindow') and window.actionButtonsWindow:
            if window.actionButtonsWindow.isVisible():
                print("❌ 动作按钮悬浮窗口仍然可见")
            else:
                print("✅ 动作按钮悬浮窗口已被关闭")
        else:
            print("❌ 动作按钮悬浮窗口不存在")

        # 退出应用
        app.quit()

    # 显示窗口
    window.show()

    # 延迟2秒后测试
    QTimer.singleShot(2000, test_stop_bat)

    print("窗口已显示，2秒后将测试stop_bat方法...")
    app.exec_()

if __name__ == "__main__":
    test_stop_bat_close_action_buttons()
