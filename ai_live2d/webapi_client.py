#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的WebAPI客户端示例
演示如何使用WebAPI与AI系统交互
"""

import requests
import json
import time
from typing import Optional

class WebAPIClient:
    """WebAPI客户端类"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}"
    
    def check_status(self) -> dict:
        """检查服务状态"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def send_message(self, message: str) -> dict:
        """发送消息"""
        data = {"message": message}
        if self.api_key:
            data["api_key"] = self.api_key
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def chat_interactive(self):
        """交互式聊天"""
        print("=== WebAPI 交互式聊天 ===")
        print(f"连接到: {self.base_url}")
        print("输入 'quit' 或 'exit' 退出")
        print("-" * 40)
        
        # 检查服务状态
        status = self.check_status()
        if "error" in status:
            print(f"❌ 服务不可用: {status['error']}")
            return
        else:
            print(f"✅ 服务状态: {status.get('message', '正常')}")
            print("-" * 40)
        
        while True:
            try:
                user_input = input("\n你: ").strip()
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("再见！")
                    break
                
                if not user_input:
                    continue
                
                print("🤔 AI正在思考...")
                
                # 发送消息
                result = self.send_message(user_input)
                
                if "error" in result:
                    print(f"❌ 错误: {result['error']}")
                else:
                    ai_response = result.get('response', '没有回复')
                    print(f"🤖 AI: {ai_response}")
                    
                    # 显示一些额外信息
                    if 'timestamp' in result:
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp']))
                        print(f"   (时间: {timestamp})")
            
            except KeyboardInterrupt:
                print("\n\n检测到 Ctrl+C，退出聊天...")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")

def main():
    """主函数"""
    print("WebAPI 客户端")
    print("=" * 50)
    
    # 获取连接信息
    host = input("服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port_input = input("端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("API密钥 (可选): ").strip() or None
    
    try:
        port = int(port_input)
    except ValueError:
        print("❌ 端口号必须是数字！")
        return
    
    # 创建客户端
    client = WebAPIClient(host, port, api_key)
    
    # 开始交互
    client.chat_interactive()

if __name__ == "__main__":
    main()
