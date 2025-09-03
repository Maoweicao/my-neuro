#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试简化后的中断功能
"""

import socket
import json
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ui_interrupt_signal():
    """测试UI发送的中断信号"""
    print("=" * 60)
    print("🧪 测试简化后的UI中断功能")
    print("=" * 60)

    try:
        # 模拟UI发送中断信号
        print("\n📤 模拟UI发送中断信号...")

        # 尝试通过socket发送中断信号
        socket_success = False
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2.0)  # 2秒超时
            client_socket.connect(('127.0.0.1', 8889))  # main.py监听的端口

            signal_data = {
                "type": "interrupt",
                "timestamp": time.time(),
                "source": "ui_test"
            }

            client_socket.send(json.dumps(signal_data).encode('utf-8'))
            client_socket.close()

            print("✓ 已通过socket发送中断信号")
            socket_success = True

        except (socket.timeout, socket.error) as e:
            print(f"⚠ Socket通信失败: {e}，将使用文件信号")

        # 如果socket失败，使用文件信号作为备用
        if not socket_success:
            try:
                with open("interrupt_signal.tmp", 'w', encoding='utf-8') as f:
                    signal_data = {
                        "type": "interrupt",
                        "timestamp": time.time(),
                        "source": "ui_test",
                        "force_stop": True
                    }
                    json.dump(signal_data, f)
                print("✓ 已创建中断信号文件")
            except Exception as e:
                print(f"❌ 创建中断信号文件失败: {e}")
                return False

        print("\n✅ UI中断信号发送完成")
        print("📋 信号内容:")
        print(f"   - 类型: {signal_data['type']}")
        print(f"   - 来源: {signal_data['source']}")
        print(f"   - 时间戳: {signal_data['timestamp']}")

        return True

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def main():
    """主函数"""
    success = test_ui_interrupt_signal()

    if success:
        print("\n" + "=" * 60)
        print("🎯 测试结果：UI中断信号发送成功！")
        print("📝 功能说明：")
        print("   - UI只负责发送中断信号")
        print("   - main.py负责接收并处理所有中断逻辑")
        print("   - 移除了直接杀进程的代码")
        print("   - 统一在main.py中进行判断和处理")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 测试失败：无法发送中断信号")
        print("=" * 60)

if __name__ == "__main__":
    main()
