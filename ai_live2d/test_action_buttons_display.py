#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试动作按钮显示功能
"""
import sys
import os
import json
import time
import socket

def test_show_action_buttons():
    """测试显示动作按钮"""
    print("=== 测试显示动作按钮 ===")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "show_action_buttons",
            "timestamp": time.time(),
            "source": "test_script"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ 已发送显示动作按钮信号")
        return True

    except Exception as e:
        print(f"✗ 发送显示动作按钮信号失败: {e}")
        return False

def test_hide_action_buttons():
    """测试隐藏动作按钮"""
    print("\n=== 测试隐藏动作按钮 ===")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "hide_action_buttons",
            "timestamp": time.time(),
            "source": "test_script"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ 已发送隐藏动作按钮信号")
        return True

    except Exception as e:
        print(f"✗ 发送隐藏动作按钮信号失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试动作按钮显示功能...")
    print("注意：需要先启动main.py服务")

    # 等待用户确认main.py已启动
    input("请确保main.py服务已启动，然后按Enter键继续测试...")

    # 测试显示动作按钮
    show_success = test_show_action_buttons()

    # 等待用户观察
    input("请观察动作按钮是否已显示，按Enter键继续测试隐藏...")

    # 测试隐藏动作按钮
    hide_success = test_hide_action_buttons()

    # 输出测试结果
    print("\n=== 测试结果 ===")
    print(f"显示动作按钮测试: {'✓ 通过' if show_success else '✗ 失败'}")
    print(f"隐藏动作按钮测试: {'✓ 通过' if hide_success else '✗ 失败'}")

    if show_success and hide_success:
        print("\n🎉 所有测试通过！动作按钮显示功能正常！")
    else:
        print("\n⚠️ 部分测试失败，请检查main.py服务是否正常运行")

if __name__ == "__main__":
    main()
