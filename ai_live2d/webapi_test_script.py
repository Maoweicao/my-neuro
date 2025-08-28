#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI 测试脚本
根据WebAPI使用说明编写的测试脚本
"""

import requests
import json
import time
from typing import Optional, Dict, Any

class WebAPITester:
    """WebAPI测试器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}"
        
    def test_chat(self, message: str) -> Dict[str, Any]:
        """
        测试聊天API
        
        Args:
            message: 要发送的消息
            
        Returns:
            API响应的字典
        """
        url = f"{self.base_url}/api/chat"
        
        # 构建请求数据
        data = {"message": message}
        if self.api_key:
            data["api_key"] = self.api_key
        
        # 设置请求头
        headers = {"Content-Type": "application/json"}
        
        try:
            print(f"🔄 发送请求到: {url}")
            print(f"📤 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            start_time = time.time()
            response = requests.post(url, json=data, headers=headers, timeout=30)
            end_time = time.time()
            
            print(f"⏱️ 响应时间: {end_time - start_time:.2f}秒")
            print(f"📊 状态码: {response.status_code}")
            
            # 解析响应
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                print(f"📥 响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return result
            else:
                print(f"📥 响应内容: {response.text}")
                return {"error": "非JSON响应", "content": response.text}
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            print(f"❌ 错误: {error_msg}")
            return {"error": error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = "连接失败，请检查服务是否启动"
            print(f"❌ 错误: {error_msg}")
            return {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常: {str(e)}"
            print(f"❌ 错误: {error_msg}")
            return {"error": error_msg}
        except json.JSONDecodeError:
            error_msg = "响应不是有效的JSON格式"
            print(f"❌ 错误: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            print(f"❌ 错误: {error_msg}")
            return {"error": error_msg}
    
    def test_status(self) -> Dict[str, Any]:
        """测试服务状态"""
        url = f"{self.base_url}/api/status"
        
        try:
            print(f"🔄 检查服务状态: {url}")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 服务正常: {result}")
                return result
            else:
                error_msg = f"服务异常，状态码: {response.status_code}"
                print(f"⚠️ {error_msg}")
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"无法连接到服务: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def run_batch_tests(self):
        """运行批量测试"""
        print("=" * 60)
        print("🚀 WebAPI 批量测试开始")
        print("=" * 60)
        
        # 1. 服务状态检查
        print("\n📋 1. 服务状态检查")
        print("-" * 30)
        status_result = self.test_status()
        
        if "error" in status_result:
            print("❌ 服务不可用，停止测试")
            return
        
        # 2. 基本聊天测试
        print("\n💬 2. 基本聊天测试")
        print("-" * 30)
        
        test_messages = [
            "你好",
            "你是谁？",
            "今天天气怎么样？",
            "给我讲个笑话",
            "1+1等于几？"
        ]
        
        success_count = 0
        total_count = len(test_messages)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 测试 {i}/{total_count}: {message}")
            print("." * 20)
            
            result = self.test_chat(message)
            
            if "error" not in result and result.get("status") == "success":
                print(f"✅ 成功 - AI回复: {result.get('response', '无回复')[:100]}...")
                success_count += 1
            else:
                print(f"❌ 失败 - {result.get('error', '未知错误')}")
            
            # 避免请求过于频繁
            time.sleep(1)
        
        # 3. 测试结果统计
        print("\n📊 3. 测试结果统计")
        print("-" * 30)
        print(f"✅ 成功: {success_count}/{total_count}")
        print(f"❌ 失败: {total_count - success_count}/{total_count}")
        print(f"📈 成功率: {success_count/total_count*100:.1f}%")
        
        # 4. 错误测试
        print("\n🔧 4. 错误处理测试")
        print("-" * 30)
        
        # 空消息测试
        print("📝 测试空消息:")
        empty_result = self.test_chat("")
        if "error" in empty_result:
            print("✅ 空消息错误处理正常")
        else:
            print("⚠️ 空消息未被正确拒绝")
        
        print("\n" + "=" * 60)
        print("🎉 WebAPI 批量测试完成")
        print("=" * 60)

def main():
    """主函数"""
    print("WebAPI 测试脚本")
    print("基于官方使用说明编写")
    print("=" * 50)
    
    # 获取配置信息
    print("请输入WebAPI服务配置:")
    host = input("服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port_input = input("端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("API密钥 (可选，直接回车跳过): ").strip() or None
    
    try:
        port = int(port_input)
    except ValueError:
        print("❌ 端口号必须是数字！")
        return
    
    # 创建测试器
    tester = WebAPITester(host, port, api_key)
    
    print(f"\n🔧 配置信息:")
    print(f"   服务器: {host}:{port}")
    print(f"   API密钥: {'已设置' if api_key else '未设置'}")
    
    # 选择测试模式
    print(f"\n请选择测试模式:")
    print("1. 单条消息测试")
    print("2. 批量自动测试")
    print("3. 服务状态检查")
    
    choice = input("\n请输入选项 (1-3): ").strip()
    
    if choice == "1":
        # 单条消息测试
        print("\n🔄 单条消息测试模式")
        print("输入 'quit' 或 'exit' 退出")
        print("-" * 30)
        
        while True:
            message = input("\n💬 请输入消息: ").strip()
            if message.lower() in ['quit', 'exit', '退出']:
                break
            
            if not message:
                print("⚠️ 消息不能为空")
                continue
            
            result = tester.test_chat(message)
            print()  # 空行分隔
    
    elif choice == "2":
        # 批量自动测试
        tester.run_batch_tests()
    
    elif choice == "3":
        # 服务状态检查
        print("\n🔄 服务状态检查")
        print("-" * 30)
        tester.test_status()
    
    else:
        print("❌ 无效选项")
    
    print("\n👋 感谢使用WebAPI测试脚本！")

if __name__ == "__main__":
    main()
