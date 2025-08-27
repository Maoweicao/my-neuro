#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试ColorDialog功能"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtGui import QColor
from qfluentwidgets import ColorDialog

class TestColorDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试ColorDialog")
        self.setGeometry(100, 100, 300, 200)
        
        layout = QVBoxLayout()
        
        # 测试按钮1：带透明度的ColorDialog
        btn1 = QPushButton("测试ColorDialog (带透明度)")
        btn1.clicked.connect(self.test_color_dialog_with_alpha)
        layout.addWidget(btn1)
        
        # 测试按钮2：不带透明度的ColorDialog
        btn2 = QPushButton("测试ColorDialog (不带透明度)")
        btn2.clicked.connect(self.test_color_dialog_without_alpha)
        layout.addWidget(btn2)
        
        self.setLayout(layout)
        
    def test_color_dialog_with_alpha(self):
        """测试带透明度的ColorDialog"""
        print("尝试打开带透明度的ColorDialog...")
        try:
            current_color = QColor(255, 0, 0, 128)  # 半透明红色
            color_dialog = ColorDialog(current_color, "选择颜色 (带透明度)", self, enableAlpha=True)
            
            def on_color_changed(color):
                print(f"颜色改变: R={color.red()}, G={color.green()}, B={color.blue()}, A={color.alpha()}")
            
            color_dialog.colorChanged.connect(on_color_changed)
            
            if color_dialog.exec():
                final_color = color_dialog.color
                print(f"最终颜色: R={final_color.red()}, G={final_color.green()}, B={final_color.blue()}, A={final_color.alpha()}")
            else:
                print("用户取消了颜色选择")
                
        except Exception as e:
            print(f"ColorDialog错误: {e}")
            import traceback
            traceback.print_exc()
    
    def test_color_dialog_without_alpha(self):
        """测试不带透明度的ColorDialog"""
        print("尝试打开不带透明度的ColorDialog...")
        try:
            current_color = QColor(0, 255, 0)  # 绿色
            color_dialog = ColorDialog(current_color, "选择颜色 (不带透明度)", self, enableAlpha=False)
            
            def on_color_changed(color):
                print(f"颜色改变: R={color.red()}, G={color.green()}, B={color.blue()}")
            
            color_dialog.colorChanged.connect(on_color_changed)
            
            if color_dialog.exec():
                final_color = color_dialog.color
                print(f"最终颜色: R={final_color.red()}, G={final_color.green()}, B={final_color.blue()}")
            else:
                print("用户取消了颜色选择")
                
        except Exception as e:
            print(f"ColorDialog错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestColorDialog()
    window.show()
    sys.exit(app.exec_())
