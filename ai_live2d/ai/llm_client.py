"""
LLM客户端模块 - 负责与LLM API通信和消息历史管理
"""

import json
import asyncio
import logging
import aiohttp
from typing import Dict, List, Any, Optional, Callable, Coroutine

logger = logging.getLogger("llm_client")

class LLMClient:
    """LLM客户端类，处理与大语言模型API的交互和消息历史管理"""
    
    def __init__(self, config:dict, event_bus=None):
        """初始化LLM客户端
        
        Args:
            config: 配置信息，包含LLM API相关配置
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus

        # 回调函数
        self.on_llm_output_callback = None # LLM输出文本回调
        
        # 从配置中获取LLM相关配置
        self.api_key = config.get("llm", {}).get("api_key", "")
        self.api_url = config.get("llm", {}).get("api_url", "https://api.openai.com/v1")
        self.model = config.get("llm", {}).get("model", "gpt-3.5-turbo")
        self.system_prompt = config.get("llm", {}).get("system_prompt", "")
        
        # 上下文管理配置
        self.enable_limit = config.get("llm", {}).get("enable_limit", True)
        self.max_messages = config.get("llm", {}).get("max_messages", 10)

        # MCP相关配置
        self.mcp_client = None
        self.tool_args = ""
        self.tool_name = ""
        self.usetool = False
        # MCP工具列表
        self.mcp_tools = []
        
        # 初始化消息历史
        self.messages = []
        
        # 设置系统提示词
        if self.system_prompt:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 创建持久化HTTP连接池
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(),
            connector=aiohttp.TCPConnector(limit_per_host=4)
        )
        
        logger.info("初始化LLM客户端... [ 完成 ]")

    def set_callbacks(self, on_llm_output: Optional[Callable[[str], Coroutine]] = None):
        """设置回调函数"""
        self.on_llm_output_callback = on_llm_output
        logger.info("设置LLM回调函数... [ 成功 ]")
    
    def add_message(self, role: str, content: Any, image_data: Any=None):
        """添加消息到上下文
        
        Args:
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            image_data: 用于多模态的图片数据
        
        Returns:
            添加后的消息列表
        """
        if not image_data:
            self.messages.append({
                "role": role,
                "content": content
            })
        else:
            self.messages.append({
                "role": role,
                "content": [
                    {"type": "text", "text": content},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            })
        
        # 裁剪消息
        if self.enable_limit:
            self.trim_messages()
        
        logger.debug(f"添加消息: {role}, 当前消息数: {len(self.messages)}")
        return self.messages
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取当前上下文的所有消息
        
        Returns:
            消息列表
        """
        return self.messages.copy()
    
    def trim_messages(self):
        """裁剪消息，确保消息数量不超过最大限制"""
        if not self.enable_limit or len(self.messages) <= self.max_messages:
            return
        
        # 保留系统消息（如果有）
        system_msgs = [msg for msg in self.messages if msg["role"] == "system"]
        non_system_msgs = [msg for msg in self.messages if msg["role"] != "system"]
        
        # 仅裁剪非系统消息
        if len(non_system_msgs) > self.max_messages:
            # 使用切片代替列表重建
            non_system_msgs = non_system_msgs[-self.max_messages:]
        
        # 重建消息数组
        self.messages = system_msgs + non_system_msgs
    
    async def send_message(self, text: str, image_data=None, stream: bool=True, tools=None, tool_choice=None, use_tool_call: bool=None, not_show: bool=False) -> str:
        """发送消息到LLM并获取回复
        
        Args:
            text: 用户消息文本
            image_data: 可选的图片数据, 用于多模态
            stream: 是否使用流式响应
        
        Returns:
            LLM的回复文本
        
        Raises:
            Exception: 请求失败时抛出异常
        """
        try:
            # 添加用户消息到上下文
            self.add_message("user", text, image_data)
            
            # 准备请求数据
            request_data = {
                "model": self.model,
                "messages": self.messages,
                "stream": stream
            }
            if tools:
                request_data["tools"] = tools
            if use_tool_call:
                request_data["tool_choice"] = "auto"
            
            # 调试日志
            logger.debug(f"发送给LLM的消息数: {len(self.messages)}")
            logger.info(self.messages)
            
            # 组装完整的API URL
            api_url = f"{self.api_url}/chat/completions" if not self.api_url.endswith('/chat/completions') else self.api_url
            
            # 处理响应
            if stream:
                return await self._handle_streaming_response(api_url, request_data)
            else:
                return await self._handle_normal_response(api_url, request_data)
        
        except Exception as e:
            logger.error(f"LLM请求错误: {e}")
            if self.event_bus:
                await self.event_bus.publish("llm_error", {"error": str(e)})
            raise
    
    async def _handle_streaming_response(self, api_url: str, request_data: Dict[str, Any]) -> str:
        """处理流式响应
        
        Args:
            api_url: API URL
            request_data: 请求数据
        
        Returns:
            完整的响应文本
        """
        full_response = ""
        
        try:
            # 重置工具调用状态
            self.tool_name = ""
            self.tool_args = ""
            self.usetool = False

            # 使用aiohttp进行异步请求
            headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            
            async with self.session.post(api_url, json=request_data, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM服务器错误: {response.status}, {error_text}")
                
                # 使用异步生成器处理流
                async for chunk in self._process_stream(response):
                    full_response += chunk

                    if self.on_llm_output_callback:
                        await self.on_llm_output_callback({
                            "text": chunk,
                            "full_text": full_response,
                            "is_final": False
                        })

            # 处理工具调用
            if self.usetool and self.tool_name and self.tool_args:
                try:
                    # 处理可能连接的多个JSON对象，只取第一个完整的
                    tool_args_str = self.tool_args.strip()
                    if '}{' in tool_args_str:
                        # 找到第一个完整的JSON对象
                        brace_count = 0
                        end_pos = 0
                        for i, char in enumerate(tool_args_str):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos > 0:
                            tool_args_str = tool_args_str[:end_pos]
                    
                    # 解析工具参数
                    tool_args_dict = json.loads(tool_args_str)
                    result = await self.mcp_client.tool_to_session_map[self.tool_name].call_tool(self.tool_name, tool_args_dict)
                    result_text = result.content[0].text
                    
                    # 添加工具使用记录到消息历史
                    self.add_message("assistant", f"use_tool {self.tool_name} with args{tool_args_dict} get result {result_text}")
                    
                    # 重置状态
                    self.tool_name = ""
                    self.tool_args = ""
                    self.usetool = False
                
                    # 递归调用处理工具结果，传入空字符串避免重复用户输入
                    full_response = await self.send_message(
                        "", 
                        stream=True, 
                        tools=self.mcp_client.all_available_tools_for_llm, 
                        tool_choice=self.mcp_client.tool_to_session_map,
                        use_tool_call=True
                    )
                   
                    # 清理临时消息
                    self.messages = [msg for msg in self.messages if "use_tool" not in msg.get("content", "")]
                    
                except json.JSONDecodeError as e:
                    logger.error(f"工具参数JSON解析失败: {self.tool_args}, 错误: {e}")
                    # 回退到普通响应处理
                    if full_response.strip():
                        self.add_message("assistant", full_response)
                except Exception as e:
                    logger.error(f"工具调用失败: {e}")
                    # 回退到普通响应处理
                    if full_response.strip():
                        self.add_message("assistant", full_response)
            else:
                # 普通响应处理
                if full_response.strip():
                    self.add_message("assistant", full_response)

                if self.on_llm_output_callback:
                    await self.on_llm_output_callback({
                        "text": '',
                        "full_text": full_response,
                        "is_final": True
                    })
            
            # 发布完成事件
            if self.event_bus:
                await self.event_bus.publish("llm_complete", {
                    "text": full_response,
                    "message_count": len(self.messages)
                })
            
            return full_response
            
        except Exception as e:
            logger.error(f"流式响应处理失败: {e}")
            raise

    async def _process_stream(self, response):
        """处理流式响应"""
        has_tool_call = False
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if not line.startswith('data: '):
                continue
                
            if line.endswith('[DONE]'):
                break
            
            try:
                # 增量解析JSON
                data = json.loads(line[6:]) # 去掉 "data: " 前缀
                if 'choices' not in data or not data['choices']:
                    continue
                    
                delta = data['choices'][0].get('delta', {})
                content = delta.get('content', '')
                tool_calls = delta.get('tool_calls', [])
                # 处理工具调用
                if tool_calls:
                    has_tool_call = True
                    for tool_call in tool_calls:
                        function_info = tool_call.get('function', {})
                        if function_info:
                            # 累加工具名称（避免重复）
                            tool_name = function_info.get('name', '')
                            if tool_name and tool_name not in self.tool_name:
                                self.tool_name += tool_name
                            
                            # 累加工具参数（字符串形式）
                            tool_args = function_info.get('arguments', '')
                            if tool_args:
                                self.tool_args += tool_args
                            
                            self.usetool = True
                
                # 只有在整个响应中没有工具调用时才输出内容
                if content and not has_tool_call:
                    yield content

            except json.JSONDecodeError:
                logger.warning(f"JSON解析错误: {line}")
            except Exception as e:
                logger.error(f"流处理错误: {e}")
    
    async def _handle_normal_response(self, api_url: str, request_data: Dict[str, Any]) -> str:
        """处理普通响应
        
        Args:
            api_url: API URL
            request_data: 请求数据
        
        Returns:
            响应文本
        """
        # 修改请求数据，禁用流式响应
        request_data["stream"] = False
        
        try:
            # 使用aiohttp进行异步请求
            timeout = aiohttp.ClientTimeout(total=60)  # 设置超时
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with session.post(api_url, json=request_data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"LLM服务器错误: {response.status}, {error_text}")
                    
                    # 解析响应
                    response_data = await response.json()
                    
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        message = response_data['choices'][0].get('message', {})
                        response_text = message.get('content', '')
                        
                        # 将AI响应添加到上下文
                        if response_text.strip():
                            self.add_message("assistant", response_text)
                        
                        # 发布完成事件
                        if self.event_bus:
                            await self.event_bus.publish("llm_complete", {
                                "text": response_text,
                                "message_count": len(self.messages)
                            })
                        
                        return response_text
                    else:
                        raise Exception("LLM响应格式错误")
                        
        except Exception as e:
            logger.error(f"普通响应处理失败: {e}")
            raise
    
    async def get_context_info(self) -> Dict[str, Any]:
        """获取上下文信息
        
        Returns:
            包含上下文统计信息的字典
        """
        system_count = len([msg for msg in self.messages if msg["role"] == "system"])
        user_count = len([msg for msg in self.messages if msg["role"] == "user"])
        assistant_count = len([msg for msg in self.messages if msg["role"] == "assistant"])
        
        return {
            "total_messages": len(self.messages),
            "system_messages": system_count,
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "max_messages": self.max_messages,
            "enable_limit": self.enable_limit
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def close(self):
        """关闭资源 - 确保正确释放连接"""
        if not self.session.closed:
            await self.session.close()

    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.close()