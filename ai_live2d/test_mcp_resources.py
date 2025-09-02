#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP资源加载测试脚本
"""
import sys
import os
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, stdio_client
from mcp.client.stdio import StdioServerParameters

def get_conda_env():
    """获取包含conda环境的PATH的环境变量"""
    server_env = os.environ.copy()

    # 确保包含conda环境的PATH（如果存在的话）
    conda_env_path = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env_path:
        conda_bin_path = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Scripts' if os.name == 'nt' else 'bin')
        current_path = server_env.get('PATH', '')
        if conda_bin_path not in current_path:
            server_env['PATH'] = conda_bin_path + os.pathsep + current_path
        print(f"检测到conda环境: {conda_env_path}")

    # 强制重新排列PATH，确保Node.js路径在前面
    nodejs_path = r'C:\nvm4w\nodejs'
    current_path = server_env.get('PATH', '')
    if nodejs_path in current_path:
        # 如果Node.js路径已在PATH中，将其移到前面
        paths = current_path.split(os.pathsep)
        paths.remove(nodejs_path)
        paths.insert(0, nodejs_path)
        server_env['PATH'] = os.pathsep.join(paths)
        print(f"重新排列PATH，将Node.js路径移到前面")
    else:
        # 如果不在PATH中，添加到前面
        server_env['PATH'] = nodejs_path + os.pathsep + current_path
        print(f"添加Node.js路径到PATH前面: {nodejs_path}")

    return server_env

async def test_mcp_server():
    """测试MCP服务器连接和资源加载"""
    print("=== MCP服务器资源加载测试 ===")

    # 配置bing-cn-mcp服务器
    config = {
        'transport': 'stdio',
        'command': 'npx',
        'args': ['bing-cn-mcp'],
        'env': {}
    }

    exit_stack = AsyncExitStack()

    try:
        print("正在连接到bing-cn-mcp服务器...")

        # 连接服务器
        command = config.get('command', '')
        args = config.get('args', [])
        env = config.get('env', {})

        server_env = get_conda_env()
        if env:
            server_env.update(env)

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=server_env
        )

        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        print("正在初始化会话...")
        await session.initialize()
        print("✅ 会话初始化成功")

        # 测试加载工具
        print("\n--- 加载工具 ---")
        try:
            response = await session.list_tools()
            tools = response.tools
            print(f"✅ 找到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  • {tool.name}: {tool.description}")
        except Exception as e:
            print(f"❌ 加载工具失败: {e}")

        # 测试加载提示
        print("\n--- 加载提示 ---")
        try:
            response = await session.list_prompts()
            prompts = response.prompts
            print(f"✅ 找到 {len(prompts)} 个提示:")
            for prompt in prompts:
                print(f"  • {prompt.name}: {getattr(prompt, 'description', '无描述')}")
        except AttributeError:
            print("⚠️  服务器不支持list_prompts方法")
        except Exception as e:
            print(f"❌ 加载提示失败: {e}")

        # 测试加载资源
        print("\n--- 加载资源 ---")
        try:
            response = await session.list_resources()
            resources = response.resources
            print(f"✅ 找到 {len(resources)} 个资源:")
            for resource in resources:
                print(f"  • {resource.uri}: {getattr(resource, 'name', '无名称')}")
        except AttributeError:
            print("⚠️  服务器不支持list_resources方法")
        except Exception as e:
            print(f"❌ 加载资源失败: {e}")

    except Exception as e:
        print(f"❌ 连接服务器失败: {e}")
    finally:
        await exit_stack.aclose()
        print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
