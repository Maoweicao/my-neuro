"""
简单的字幕显示测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from interface.subtitle_manager import SubtitleManager
import json

def test_subtitle_positioning():
    """测试字幕定位功能"""
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 加载配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("创建字幕管理器...")
    subtitle_manager = SubtitleManager(parent=None, config=config)
    
    print("当前字幕配置:")
    subtitle_config = config.get('subtitle', {})
    print(f"  显示器: {subtitle_config.get('display_monitor', 0)}")
    print(f"  位置: {subtitle_config.get('display_position', 'bottom')}")
    print(f"  X坐标: {subtitle_config.get('position_x', 0)}")
    print(f"  Y坐标: {subtitle_config.get('position_y', 0)}")
    print(f"  X偏移: {subtitle_config.get('display_offset_x', 0)}")
    print(f"  Y偏移: {subtitle_config.get('display_offset_y', 0)}")
    
    # 显示测试字幕
    test_message = "这是一条测试字幕，用于验证位置是否正确显示"
    print(f"\n显示测试字幕: {test_message}")
    
    subtitle_manager.add_text(test_message)
    
    # 等待用户确认
    input("\n请确认字幕是否显示在正确位置，然后按Enter继续...")
    
    # 测试位置更新功能
    print("测试位置更新功能...")
    print("将字幕移动到屏幕中央...")
    
    # 更新位置到中央
    subtitle_manager.update_display_settings(
        monitor_index=0,
        position='center',
        position_x=640,  # 假设屏幕宽度1920的中央
        position_y=540   # 假设屏幕高度1080的中央
    )
    
    input("请确认字幕是否移动到了屏幕中央，然后按Enter继续...")
    
    # 测试偏移功能
    print("测试偏移功能...")
    print("添加100像素的偏移...")
    
    subtitle_manager.update_display_settings(
        offset_x=100,
        offset_y=100
    )
    
    input("请确认字幕是否向右下方偏移了100像素，然后按Enter继续...")
    
    # 清除字幕
    subtitle_manager.clear_text()
    
    print("测试完成")

if __name__ == "__main__":
    print("=== 字幕定位功能测试 ===")
    try:
        test_subtitle_positioning()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
