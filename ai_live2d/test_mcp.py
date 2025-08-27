# -*- coding: utf-8 -*-
"""
测试MCP工具管理器的基本功能
"""
import sys
import os
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from UI import MCPToolManager

def test_mcp_manager():
    """测试MCP管理器的基本功能"""
    app = QApplication(sys.argv)
    
    # 创建一个模拟的父组件
    class MockParent:
        def __init__(self):
            self.config_data = {
                'mcp': {
                    'tools': [
                        {
                            'name': '测试工具1',
                            'type': 'server',
                            'url': 'ws://localhost:3000/mcp',
                            'path': '',
                            'enabled': True,
                            'args': {'timeout': 5000},
                            'description': '这是一个测试工具'
                        }
                    ]
                }
            }
    
    # 创建MCP管理器
    parent = MockParent()
    mcp_manager = MCPToolManager(parent)
    
    # 显示管理器
    mcp_manager.show()
    mcp_manager.resize(800, 600)
    mcp_manager.setWindowTitle('MCP工具管理器测试')
    
    print("MCP工具管理器已启动")
    print(f"已加载 {len(mcp_manager.mcp_tools)} 个工具")
    
    # 输出工具配置
    config = mcp_manager.get_tools_config()
    print("当前配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 运行应用
    return app.exec_()

if __name__ == '__main__':
    sys.exit(test_mcp_manager())
