#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI 服务检查脚本
检查WebAPI服务是否在运行
"""

import socket
import requests
import json

def check_port_open(host='127.0.0.1', port=8888):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_webapi_service(host='127.0.0.1', port=8888):
    """检查WebAPI服务状态"""
    print("🔍 WebAPI 服务检查")
    print("=" * 40)
    
    # 1. 检查端口
    print(f"1️⃣ 检查端口 {host}:{port} ...")
    if check_port_open(host, port):
        print(f"✅ 端口 {port} 已开放")
    else:
        print(f"❌ 端口 {port} 未开放")
        print("\n💡 解决方案:")
        print("   1. 启动UI程序: python UI.py")
        print("   2. 在设置页面启用WebAPI")
        print("   3. 点击'启动服务'按钮")
        return False
    
    # 2. 检查HTTP服务
    print(f"2️⃣ 检查HTTP服务...")
    try:
        url = f"http://{host}:{port}/api/status"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print("✅ WebAPI服务正常运行")
            try:
                data = response.json()
                print(f"   状态: {data.get('message', '正常')}")
            except:
                pass
            return True
        else:
            print(f"⚠️ 服务响应异常 (状态码: {response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ HTTP服务连接失败")
        print("   端口开放但服务未正确启动")
        return False
    except requests.exceptions.Timeout:
        print("❌ HTTP服务响应超时")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_config():
    """检查配置文件"""
    print("\n3️⃣ 检查配置文件...")
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查LLM配置
        llm_config = config.get('llm', {})
        if llm_config.get('api_key') and llm_config.get('api_url'):
            print("✅ LLM配置完整")
        else:
            print("⚠️ LLM配置不完整")
            print("   请在UI中配置API Key和API URL")
        
        # 检查WebAPI配置
        webapi_config = config.get('webapi', {})
        if webapi_config.get('enabled'):
            print("✅ WebAPI已启用")
            print(f"   端口: {webapi_config.get('port', 8888)}")
            print(f"   地址: {webapi_config.get('host', '127.0.0.1')}")
        else:
            print("⚠️ WebAPI未启用")
            print("   请在设置页面启用WebAPI")
        
        return config
        
    except FileNotFoundError:
        print("❌ 配置文件不存在")
        print("   请先运行UI程序创建配置")
        return None
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return None

def main():
    print("WebAPI 服务检查工具")
    print("=" * 50)
    
    # 检查配置
    config = check_config()
    
    # 确定检查的端口
    if config and config.get('webapi', {}).get('port'):
        port = config['webapi']['port']
    else:
        port = 8888
    
    # 检查服务
    if check_webapi_service('127.0.0.1', port):
        print("\n🎉 WebAPI服务检查通过！")
        print("可以开始使用测试脚本了")
    else:
        print("\n🔧 需要先启动WebAPI服务")
    
    print("\n📋 快速启动指南:")
    print("1. python UI.py")
    print("2. 配置LLM设置")
    print("3. 启用WebAPI并启动服务")
    print("4. 使用测试脚本验证")

if __name__ == "__main__":
    main()
