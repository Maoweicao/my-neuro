# -*- coding: utf-8 -*-
"""
测试DropDownColorPicker颜色选择器组件
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

try:
    from UI import ColorPickerWidget
    
    def test_dropdown_color_picker():
        """测试基于DropDownColorPicker的颜色选择器组件"""
        app = QApplication(sys.argv)
        
        # 创建测试窗口
        window = QWidget()
        window.setWindowTitle('DropDownColorPicker测试')
        window.resize(700, 500)
        
        layout = QVBoxLayout(window)
        
        # 添加说明
        label = QLabel(
            '基于qfluentwidgets DropDownColorPicker的颜色选择器测试\n'
            '• 点击颜色下拉按钮选择颜色\n'
            '• 可直接修改RGB/RGBA数值\n'
            '• 支持透明度设置（RGBA模式）'
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # 测试RGBA颜色选择器（背景颜色）
        layout.addWidget(QLabel("背景颜色 (RGBA):"))
        rgba_picker1 = ColorPickerWidget(window, "背景颜色", has_alpha=True)
        rgba_picker1.set_color(40, 44, 52, 220)
        layout.addWidget(rgba_picker1)
        
        # 测试RGB颜色选择器（文字颜色）
        layout.addWidget(QLabel("文字颜色 (RGB):"))
        rgb_picker = ColorPickerWidget(window, "文字颜色", has_alpha=False)
        rgb_picker.set_color(220, 220, 220)
        layout.addWidget(rgb_picker)
        
        # 测试RGB颜色选择器（边框颜色）
        layout.addWidget(QLabel("边框颜色 (RGB):"))
        rgb_picker2 = ColorPickerWidget(window, "边框颜色", has_alpha=False)
        rgb_picker2.set_color(86, 182, 194)
        layout.addWidget(rgb_picker2)
        
        # 测试RGBA颜色选择器（输入框背景）
        layout.addWidget(QLabel("输入框背景 (RGBA):"))
        rgba_picker2 = ColorPickerWidget(window, "输入框背景", has_alpha=True)
        rgba_picker2.set_color(60, 60, 70, 220)
        layout.addWidget(rgba_picker2)
        
        layout.addStretch()
        
        def print_colors():
            print("\n=== 当前颜色值 ===")
            print(f"背景颜色 (RGBA): {rgba_picker1.get_rgba()}")
            print(f"文字颜色 (RGB): {rgb_picker.get_rgb()}")
            print(f"边框颜色 (RGB): {rgb_picker2.get_rgb()}")
            print(f"输入框背景 (RGBA): {rgba_picker2.get_rgba()}")
        
        # 定时打印颜色值
        from PyQt5.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(print_colors)
        timer.start(3000)  # 3秒
        
        window.show()
        print("DropDownColorPicker测试窗口已启动")
        print("使用qfluentwidgets的DropDownColorPicker组件")
        
        return app.exec_()

    if __name__ == '__main__':
        sys.exit(test_dropdown_color_picker())

except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装PyQt5和qfluentwidgets")
    print("可以运行: pip install PyQt5 qfluentwidgets")
except Exception as e:
    print(f"运行错误: {e}")
    import traceback
    traceback.print_exc()
