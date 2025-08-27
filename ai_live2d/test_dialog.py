#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试退出窗口的新样式
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from qfluentwidgets import MessageBox

class TestDialog:
    def __init__(self):
        self.app = QApplication(sys.argv)
        
    def test_exit_dialog(self):
        """测试新的退出对话框样式"""
        w = MessageBox(
            '是否退出程序？',
            '你真的要离开肥牛了吗？\n\n点击"确定"直接退出，点击"取消"将最小化到托盘~',
            None
        )
        w.yesButton.setText('直接退出')
        w.cancelButton.setText('最小化到托盘')
        
        result = w.exec()
        print(f"用户选择: {'直接退出' if result else '最小化到托盘'}")
        
    def test_intro_dialog(self):
        """测试项目介绍对话框样式"""
        w = MessageBox(
            '欢迎使用肥牛菜单！！！',
            '如果你喜欢本项目的话记得在GitHub上点个⭐，你的支持就是我们最大的动力！',
            None
        )
        w.yesButton.setText('那必须的')
        w.cancelButton.setText('下次一定')
        
        result = w.exec()
        print(f"用户选择: {'那必须的' if result else '下次一定'}")
        
    def run_test(self):
        print("测试1: 项目介绍对话框")
        self.test_intro_dialog()
        
        print("\n测试2: 退出确认对话框")
        self.test_exit_dialog()

if __name__ == '__main__':
    test = TestDialog()
    test.run_test()
