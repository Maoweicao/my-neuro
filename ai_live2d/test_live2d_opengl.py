#!/usr/bin/env python3
# coding:utf-8

import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton
from UI import Live2DPreviewWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live2D OpenGL预览测试")
        self.setGeometry(100, 100, 600, 600)
        
        layout = QVBoxLayout(self)
        
        # 测试按钮
        test_btn = QPushButton("加载Live2D模型")
        test_btn.clicked.connect(self.load_model)
        layout.addWidget(test_btn)
        
        # Live2D预览组件
        model_path = r"f:\my-neuro\ai_live2d\models\2D\肥牛"
        self.preview_widget = Live2DPreviewWidget(model_path)
        layout.addWidget(self.preview_widget)
        
        # 控制按钮
        control_layout = QVBoxLayout()
        
        play_btn = QPushButton("播放动作")
        play_btn.clicked.connect(lambda: self.preview_widget.play_motion("TapBody"))
        control_layout.addWidget(play_btn)
        
        expression_btn = QPushButton("设置表情")
        expression_btn.clicked.connect(lambda: self.preview_widget.set_expression("happy"))
        control_layout.addWidget(expression_btn)
        
        stop_btn = QPushButton("停止动画")
        stop_btn.clicked.connect(self.preview_widget.stop_motion)
        control_layout.addWidget(stop_btn)
        
        layout.addLayout(control_layout)
    
    def load_model(self):
        model_path = r"f:\my-neuro\ai_live2d\models\2D\肥牛"
        self.preview_widget.load_model(model_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
