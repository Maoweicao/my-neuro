#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试字幕位置计算功能
"""

def test_position_calculation():
    """测试新增位置的计算逻辑"""
    print("=== 测试字幕位置计算 ===")
    
    # 模拟屏幕尺寸
    class MockScreenRect:
        def __init__(self, x=0, y=0, width=1920, height=1080):
            self._x = x
            self._y = y
            self._width = width
            self._height = height
            
        def x(self):
            return self._x
            
        def y(self):
            return self._y
            
        def width(self):
            return self._width
            
        def height(self):
            return self._height
    
    def calculate_position(position, screen_rect):
        """计算字幕位置"""
        subtitle_width = 600
        subtitle_height = 100
        
        x, y = 0, 0
        
        if position == 'center':
            x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
            y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
        elif position == 'top':
            x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
            y = screen_rect.y() + 50
        elif position == 'bottom':
            x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
        elif position == 'left':
            x = screen_rect.x() + 50
            y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
        elif position == 'right':
            x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
            y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
        elif position == 'top_left':
            x = screen_rect.x() + 50
            y = screen_rect.y() + 50
        elif position == 'top_right':
            x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
            y = screen_rect.y() + 50
        elif position == 'bottom_left':
            x = screen_rect.x() + 50
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
        elif position == 'bottom_right':
            x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
        # 新增的中心位置选项
        elif position == 'top_left_center':
            x = screen_rect.x() + screen_rect.width() // 4 - subtitle_width // 2
            y = screen_rect.y() + 50
        elif position == 'top_right_center':
            x = screen_rect.x() + screen_rect.width() * 3 // 4 - subtitle_width // 2
            y = screen_rect.y() + 50
        elif position == 'bottom_left_center':
            x = screen_rect.x() + screen_rect.width() // 4 - subtitle_width // 2
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
        elif position == 'bottom_right_center':
            x = screen_rect.x() + screen_rect.width() * 3 // 4 - subtitle_width // 2
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
        elif position == 'left_center':
            x = screen_rect.x() + 50
            y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
        elif position == 'right_center':
            x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
            y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
        elif position == 'top_center':
            x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
            y = screen_rect.y() + 50
        elif position == 'bottom_center':
            x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
            y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            
        return x, y
    
    # 测试用例
    screen = MockScreenRect(0, 0, 1920, 1080)
    
    test_positions = [
        'center', 'top', 'bottom', 'left', 'right',
        'top_left', 'top_right', 'bottom_left', 'bottom_right',
        'top_left_center', 'top_right_center', 'bottom_left_center', 'bottom_right_center',
        'left_center', 'right_center', 'top_center', 'bottom_center'
    ]
    
    for position in test_positions:
        x, y = calculate_position(position, screen)
        print(f"{position:20} -> X={x:4}, Y={y:4}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_position_calculation()
