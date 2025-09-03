#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试进程间通信功能
"""

import socket
import json
import time
import os
import threading

def test_socket_communication():
    """测试socket通信"""
    print("=== 测试Socket通信 ===")

    # 启动一个简单的服务器线程来模拟main.py
    def mock_server():
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('127.0.0.1', 8889))
            server_socket.listen(1)
            print("模拟服务器已启动，监听端口 8889")

            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    print(f"收到连接: {addr}")

                    data = client_socket.recv(1024)
                    if data:
                        signal_data = json.loads(data.decode('utf-8'))
                        print(f"收到信号: {signal_data}")

                    client_socket.close()
                    break  # 只处理一个连接就退出
                except Exception as e:
                    print(f"服务器错误: {e}")
                    break

            server_socket.close()
        except Exception as e:
            print(f"服务器启动失败: {e}")

    # 启动服务器线程
    server_thread = threading.Thread(target=mock_server, daemon=True)
    server_thread.start()

    # 等待服务器启动
    time.sleep(1)

    # 发送中断信号
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "interrupt",
            "timestamp": time.time(),
            "source": "test_client"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ Socket通信测试成功")
    except Exception as e:
        print(f"✗ Socket通信测试失败: {e}")

    # 等待服务器线程结束
    server_thread.join(timeout=2)

def test_file_signal():
    """测试文件信号"""
    print("\n=== 测试文件信号 ===")

    signal_file = "interrupt_signal.tmp"

    # 创建信号文件
    try:
        signal_data = {
            "type": "interrupt",
            "timestamp": time.time(),
            "source": "test_file"
        }

        with open(signal_file, 'w', encoding='utf-8') as f:
            json.dump(signal_data, f)

        print("✓ 文件信号创建成功")

        # 读取并验证
        with open(signal_file, 'r', encoding='utf-8') as f:
            read_data = json.load(f)

        print(f"✓ 文件信号读取成功: {read_data}")

        # 清理文件
        os.remove(signal_file)
        print("✓ 文件信号清理成功")

    except Exception as e:
        print(f"✗ 文件信号测试失败: {e}")

def test_combined_communication():
    """测试组合通信方案"""
    print("\n=== 测试组合通信方案 ===")

    # 1. 首先尝试socket通信
    print("1. 尝试Socket通信...")
    socket_success = False
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1.0)
        client_socket.connect(('127.0.0.1', 8889))

        signal_data = {
            "type": "interrupt",
            "timestamp": time.time(),
            "source": "combined_test"
        }

        client_socket.send(json.dumps(signal_data).encode('utf-8'))
        client_socket.close()

        print("✓ Socket通信成功")
        socket_success = True
    except Exception as e:
        print(f"⚠ Socket通信失败: {e}")

    # 2. 如果socket失败，使用文件信号
    if not socket_success:
        print("2. 回退到文件信号...")
        try:
            signal_data = {
                "type": "interrupt",
                "timestamp": time.time(),
                "source": "combined_fallback"
            }

            with open("interrupt_signal.tmp", 'w', encoding='utf-8') as f:
                json.dump(signal_data, f)

            print("✓ 文件信号创建成功")

            # 清理文件
            os.remove("interrupt_signal.tmp")
            print("✓ 文件信号清理成功")

        except Exception as e:
            print(f"✗ 文件信号也失败: {e}")

def main():
    """主测试函数"""
    print("开始测试进程间通信功能...")
    print("=" * 50)

    test_socket_communication()
    test_file_signal()
    test_combined_communication()

    print("\n" + "=" * 50)
    print("进程间通信测试完成！")

if __name__ == "__main__":
    main()
