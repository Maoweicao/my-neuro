# coding:utf-8
"""
测试日志管理功能
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from UI import Widget

def test_log_management():
    """测试日志管理功能"""
    app = QApplication(sys.argv)
    
    # 创建Widget实例
    widget = Widget("设置", 9)  # 9是设置页面的索引
    
    # 检查是否有新的日志管理方法
    methods_to_check = [
        '_update_log_status',
        'save_logs_package', 
        'clear_all_logs',
        'view_logs_directory',
        '_collect_system_info',
        '_collect_runtime_info'
    ]
    
    print("检查日志管理方法:")
    for method in methods_to_check:
        if hasattr(widget, method):
            print(f"✓ {method} - 存在")
        else:
            print(f"✗ {method} - 不存在")
    
    # 检查UI元素
    widget.show()
    
    print("\n检查UI元素:")
    ui_elements = [
        'log_status_label',
        'save_logs_btn',
        'clear_logs_btn', 
        'view_logs_btn'
    ]
    
    for element in ui_elements:
        if hasattr(widget, element):
            print(f"✓ {element} - 存在")
        else:
            print(f"✗ {element} - 不存在")
    
    app.quit()
    return True

if __name__ == "__main__":
    try:
        test_log_management()
        print("\n✓ 日志管理功能测试完成")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
