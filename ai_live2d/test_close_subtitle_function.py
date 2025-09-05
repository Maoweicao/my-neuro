#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试关闭字幕功能
"""

def test_close_subtitle_logic():
    """测试关闭字幕的逻辑"""
    print("=== 测试关闭字幕功能 ===")
    
    # 模拟UI类的关闭字幕方法
    class MockWindow:
        def __init__(self, name):
            self.name = name
            self.closed = False
            
        def close(self):
            self.closed = True
            print(f"{self.name} 已关闭")
    
    class MockUI:
        def __init__(self):
            self._test_window = None
            
        def create_preview_window(self):
            """创建预览窗口"""
            self._test_window = MockWindow("预览字幕窗口")
            print("预览字幕窗口已创建")
            
        def close_current_subtitle(self):
            """关闭当前字幕（包括预览字幕和主程序字幕）"""
            success = True
            
            # 1. 关闭预览字幕窗口
            if hasattr(self, '_test_window') and self._test_window:
                try:
                    self._test_window.close()
                    self._test_window = None
                except Exception as e:
                    print(f"关闭预览字幕窗口时出错: {e}")
                    success = False
            else:
                print("没有预览字幕窗口需要关闭")
            
            # 2. 发送消息关闭主程序字幕
            try:
                # 模拟发送消息
                print("主程序字幕关闭消息已发送")
            except Exception as e:
                print(f"发送主程序字幕关闭消息失败: {e}")
                success = False
                
            return success
    
    # 测试场景
    ui = MockUI()
    
    print("\n测试1: 没有预览窗口时关闭字幕")
    result = ui.close_current_subtitle()
    print(f"结果: {'成功' if result else '失败'}")
    
    print("\n测试2: 有预览窗口时关闭字幕")
    ui.create_preview_window()
    result = ui.close_current_subtitle()
    print(f"结果: {'成功' if result else '失败'}")
    
    print("\n测试3: 再次关闭（窗口已关闭）")
    result = ui.close_current_subtitle()
    print(f"结果: {'成功' if result else '失败'}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_close_subtitle_logic()
