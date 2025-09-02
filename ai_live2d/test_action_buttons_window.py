#!/usr/bin/env python3
"""
测试动作按钮悬浮窗口
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from interface.action_buttons import ActionButtonsWindow

def test_action_buttons():
    """测试动作按钮悬浮窗口"""
    app = QApplication(sys.argv)

    # 创建测试配置
    config = {
        "action_buttons": {
            "width": 300,
            "height": 80,
            "bg_color_r": 30,
            "bg_color_g": 31,
            "bg_color_b": 34,
            "bg_color_a": 220,
            "text_color_r": 220,
            "text_color_g": 220,
            "text_color_b": 220,
            "border_color_r": 86,
            "border_color_g": 182,
            "border_color_b": 194,
            "border_radius": 10,
            "font_family": "Microsoft YaHei",
            "font_size": 12
        }
    }

    # 创建悬浮窗口
    window = ActionButtonsWindow(config)

    # 显示窗口
    window.show()

    print("动作按钮悬浮窗口已创建并显示")
    print("按Ctrl键进入拖动模式，按Alt键进入穿透模式")

    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_action_buttons()
