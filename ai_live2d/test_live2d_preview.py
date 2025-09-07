#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live2D预览功能测试
测试新添加的Live2D模型预览窗口功能
"""

import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QLabel
from PyQt5.QtCore import Qt

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from UI import Live2DPreviewWindow

class TestMainWindow(QMainWindow):
    """测试主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("Live2D预览功能测试")
        self.setGeometry(100, 100, 400, 200)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 说明标签
        info_label = QLabel("Live2D预览功能测试")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(info_label)
        
        # 选择模型按钮
        self.select_btn = QPushButton("📁 选择Live2D模型文件")
        self.select_btn.clicked.connect(self.select_model_file)
        layout.addWidget(self.select_btn)
        
        # 模型路径显示
        self.model_path_label = QLabel("未选择模型文件")
        self.model_path_label.setStyleSheet("color: #7f8c8d; padding: 5px; border: 1px solid #bdc3c7; border-radius: 3px;")
        layout.addWidget(self.model_path_label)
        
        # 预览按钮
        self.preview_btn = QPushButton("🎭 打开Live2D预览")
        self.preview_btn.clicked.connect(self.open_preview)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        layout.addWidget(self.preview_btn)
        
        # 测试示例按钮
        test_btn = QPushButton("🧪 使用示例模型测试")
        test_btn.clicked.connect(self.test_with_example)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        layout.addWidget(test_btn)
        
        self.current_model_path = None
    
    def select_model_file(self):
        """选择模型文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Live2D模型文件",
            "",
            "Live2D模型文件 (*.model3.json);;所有文件 (*.*)"
        )
        
        if file_path:
            self.current_model_path = file_path
            self.model_path_label.setText(f"已选择: {os.path.basename(file_path)}")
            self.model_path_label.setToolTip(file_path)
            self.preview_btn.setEnabled(True)
    
    def test_with_example(self):
        """使用示例模型测试"""
        # 创建一个示例model3.json文件用于测试
        example_data = {
            "Version": 3,
            "FileReferences": {
                "Moc": "example.moc3",
                "Textures": ["texture_00.png", "texture_01.png"],
                "Expressions": [
                    {"Name": "happy", "File": "expressions/happy.exp3.json"},
                    {"Name": "sad", "File": "expressions/sad.exp3.json"},
                    {"Name": "angry", "File": "expressions/angry.exp3.json"}
                ],
                "Motions": {
                    "Idle": [
                        {"File": "motions/idle_01.motion3.json"},
                        {"File": "motions/idle_02.motion3.json"}
                    ],
                    "TapHead": [
                        {"File": "motions/tap_head.motion3.json"}
                    ]
                }
            },
            "Layout": {
                "CenterX": 0.0,
                "CenterY": 0.0,
                "Width": 2.0,
                "Height": 2.0
            }
        }
        
        # 保存示例文件
        example_path = "test_example_model.model3.json"
        try:
            with open(example_path, 'w', encoding='utf-8') as f:
                json.dump(example_data, f, indent=2, ensure_ascii=False)
            
            self.current_model_path = os.path.abspath(example_path)
            self.model_path_label.setText(f"测试示例: {os.path.basename(example_path)}")
            self.model_path_label.setToolTip(f"示例模型文件: {self.current_model_path}")
            self.preview_btn.setEnabled(True)
            
            print(f"✅ 创建示例模型文件: {self.current_model_path}")
            
        except Exception as e:
            print(f"❌ 创建示例模型失败: {e}")
    
    def open_preview(self):
        """打开预览窗口"""
        if self.current_model_path and os.path.exists(self.current_model_path):
            try:
                print(f"🎭 打开预览窗口: {self.current_model_path}")
                preview_window = Live2DPreviewWindow(self.current_model_path, self)
                preview_window.exec_()
            except Exception as e:
                print(f"❌ 预览窗口错误: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ 模型文件不存在或未选择")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("Live2D预览测试")
    app.setApplicationVersion("1.0")
    
    # 创建并显示测试窗口
    window = TestMainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
