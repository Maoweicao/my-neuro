#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的WebAPI服务器测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from UI import WebAPIServer

class MockUI:
    """模拟UI类"""
    def __init__(self):
        self.config_data = {
            'webapi': {
                'api_key': '',
                'host': '127.0.0.1',
                'port': 8888
            }
        }

    def log_user_input(self, message):
        print(f"[LOG] User input: {message}")

    def log_llm_response(self, response):
        print(f"[LOG] LLM response: {response}")

    def interrupt_current_operations(self):
        print("[LOG] Interrupt operations")
        return True

    def trigger_live2d_motion(self, motion_index):
        print(f"[LOG] Trigger motion: {motion_index}")

if __name__ == "__main__":
    print("启动独立的WebAPI服务器测试...")

    # 创建模拟UI
    mock_ui = MockUI()

    # 创建WebAPI服务器
    server = WebAPIServer('127.0.0.1', 8888, mock_ui)

    try:
        print("WebAPI服务器启动中...")
        server.run()
    except Exception as e:
        print(f"服务器运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("清理服务器...")
        if server:
            server.stop_server()
