import asyncio
from typing import Optional, Dict, List
from contextlib import AsyncExitStack
from mcp import ClientSession, stdio_client
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters
from dotenv import load_dotenv
import json
import os
import sys
import subprocess
import platform

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, config, event_bus=None):
        """初始化MCP客户端
        
        Args:
            config: 配置信息
            event_bus: 事件总线，用于发布事件
        """
        self.sessions: Dict[str, ClientSession] = {} # 修改为字典来存储多个会话
        self.exit_stack = AsyncExitStack()

        self.all_available_tools_for_llm: List[Dict] = []
        self.tool_to_session_map: Dict[str, ClientSession] = {}
        self.config = config
        self.system = platform.system().lower()
        
        # 从配置中获取MCP服务器配置（新格式）
        mcp_config = config.get("mcp", {})
        self.mcp_servers = mcp_config.get("mcpServers", {})
        
        # 向后兼容：如果没有新格式，尝试从旧格式转换
        if not self.mcp_servers:
            self._convert_legacy_config(mcp_config)
    
    def _convert_legacy_config(self, mcp_config):
        """将旧格式配置转换为新格式"""
        self.mcp_servers = {}
        
        # 处理URLs (SSE)
        urls = mcp_config.get('urls', [])
        if isinstance(urls, str):
            urls = [url.strip() for url in urls.split(',') if url.strip()]
        elif not isinstance(urls, list):
            urls = []
        
        for i, url in enumerate(urls):
            if url.strip():
                server_name = f'legacy_url_{i+1}'
                self.mcp_servers[server_name] = {
                    'transport': 'sse',
                    'url': url.strip(),
                    'headers': {},
                    'enabled': True
                }
        
        # 处理Paths (stdio/python)
        paths = mcp_config.get('paths', [])
        if isinstance(paths, str):
            paths = [path.strip() for path in paths.split(',') if path.strip()]
        elif not isinstance(paths, list):
            paths = []
        
        for i, path in enumerate(paths):
            if path.strip():
                server_name = f'legacy_path_{i+1}'
                if path.endswith('.py'):
                    self.mcp_servers[server_name] = {
                        'transport': 'python',
                        'module': path.strip(),
                        'args': [],
                        'enabled': True
                    }
                else:
                    self.mcp_servers[server_name] = {
                        'transport': 'stdio',
                        'command': path.strip(),
                        'args': [],
                        'env': {},
                        'enabled': True
                    }


    async def start(self):
        """启动所有启用的MCP服务器连接"""
        tools = []
        
        for server_name, server_config in self.mcp_servers.items():
            if not server_config.get('enabled', True):
                continue
                
            transport = server_config.get('transport', 'stdio')
            
            try:
                if transport == 'sse':
                    await self._connect_sse_server(server_name, server_config)
                    
                elif transport == 'streamablehttp':
                    await self._connect_streamable_http_server(server_name, server_config)
                    
                elif transport == 'stdio':
                    await self._connect_stdio_server(server_name, server_config)
                    
                elif transport == 'python':
                    await self._connect_python_server(server_name, server_config)
                    
            except Exception as e:
                print(f"连接到MCP服务器 {server_name} 时出错: {e}")
        
        print(f"全部的工具：{self.all_available_tools_for_llm}\n")
        print(f"工具到会话的映射：{list(self.tool_to_session_map.keys())}\n")

    async def _connect_sse_server(self, server_name, config):
        """连接SSE服务器"""
        url = config.get('url', '')
        headers = config.get('headers', {})
        
        if not url:
            print(f"SSE服务器 {server_name} 未配置URL")
            return
        
        print(f"连接到SSE MCP服务器: {server_name} ({url})")
        
        # 创建SSE客户端
        read, write = await self.exit_stack.enter_async_context(sse_client(url, headers=headers))
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        self.sessions[server_name] = session
        print(f"MCP会话已初始化: {server_name}")
        
        # 获取工具列表
        response = await session.list_tools()
        for tool in response.tools:
            llm_tool_format = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            self.all_available_tools_for_llm.append(llm_tool_format)
            self.tool_to_session_map[tool.name] = session

    async def _connect_streamable_http_server(self, server_name, config):
        """连接Streamable HTTP服务器"""
        # 目前使用与SSE相同的方式，后续可扩展
        await self._connect_sse_server(server_name, config)

    async def _connect_stdio_server(self, server_name, config):
        """连接stdio服务器"""
        command = config.get('command', '')
        args = config.get('args', [])
        env = config.get('env', {})
        package = config.get('package', '')
        script = config.get('script', '')
        
        if not command and not package and not script:
            print(f"stdio服务器 {server_name} 未配置命令、包或脚本")
            return
        
        # 智能处理UV和Bun命令
        final_command = command
        final_args = args.copy()
        
        if package:
            # 如果配置了包名，检查是否是UV或Bun包
            if command in ['uv', 'bun'] or (not command and self._is_tool_available('uv')):
                final_command = 'uv'
                final_args = ['run', package] + args
                print(f"连接到UV MCP服务器: {server_name} (包: {package})")
            elif command == 'bun' or (not command and self._is_tool_available('bun')):
                final_command = 'bun'
                final_args = ['run', package] + args
                print(f"连接到Bun MCP服务器: {server_name} (包: {package})")
            else:
                print(f"连接到stdio MCP服务器: {server_name} ({command} {package})")
        elif script:
            # 如果配置了脚本，检查是否是UV或Bun脚本
            if command in ['uv', 'bun'] or (not command and self._is_tool_available('uv')):
                final_command = 'uv'
                final_args = ['run', script] + args
                print(f"连接到UV MCP服务器: {server_name} (脚本: {script})")
            elif command == 'bun' or (not command and self._is_tool_available('bun')):
                final_command = 'bun'
                final_args = ['run', script] + args
                print(f"连接到Bun MCP服务器: {server_name} (脚本: {script})")
            else:
                final_command = command or script
                print(f"连接到stdio MCP服务器: {server_name} ({final_command})")
        else:
            print(f"连接到stdio MCP服务器: {server_name} ({command})")
        
        # 合并环境变量
        server_env = os.environ.copy()
        if env:
            server_env.update(env)
        
        # 确保包含conda环境的PATH（如果存在的话）
        # 默认使用my-neuro-tts环境，如果没有设置CONDA_DEFAULT_ENV的话
        conda_env_path = os.environ.get('CONDA_DEFAULT_ENV', 'my-neuro-tts')
        if conda_env_path:
            conda_bin_path = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Scripts' if os.name == 'nt' else 'bin')
            current_path = server_env.get('PATH', '')
            if conda_bin_path not in current_path:
                server_env['PATH'] = conda_bin_path + os.pathsep + current_path
        
        # 确保UV或Bun在PATH中（如果使用的话）
        if final_command in ['uv', 'bun']:
            self._ensure_tool_in_path(final_command, server_env)
        
        server_params = StdioServerParameters(
            command=final_command,
            args=final_args,
            env=server_env
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await session.initialize()
        
        self.sessions[server_name] = session
        print(f"MCP会话已初始化: {server_name}")
        
        # 获取工具列表
        response = await session.list_tools()
        for tool in response.tools:
            llm_tool_format = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            self.all_available_tools_for_llm.append(llm_tool_format)
            self.tool_to_session_map[tool.name] = session

    async def _connect_python_server(self, server_name, config):
        """连接Python服务器"""
        module = config.get('module', '')
        args = config.get('args', [])
        
        if not module:
            print(f"Python服务器 {server_name} 未配置模块")
            return
        
        print(f"连接到Python MCP服务器: {server_name} ({module})")
        
        # 构建命令
        if module.endswith('.py'):
            # 如果是Python文件
            if os.path.exists(module):
                command = sys.executable
                args = [module] + args
            else:
                print(f"Python文件不存在: {module}")
                return
        else:
            # 如果是模块名
            command = sys.executable
            args = ['-m', module] + args
        
        # 设置环境变量，确保包含conda环境的PATH
        # 默认使用my-neuro-tts环境，如果没有设置CONDA_DEFAULT_ENV的话
        server_env = os.environ.copy()
        conda_env_path = os.environ.get('CONDA_DEFAULT_ENV', 'my-neuro-tts')
        if conda_env_path:
            conda_bin_path = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Scripts' if os.name == 'nt' else 'bin')
            current_path = server_env.get('PATH', '')
            if conda_bin_path not in current_path:
                server_env['PATH'] = conda_bin_path + os.pathsep + current_path
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=server_env
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await session.initialize()
        
        self.sessions[server_name] = session
        print(f"MCP会话已初始化: {server_name}")
        
        # 获取工具列表
        response = await session.list_tools()
        for tool in response.tools:
            llm_tool_format = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            self.all_available_tools_for_llm.append(llm_tool_format)
            self.tool_to_session_map[tool.name] = session

    def _ensure_tool_in_path(self, tool_name, env_dict):
        """确保工具在PATH中，如果不在则尝试添加常见安装路径"""
        current_path = env_dict.get('PATH', '')
        
        # 检查工具是否已在PATH中
        if self._is_tool_available(tool_name, env_dict):
            return
        
        # 尝试添加常见安装路径
        install_paths = []
        
        if self.system == "windows":
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                install_paths.append(os.path.join(local_app_data, "MCPTools"))
        else:
            home = os.path.expanduser("~")
            install_paths.append(os.path.join(home, ".local", "bin"))
        
        for path in install_paths:
            if os.path.exists(path) and path not in current_path:
                env_dict['PATH'] = f"{path}{os.pathsep}{current_path}"
                if self._is_tool_available(tool_name, env_dict):
                    print(f"找到 {tool_name} 在: {path}")
                    return
        
        print(f"警告: {tool_name} 未在PATH中找到，可能导致连接失败")

    def _is_tool_available(self, tool_name, env_dict=None):
        """检查工具是否可用"""
        try:
            env = env_dict if env_dict else os.environ
            subprocess.run([tool_name, "--version"],
                         capture_output=True,
                         check=True,
                         timeout=5,
                         env=env)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def process_query(self, query: str) -> str:
        """使用可用工具处理查询"""
        # 检查是否有可用的会话
        if not self.sessions:
            return "没有可用的MCP服务器连接。"

        messages = [{"role": "user", "content": query}]
        final_text = []

        while True:
            # 这里需要集成LLM调用，暂时返回简单响应
            # 实际实现需要根据您的LLM集成来调整

            # 模拟LLM响应（需要替换为实际的LLM调用）
            response_content = f"处理查询: {query}"

            # 检查是否需要调用工具（这里是模拟逻辑）
            tool_calls = []  # 需要从LLM响应中提取

            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    if tool_name in self.tool_to_session_map:
                        session = self.tool_to_session_map[tool_name]
                        # 注意：这里需要是async方法才能使用await
                        # result = await session.call_tool(tool_name, tool_args)

                        final_text.append(f"[调用工具 {tool_name} 参数 {tool_args}]")

                        # 模拟结果内容
                        content_str = f"工具 {tool_name} 的执行结果"

                        messages.append({
                            "role": "user",
                            "content": content_str
                        })
                    else:
                        final_text.append(f"[工具 {tool_name} 不可用]")
            else:
                final_text.append(response_content)
                break

        return "\n".join(final_text)

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
        
    
    try:
        # 示例配置
        config = {
            "mcp": {
                "mcpServers": {
                    "example_stdio": {
                        "transport": "stdio",
                        "command": "echo",
                        "args": ["Hello MCP"],
                        "enabled": True
                    }
                }
            }
        }
        
        client = MCPClient(config)
        await client.start()
        
        # 示例查询
        result = await client.process_query("测试查询")
        print(f"查询结果: {result}")
        
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())