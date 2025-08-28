#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI cURL 样式测试脚本
模拟cURL命令的测试方式
"""

import requests
import json
import argparse
import sys

def send_chat_request(url, message, api_key=None, timeout=30):
    """
    发送聊天请求
    
    Args:
        url: API端点URL
        message: 消息内容
        api_key: 可选的API密钥
        timeout: 超时时间
    """
    
    # 构建请求数据
    data = {"message": message}
    if api_key:
        data["api_key"] = api_key
    
    # 设置请求头
    headers = {"Content-Type": "application/json"}
    
    print(f"curl -X POST {url} \\")
    print(f"  -H \"Content-Type: application/json\" \\")
    print(f"  -d '{json.dumps(data, ensure_ascii=False)}'")
    print()
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=timeout)
        
        print(f"HTTP/{response.status_code}")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length']:
                print(f"{key}: {value}")
        print()
        
        if response.headers.get('content-type', '').startswith('application/json'):
            result = response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(response.text)
            
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("curl: (28) Operation timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("curl: (7) Failed to connect")
        return False
    except Exception as e:
        print(f"curl: error - {str(e)}")
        return False

def send_status_request(url, timeout=5):
    """发送状态检查请求"""
    
    print(f"curl {url}")
    print()
    
    try:
        response = requests.get(url, timeout=timeout)
        
        print(f"HTTP/{response.status_code}")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length']:
                print(f"{key}: {value}")
        print()
        
        if response.headers.get('content-type', '').startswith('application/json'):
            result = response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(response.text)
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"curl: error - {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="WebAPI cURL样式测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 基本聊天测试
  python curl_test.py --host 127.0.0.1 --port 8888 --message "你好"
  
  # 带API密钥的测试
  python curl_test.py --host 127.0.0.1 --port 8888 --message "你好" --api-key "your-key"
  
  # 检查服务状态
  python curl_test.py --host 127.0.0.1 --port 8888 --status
  
  # 使用自定义URL
  python curl_test.py --url "http://192.168.1.100:8888/api/chat" --message "测试消息"
        """
    )
    
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8888, help="端口号 (默认: 8888)")
    parser.add_argument("--url", help="完整的API URL (如果指定则忽略host和port)")
    parser.add_argument("--message", "-m", help="要发送的消息")
    parser.add_argument("--api-key", "-k", help="API密钥")
    parser.add_argument("--status", "-s", action="store_true", help="检查服务状态")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="超时时间(秒) (默认: 30)")
    
    args = parser.parse_args()
    
    # 确定基础URL
    if args.url:
        if args.status:
            status_url = args.url.replace('/api/chat', '/api/status')
        else:
            chat_url = args.url
    else:
        base_url = f"http://{args.host}:{args.port}"
        chat_url = f"{base_url}/api/chat"
        status_url = f"{base_url}/api/status"
    
    print("WebAPI cURL 样式测试")
    print("=" * 50)
    
    if args.status:
        # 状态检查
        print("📋 检查服务状态")
        print("-" * 20)
        success = send_status_request(status_url, args.timeout)
        sys.exit(0 if success else 1)
    
    elif args.message:
        # 发送聊天消息
        print("💬 发送聊天消息")
        print("-" * 20)
        success = send_chat_request(chat_url, args.message, args.api_key, args.timeout)
        sys.exit(0 if success else 1)
    
    else:
        # 交互模式
        print("🔄 交互模式")
        print("输入消息发送到API，输入 'quit' 退出")
        print("-" * 30)
        
        while True:
            try:
                message = input("\n💬 消息: ").strip()
                if message.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not message:
                    continue
                
                print()
                success = send_chat_request(chat_url, message, args.api_key, args.timeout)
                
            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                break
            except EOFError:
                break

if __name__ == "__main__":
    main()
