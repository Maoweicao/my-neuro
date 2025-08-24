import asyncio
from typing import Optional, Dict, List
from contextlib import AsyncExitStack
from mcp import ClientSession, stdio_client
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters
from dotenv import load_dotenv
import json

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
        # 从配置中获取直播相关配置
        self.urls = config.get("mcp", {}).get("urls", [])
        self.paths = config.get("mcp", {}).get("paths", [])


    async def start(self):
        
        tools = []
        if self.urls != ['']:
            print("连接到远程SSE MCP服务器...")
            for url in self.urls:
                try:
                    print(111111111111111111111111111)
                    read, write = await self.exit_stack.enter_async_context(sse_client(url))
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self.sessions[url] = session # 将会话存储在字典中
                    print(f"MCP会话已初始化: {url}")
                    
                    # 列出每个服务器的工具 (可选)
                    response = await session.list_tools()
                    tools.append(response)
                    print(f"\nConnected to {url} with tools:", [tool for tool in tools])
            
                    # 为LLM绑定准备工具格式
                    for tool in response.tools:
                        llm_tool_format = {
                            "type":"function",
                            "function":{
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                            }
                        }
                        self.all_available_tools_for_llm.append(llm_tool_format)
                        # 建立工具名到会话的映射
                        self.tool_to_session_map[tool.name] = session
                
            
                except Exception as e:
                    print(f"连接到 {url} 时出错: {e}")
   

        command = 'python' if self.paths[0].endswith('.py') else 'node'
        server_params = StdioServerParameters(
                command = command,
                args = self.paths,
                env = None
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.sessions['stdio'] = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.sessions['stdio'].initialize()
        response = await self.sessions['stdio'].list_tools()
        tools.append(response)
        for tool in response.tools:
            llm_tool_format = {
                    "type":"function",
                    "function":{
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                    }
                }
            self.tool_to_session_map[tool.name] = self.sessions['stdio']
            self.all_available_tools_for_llm.append(llm_tool_format)
        
        print(f"全部的工具：{self.all_available_tools_for_llm}\n")
        self.tools = tools
        print(f"这是map{self.tool_to_session_map}\n")

    async def process_query(self, query: str) -> str:
        """Process a query using DeepSeek and available tools"""
        # 检查是否有可用的会话
        if not self.sessions:
            return "没有可用的MCP服务器连接。"
        
        # 示例：简单地使用字典中的第一个会话
        # 在更复杂的应用中，你可能需要更智能的会话选择逻辑

        else:

            messages = [
                {"role": "user", "content": query}
            ]
            llm = self.deepseek.bind_tools(self.all_available_tools_for_llm)
            final_text = []

            while True:
                response = llm.invoke(messages)
                print(response)
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']
                        result = await self.tool_to_session_map[tool_name].call_tool(tool_name, tool_args)
                        final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                        messages.append({
                            "role": "assistant",
                            "content": f"Tool {tool_name} was called with args {tool_args}"
                        })
                        #提取字符串内容
                        if isinstance(result, list) and hasattr(result[0], "text"):
                            content_str = result[0].text
                        else:
                            content_str = str(result)
                        messages.append({
                            "role": "user",
                            "content": content_str
                        })
                    # 继续循环，看 LLM 是否还要调用工具
                else:
                    # 没有更多 tool_call，输出最终内容

                    final_text.append(response.content)
                    break

            return "\n".join(final_text)


    async def cleanup(self):
            """Clean up resources"""
            await self.exit_stack.aclose()

async def main():
        
    
    try:
        # 传入一个URL列表

        client = MCPClient()
        await client.start()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())