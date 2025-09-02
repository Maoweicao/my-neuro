#!/usr/bin/env python3
"""
MCP工具验证脚本
验证UV和Bun工具是否正确安装并可用
"""

import subprocess
import sys
import os

def check_tool(tool_name, version_arg="--version"):
    """检查工具是否可用"""
    try:
        result = subprocess.run([tool_name, version_arg],
                              capture_output=True,
                              text=True,
                              timeout=10)
        if result.returncode == 0:
            print(f"✅ {tool_name} 已安装")
            print(f"   版本信息: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {tool_name} 安装异常")
            print(f"   错误信息: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print(f"❌ {tool_name} 未找到，请运行下载脚本安装")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ {tool_name} 响应超时")
        return False
    except Exception as e:
        print(f"❌ {tool_name} 检查失败: {e}")
        return False

def check_mcp_config():
    """检查MCP配置文件"""
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return False

    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        mcp_config = config.get("mcp", {})
        mcp_servers = mcp_config.get("mcpServers", {})

        uv_servers = [name for name, server in mcp_servers.items()
                     if server.get("transport") == "uv" and server.get("enabled", False)]
        bun_servers = [name for name, server in mcp_servers.items()
                      if server.get("transport") == "bun" and server.get("enabled", False)]

        if uv_servers:
            print(f"✅ 发现 {len(uv_servers)} 个启用的UV服务器: {', '.join(uv_servers)}")
        else:
            print("ℹ️  未发现启用的UV服务器")

        if bun_servers:
            print(f"✅ 发现 {len(bun_servers)} 个启用的Bun服务器: {', '.join(bun_servers)}")
        else:
            print("ℹ️  未发现启用的Bun服务器")

        return True
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def main():
    print("MCP工具验证脚本")
    print("=" * 30)
    print()

    # 检查工具
    tools_available = 0

    if check_tool("uv"):
        tools_available += 1

    if check_tool("bun"):
        tools_available += 1

    # 检查配置文件
    print()
    config_ok = check_mcp_config()

    # 总结
    print()
    print("验证结果:")
    print(f"- 可用工具数量: {tools_available}/2")
    print(f"- 配置文件状态: {'✅' if config_ok else '❌'}")

    if tools_available == 0:
        print()
        print("建议操作:")
        print("1. 运行下载脚本: python utils\\mcp_tool_downloader.py")
        print("2. 或运行批处理文件: download_mcp_tools.bat")
        print("3. 更新PATH环境变量")
        print("4. 重新运行此验证脚本")

    if tools_available > 0 and config_ok:
        print()
        print("🎉 所有检查通过！您可以开始使用UV和Bun MCP服务器了。")

    return 0 if tools_available > 0 and config_ok else 1

if __name__ == "__main__":
    sys.exit(main())
