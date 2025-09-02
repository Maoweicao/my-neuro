#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI 打断功能测试脚本
演示如何使用WebAPI的打断功能
"""

import requests
import json
import time
import threading
from typing import Optional

class InterruptDemo:
    """打断功能演示类"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}"
    
    def send_chat_request(self, message: str, delay_interrupt: float = 0):
        """发送聊天请求，并在指定时间后发送打断"""
        def chat_worker():
            print(f"🤖 发送聊天请求: {message}")
            url = f"{self.base_url}/api/chat"
            data = {"message": message}
            if self.api_key:
                data["api_key"] = self.api_key
            
            try:
                response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 聊天响应: {result.get('response', '无响应')[:100]}...")
                else:
                    print(f"❌ 聊天请求失败: {response.status_code}")
            except Exception as e:
                print(f"❌ 聊天请求异常: {e}")
        
        def interrupt_worker():
            time.sleep(delay_interrupt)
            print("🛑 发送打断请求...")
            self.send_interrupt()
        
        # 启动聊天线程
        chat_thread = threading.Thread(target=chat_worker)
        chat_thread.start()
        
        # 如果设置了延迟打断，启动打断线程
        if delay_interrupt > 0:
            interrupt_thread = threading.Thread(target=interrupt_worker)
            interrupt_thread.start()
            interrupt_thread.join()
        
        chat_thread.join()
    
    def send_interrupt(self):
        """发送打断请求"""
        url = f"{self.base_url}/api/interrupt"
        data = {}
        if self.api_key:
            data["api_key"] = self.api_key
        
        try:
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    print("✅ 打断成功")
                elif result.get("status") == "warning":
                    print("⚠️ 打断响应正常（没有正在进行的操作）")
                else:
                    print(f"❌ 打断失败: {result}")
            else:
                print(f"❌ 打断请求失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 打断请求异常: {e}")
    
    def demo_basic_interrupt(self):
        """演示基本的打断功能"""
        print("=" * 60)
        print("🛑 WebAPI 打断功能演示")
        print("=" * 60)
        
        print("\n📋 1. 测试单独的打断请求")
        print("-" * 30)
        self.send_interrupt()
        
        print("\n📋 2. 测试聊天+打断组合")
        print("-" * 30)
        print("注意：这个演示需要手动在另一个终端运行")
        print("步骤：")
        print("1. 在另一个终端运行: python -c \"import time; time.sleep(10); print('模拟长时间操作')\"")
        print("2. 然后运行这个脚本发送打断请求")
        
        input("\n按回车键发送打断请求...")
        self.send_interrupt()
        
        print("\n" + "=" * 60)
        print("🎉 演示完成")
        print("=" * 60)

def main():
    """主函数"""
    print("WebAPI 打断功能演示")
    print("=" * 50)
    
    # 获取配置信息
    host = input("服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port_input = input("端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("API密钥 (可选，直接回车跳过): ").strip() or None
    
    try:
        port = int(port_input)
    except ValueError:
        print("❌ 端口号必须是数字！")
        return
    
    # 创建演示实例
    demo = InterruptDemo(host, port, api_key)
    
    # 运行演示
    demo.demo_basic_interrupt()

if __name__ == "__main__":
    main()
