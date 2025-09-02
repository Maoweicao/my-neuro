#!/usr/bin/env python3
"""
简单的MCP连接测试
"""

import asyncio
import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append('.')

async def test_mcp():
    try:
        from ai.mcp_client import MCPClient

        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("正在初始化MCP客户端...")
        client = MCPClient(config)

        print("正在启动MCP服务器连接...")
        await client.start()

        print("\n=== 测试结果 ===")
        print(f"连接的服务器数量: {len(client.sessions)}")
        print(f"可用的工具数量: {len(client.all_available_tools_for_llm)}")

        if client.sessions:
            print("\n连接的服务器:")
            for name in client.sessions.keys():
                print(f"  - {name}")

        if client.all_available_tools_for_llm:
            print("\n可用的工具:")
            for tool in client.all_available_tools_for_llm[:5]:  # 只显示前5个
                print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")
            if len(client.all_available_tools_for_llm) > 5:
                print(f"  ... 还有 {len(client.all_available_tools_for_llm) - 5} 个工具")

        await client.cleanup()
        print("\n✅ MCP连接测试成功完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())
