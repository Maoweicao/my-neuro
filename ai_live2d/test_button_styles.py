#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试QFluentWidgets按钮样式
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from qfluentwidgets import FluentIcon as FIF, PrimaryToolButton, ToolButton, PushButton
    from qfluentwidgets import setTheme, Theme
except ImportError as e:
    print(f"导入qfluentwidgets失败: {e}")
    sys.exit(1)

class ButtonTestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QFluentWidgets按钮样式测试")
        self.setGeometry(300, 300, 500, 300)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("日志管理按钮样式对比")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # 原始样式（PushButton）
        old_layout = QHBoxLayout()
        old_label = QLabel("原始样式:")
        old_layout.addWidget(old_label)
        
        old_save_btn = PushButton("保存日志包")
        old_save_btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }")
        old_clear_btn = PushButton("清空日志")
        old_clear_btn.setStyleSheet("QPushButton { background-color: #d83b01; color: white; }")
        old_view_btn = PushButton("查看日志目录")
        
        old_layout.addWidget(old_save_btn)
        old_layout.addWidget(old_clear_btn)
        old_layout.addWidget(old_view_btn)
        layout.addLayout(old_layout)
        
        # 新样式（QFluentWidgets）
        new_layout = QHBoxLayout()
        new_label = QLabel("新样式:")
        new_layout.addWidget(new_label)
        
        new_save_btn = PrimaryToolButton(FIF.SAVE)
        new_save_btn.setText("保存日志包")
        new_save_btn.setToolTip("将所有日志文件和系统信息打包保存为ZIP文件")
        
        new_clear_btn = ToolButton(FIF.DELETE)
        new_clear_btn.setText("清空日志")
        new_clear_btn.setToolTip("清空所有日志文件的内容，释放磁盘空间")
        
        new_view_btn = ToolButton(FIF.FOLDER)
        new_view_btn.setText("查看日志目录")
        new_view_btn.setToolTip("在文件管理器中打开logs文件夹")
        
        new_layout.addWidget(new_save_btn)
        new_layout.addWidget(new_clear_btn)
        new_layout.addWidget(new_view_btn)
        layout.addLayout(new_layout)
        
        # 系统信息刷新按钮对比
        refresh_layout = QHBoxLayout()
        refresh_label = QLabel("刷新按钮:")
        refresh_layout.addWidget(refresh_label)
        
        old_refresh_btn = PushButton("刷新系统信息")
        new_refresh_btn = ToolButton(FIF.SYNC)
        new_refresh_btn.setText("刷新系统信息")
        new_refresh_btn.setToolTip("重新获取并更新系统硬件信息")
        
        refresh_layout.addWidget(old_refresh_btn)
        refresh_layout.addWidget(new_refresh_btn)
        layout.addLayout(refresh_layout)
        
        # 说明
        info_label = QLabel(
            "新样式特点:\n"
            "• 使用Fluent Design图标\n"
            "• PrimaryToolButton用于主要操作（保存）\n"
            "• ToolButton用于辅助操作\n"
            "• 添加了详细的工具提示\n"
            "• 更加现代化和直观"
        )
        info_label.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 设置主题
        setTheme(Theme.LIGHT)

def main():
    app = QApplication(sys.argv)
    widget = ButtonTestWidget()
    widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
