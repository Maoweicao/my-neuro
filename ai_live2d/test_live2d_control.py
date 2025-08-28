#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Live2D控制功能
用于验证UI、WebAPI和文件触发器是否能正确控制Live2D模型
"""

import json
import time
import requests
import sys
import os

def test_file_trigger_motion(motion_index=0):
    """测试文件触发器控制动作"""
    print(f"🎭 测试文件触发器控制动作: {motion_index}")
    
    motion_file = "motion_trigger.tmp"
    data = {
        "action": "trigger_motion",
        "motion_index": motion_index,
        "motion_group": "TapBody",
        "priority": 3,
        "timestamp": time.time()
    }
    
    try:
        with open(motion_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"✅ 动作触发文件已写入: {motion_file}")
        return True
    except Exception as e:
        print(f"❌ 写入动作触发文件失败: {e}")
        return False

def test_file_trigger_expression(expression_name="happy"):
    """测试文件触发器控制表情"""
    print(f"😊 测试文件触发器控制表情: {expression_name}")
    
    expression_file = "expression_trigger.tmp"
    data = {
        "action": "trigger_expression",
        "expression_name": expression_name,
        "timestamp": time.time()
    }
    
    try:
        with open(expression_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"✅ 表情触发文件已写入: {expression_file}")
        return True
    except Exception as e:
        print(f"❌ 写入表情触发文件失败: {e}")
        return False

def test_webapi_motion(motion_index=1, host="127.0.0.1", port=8888):
    """测试WebAPI控制动作"""
    print(f"🌐 测试WebAPI控制动作: {motion_index}")
    
    api_url = f"http://{host}:{port}/api/live2d/motion"
    data = {
        "motion_index": motion_index,
        "motion_group": "TapBody",
        "priority": 3
    }
    
    try:
        response = requests.post(api_url, json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ WebAPI动作控制成功: {result}")
            return True
        else:
            print(f"❌ WebAPI动作控制失败: HTTP {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到WebAPI服务器: {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ WebAPI动作控制异常: {e}")
        return False

def test_webapi_expression(expression_name="sad", host="127.0.0.1", port=8888):
    """测试WebAPI控制表情"""
    print(f"🌐 测试WebAPI控制表情: {expression_name}")
    
    api_url = f"http://{host}:{port}/api/live2d/expression"
    data = {
        "expression_name": expression_name
    }
    
    try:
        response = requests.post(api_url, json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ WebAPI表情控制成功: {result}")
            return True
        else:
            print(f"❌ WebAPI表情控制失败: HTTP {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到WebAPI服务器: {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ WebAPI表情控制异常: {e}")
        return False

def test_webapi_status(host="127.0.0.1", port=8888):
    """测试WebAPI服务状态"""
    print(f"🔍 检查WebAPI服务状态")
    
    api_url = f"http://{host}:{port}/api/status"
    
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ WebAPI服务正常: {result}")
            return True
        else:
            print(f"❌ WebAPI服务异常: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ WebAPI服务未启动: {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ WebAPI状态检查异常: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 Live2D控制功能测试")
    print("=" * 60)
    
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"📁 当前工作目录: {os.getcwd()}")
    
    results = []
    
    # 1. 测试WebAPI状态
    print("\n1️⃣ WebAPI服务测试")
    webapi_available = test_webapi_status()
    results.append(("WebAPI服务状态", webapi_available))
    
    # 2. 测试文件触发器
    print("\n2️⃣ 文件触发器测试")
    file_motion_success = test_file_trigger_motion(0)
    results.append(("文件触发器-动作", file_motion_success))
    
    time.sleep(1)  # 等待1秒
    
    file_expression_success = test_file_trigger_expression("happy")
    results.append(("文件触发器-表情", file_expression_success))
    
    # 3. 测试WebAPI控制（如果可用）
    if webapi_available:
        print("\n3️⃣ WebAPI控制测试")
        
        time.sleep(1)
        webapi_motion_success = test_webapi_motion(1)
        results.append(("WebAPI控制-动作", webapi_motion_success))
        
        time.sleep(1)
        webapi_expression_success = test_webapi_expression("sad")
        results.append(("WebAPI控制-表情", webapi_expression_success))
    else:
        print("\n3️⃣ WebAPI控制测试 - 跳过（服务不可用）")
        results.append(("WebAPI控制-动作", False))
        results.append(("WebAPI控制-表情", False))
    
    # 4. 显示测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    success_count = 0
    for test_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{test_name:20s} - {status}")
        if success:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(results)} 项测试通过")
    
    if success_count == len(results):
        print("🎉 所有测试都通过了！Live2D控制功能正常工作。")
    elif success_count > 0:
        print("⚠️  部分测试通过。请检查失败的项目。")
    else:
        print("💥 所有测试都失败了。请检查Live2D服务和配置。")
    
    print("\n💡 使用提示:")
    print("   - 确保Live2D桌宠服务已启动 (python main.py)")
    print("   - 确保WebAPI服务已启动 (python standalone_webapi.py)")
    print("   - 检查配置文件中的Live2D模型路径")
    print("   - 观察Live2D桌宠窗口是否有动作和表情变化")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n💤 测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        sys.exit(1)
