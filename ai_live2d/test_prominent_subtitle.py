"""
醒目的字幕显示测试 - 放在屏幕中央，使用醒目样式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import json

def prominent_subtitle_test():
    """醒目的字幕显示测试"""
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 创建字幕窗口
    subtitle_window = QWidget()
    subtitle_window.setWindowTitle("醒目字幕测试")
    
    # 设置窗口属性：无边框、置顶
    subtitle_window.setWindowFlags(
        Qt.WindowStaysOnTopHint | 
        Qt.FramelessWindowHint | 
        Qt.Tool
    )
    
    # 创建标签显示文本
    label = QLabel("🚨 这是醒目的测试字幕 🚨\n如果您看到这个，说明字幕显示正常！", subtitle_window)
    
    # 设置大字体
    font = QFont('Microsoft YaHei')
    font.setPointSize(32)  # 更大的字体
    font.setBold(True)
    label.setFont(font)
    
    # 设置醒目的样式：红色背景，白色文字，黄色边框
    label.setStyleSheet("""
        QLabel {
            color: white;
            background-color: rgb(255, 0, 0);
            border: 5px solid rgb(255, 255, 0);
            border-radius: 15px;
            padding: 30px;
            text-align: center;
        }
    """)
    
    # 居中对齐文本
    label.setAlignment(Qt.AlignCenter)
    
    # 调整窗口大小以适应文本
    label.adjustSize()
    subtitle_window.resize(label.size())
    
    # 获取屏幕信息并居中显示
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()
    
    x = (screen_geometry.width() - subtitle_window.width()) // 2
    y = (screen_geometry.height() - subtitle_window.height()) // 2
    
    print(f"屏幕信息: {screen_geometry.width()}x{screen_geometry.height()}")
    print(f"窗口大小: {subtitle_window.width()}x{subtitle_window.height()}")
    print(f"计算的中央位置: ({x}, {y})")
    
    # 设置窗口位置
    subtitle_window.move(x, y)
    
    # 显示窗口
    subtitle_window.show()
    subtitle_window.raise_()
    subtitle_window.activateWindow()
    
    print(f"窗口实际位置: ({subtitle_window.x()}, {subtitle_window.y()})")
    print(f"窗口可见性: {subtitle_window.isVisible()}")
    
    # 10秒后自动关闭
    QTimer.singleShot(10000, app.quit)
    
    print("\n🚨 窗口将在屏幕中央显示10秒钟，使用红色背景和黄色边框！")
    print("如果您还是看不到，可能是显示器配置或其他系统问题。")
    
    # 运行应用
    app.exec_()

if __name__ == "__main__":
    print("=== 醒目字幕显示测试 ===")
    try:
        prominent_subtitle_test()
        print("测试完成")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
