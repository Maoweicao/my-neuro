#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台词转换API演示脚本
演示如何使用新的/api/dialogue端点
"""

import requests
import json

def demo_dialogue_conversion(host='127.0.0.1', port=8888, api_key=None):
    """演示台词转换功能"""
    url = f"http://{host}:{port}/api/dialogue"

    print("🎭 台词转换API演示")
    print("=" * 50)

    # 示例台词
    sample_dialogues = [
        "你好，我是小明",
        "今天天气真不错，我们去公园吧",
        "我喜欢吃冰淇淋，尤其是草莓味的",
        "谢谢你的帮助，我很感激",
        "对不起，我错了",
        "恭喜你，考试及格了！"
    ]

    for i, dialogue in enumerate(sample_dialogues, 1):
        print(f"\n{i}. 原始台词: {dialogue}")

        data = {"dialogue": dialogue}
        if api_key:
            data["api_key"] = api_key

        try:
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                converted = result.get('converted_dialogue', '转换失败')
                print(f"   转换后: {converted}")
            else:
                print(f"   错误: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"   请求失败: {e}")

def main():
    """主函数"""
    print("台词转换API演示脚本")
    print("这个脚本演示了如何使用新的/api/dialogue端点")
    print("将普通台词转换为适合AI角色表演的格式\n")

    host = input("服务器地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
    port = input("端口号 (默认: 8888): ").strip() or "8888"
    api_key = input("API密钥 (可选，直接回车跳过): ").strip() or None

    try:
        port = int(port)
    except ValueError:
        print("❌ 端口号必须是数字！")
        return

    print(f"\n🔗 连接到 {host}:{port}")
    if api_key:
        print("🔑 使用API密钥验证")

    # 演示转换
    demo_dialogue_conversion(host, port, api_key)

    print("\n✅ 演示完成！")
    print("\n💡 提示:")
    print("  - 转换后的台词包含动作描述和语气调整")
    print("  - 适合用于AI角色表演和Live2D动画")
    print("  - 可以与语音合成系统结合使用")

if __name__ == "__main__":
    main()
