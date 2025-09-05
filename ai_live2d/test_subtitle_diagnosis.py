"""
详细的字幕显示诊断测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QDesktopWidget
from PyQt5.QtCore import QTimer
from interface.subtitle_manager import SubtitleManager
import json

def diagnose_subtitle_display():
    """诊断字幕显示问题"""
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 加载配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("=== 系统诊断 ===")
    
    # 检查显示器信息
    desktop = QDesktopWidget()
    screen_count = desktop.screenCount()
    print(f"检测到 {screen_count} 个显示器")
    
    for i in range(screen_count):
        geometry = desktop.screenGeometry(i)
        print(f"  显示器 {i}: {geometry.width()}x{geometry.height()} 位置({geometry.x()}, {geometry.y()})")
        if i == desktop.primaryScreen():
            print(f"    ^ 主显示器")
    
    print("\n=== 字幕配置 ===")
    subtitle_config = config.get('subtitle', {})
    monitor_index = subtitle_config.get('display_monitor', 0)
    position_x = subtitle_config.get('position_x', 0)
    position_y = subtitle_config.get('position_y', 0)
    offset_x = subtitle_config.get('display_offset_x', 0)
    offset_y = subtitle_config.get('display_offset_y', 0)
    
    print(f"配置的显示器索引: {monitor_index}")
    print(f"配置的坐标: ({position_x}, {position_y})")
    print(f"配置的偏移: ({offset_x}, {offset_y})")
    
    # 验证显示器配置
    if monitor_index >= screen_count:
        print(f"⚠️ 警告: 配置的显示器索引 {monitor_index} 超出范围，将使用主显示器")
    else:
        target_geometry = desktop.screenGeometry(monitor_index)
        final_x = target_geometry.x() + position_x + offset_x
        final_y = target_geometry.y() + position_y + offset_y
        print(f"计算的最终坐标: ({final_x}, {final_y})")
        
        # 检查坐标是否在屏幕范围内
        if (final_x < target_geometry.x() or 
            final_x > target_geometry.x() + target_geometry.width() or
            final_y < target_geometry.y() or 
            final_y > target_geometry.y() + target_geometry.height()):
            print(f"⚠️ 警告: 计算的坐标 ({final_x}, {final_y}) 超出显示器范围")
    
    print("\n=== 创建字幕管理器 ===")
    subtitle_manager = SubtitleManager(parent=None, config=config)
    
    print("字幕管理器创建成功")
    print(f"窗口大小: {subtitle_manager.width()}x{subtitle_manager.height()}")
    print(f"窗口位置: ({subtitle_manager.x()}, {subtitle_manager.y()})")
    print(f"窗口可见性: {subtitle_manager.isVisible()}")
    
    print("\n=== 测试字幕显示 ===")
    test_message = "🎯 这是诊断测试字幕 - 如果您看到这条消息，说明字幕显示正常"
    
    # 显示字幕
    print(f"发送字幕文本: {test_message}")
    subtitle_manager.add_text(test_message)
    
    # 等待一秒让动画完成
    QTimer.singleShot(1000, lambda: print_window_status(subtitle_manager))
    
    def print_window_status(manager):
        print(f"\n显示后状态:")
        print(f"窗口大小: {manager.width()}x{manager.height()}")
        print(f"窗口位置: ({manager.x()}, {manager.y()})")
        print(f"窗口可见性: {manager.isVisible()}")
        print(f"is_visible标志: {manager.is_visible}")
        print(f"目标透明度: {manager.target_opacity}")
        print(f"显示文本: '{manager.display_text}'")
        
        # 尝试强制显示窗口
        print("\n=== 强制显示窗口 ===")
        manager.show()
        manager.raise_()
        manager.activateWindow()
        print("已调用 show(), raise_(), activateWindow()")
        
        # 再等待一会
        QTimer.singleShot(2000, lambda: final_check(manager))
    
    def final_check(manager):
        print(f"\n最终检查:")
        print(f"窗口可见性: {manager.isVisible()}")
        print(f"窗口位置: ({manager.x()}, {manager.y()})")
        
        print("\n请检查您的屏幕上是否有字幕显示")
        print("如果没有看到字幕，可能的原因:")
        print("1. 字幕位置超出屏幕范围")
        print("2. 字幕被其他窗口遮挡") 
        print("3. 字幕透明度或颜色问题")
        print("4. 字幕在错误的显示器上")
        
        input("\n按Enter键继续...")
        
        # 清除字幕
        manager.clear_text()
        print("测试完成")
        app.quit()
    
    # 启动应用
    app.exec_()

if __name__ == "__main__":
    print("=== 字幕显示诊断程序 ===")
    try:
        diagnose_subtitle_display()
    except Exception as e:
        print(f"诊断失败: {e}")
        import traceback
        traceback.print_exc()
