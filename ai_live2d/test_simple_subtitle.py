"""
简单的字幕显示测试 - 测试字幕显示在屏幕中央
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette
import json

def simple_subtitle_test():
    """简单的字幕显示测试"""
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 读取配置中的字幕设置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    subtitle_config = config.get('subtitle', {})
    
    # 创建简单的字幕窗口
    subtitle_window = QWidget()
    subtitle_window.setWindowTitle("字幕测试")
    
    # 设置窗口属性：无边框、置顶、透明背景
    subtitle_window.setWindowFlags(
        Qt.WindowStaysOnTopHint | 
        Qt.FramelessWindowHint | 
        Qt.Tool |
        Qt.WindowTransparentForInput
    )
    subtitle_window.setAttribute(Qt.WA_TranslucentBackground)
    
    # 创建标签显示文本
    label = QLabel("🎯 这是测试字幕 - 如果您看到这个，说明字幕显示正常！", subtitle_window)
    
    # 设置字体和样式
    font = QFont(subtitle_config.get('font_family', 'Microsoft YaHei'))
    font.setPointSize(subtitle_config.get('font_size', 24))
    font.setBold(subtitle_config.get('font_bold', True))
    label.setFont(font)
    
    # 设置样式：白色文字，黑色边框，半透明背景
    label.setStyleSheet("""
        QLabel {
            color: rgb(255, 255, 255);
            background-color: rgba(0, 0, 0, 120);
            border: 2px solid rgb(255, 215, 0);
            border-radius: 10px;
            padding: 15px;
        }
    """)
    
    # 调整窗口大小以适应文本
    label.adjustSize()
    subtitle_window.resize(label.size())
    
    # 获取屏幕信息
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()
    
    print(f"屏幕信息: {screen_geometry.width()}x{screen_geometry.height()}")
    
    # 从配置读取位置信息
    position_x = subtitle_config.get('position_x', 0)
    position_y = subtitle_config.get('position_y', 0)
    offset_x = subtitle_config.get('display_offset_x', 0)
    offset_y = subtitle_config.get('display_offset_y', 0)
    
    # 如果配置的坐标为0，则使用屏幕中央
    if position_x == 0 and position_y == 0:
        # 居中显示
        x = (screen_geometry.width() - subtitle_window.width()) // 2
        y = (screen_geometry.height() - subtitle_window.height()) // 2
        print(f"使用屏幕中央位置: ({x}, {y})")
    else:
        # 使用配置的位置
        x = position_x + offset_x
        y = position_y + offset_y
        print(f"使用配置位置: 基础({position_x}, {position_y}) + 偏移({offset_x}, {offset_y}) = 最终({x}, {y})")
    
    # 设置窗口位置
    subtitle_window.move(x, y)
    
    # 显示窗口
    subtitle_window.show()
    subtitle_window.raise_()
    subtitle_window.activateWindow()
    
    print(f"窗口已显示在位置: ({subtitle_window.x()}, {subtitle_window.y()})")
    print(f"窗口大小: {subtitle_window.width()}x{subtitle_window.height()}")
    print(f"窗口可见性: {subtitle_window.isVisible()}")
    
    # 5秒后自动关闭
    QTimer.singleShot(5000, app.quit)
    
    print("\n窗口将显示5秒钟...")
    print("请检查您的屏幕上是否有字幕显示！")
    
    # 运行应用
    app.exec_()

if __name__ == "__main__":
    print("=== 简单字幕显示测试 ===")
    try:
        simple_subtitle_test()
        print("测试完成")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
