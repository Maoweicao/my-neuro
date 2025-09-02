#!/usr/bin/env python3
"""
测试动作按钮悬浮窗口关闭功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from UI import Window

def test_close_functionality():
    """测试关闭功能"""
    app = QApplication(sys.argv)
    window = Window()

    def test_close():
        print('测试关闭动作按钮悬浮窗口...')
        if hasattr(window, 'actionButtonsWindow'):
            print('✅ 动作按钮悬浮窗口存在')
            window.actionButtonsWindow.close()
            print('✅ 动作按钮悬浮窗口已关闭')
        else:
            print('❌ 动作按钮悬浮窗口不存在')

        # 测试close_bat_msg方法
        print('测试close_bat_msg方法...')
        window.close_bat_msg()
        print('✅ close_bat_msg方法执行完成')

        # 退出应用
        app.quit()

    # 显示窗口
    window.show()

    # 延迟2秒后测试关闭
    QTimer.singleShot(2000, test_close)

    print("窗口已显示，2秒后将测试关闭功能...")
    app.exec_()

if __name__ == "__main__":
    test_close_functionality()
