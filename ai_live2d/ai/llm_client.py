"""
LLM客户端模块 - 负责与LLM API通信和消息历史管理
"""

import json
import asyncio
import logging
import aiohttp
from typing import Dict, List, Any, Optional, Callable, Coroutine
import base64

logger = logging.getLogger("llm_client")
logger.setLevel(logging.DEBUG)

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
        self.on_llm_output_callback = None  # LLM输出文本回调

        # 中断控制
        self.interrupt_flag = False  # 中断标志，用于停止流式输出

        # 从配置中获取LLM相关配置
        llm_cfg = config.get("llm", {})
        self.api_key = llm_cfg.get("api_key", "")
        self.api_url = llm_cfg.get("api_url", "https://api.openai.com/v1")
        self.model = llm_cfg.get("model", "gpt-3.5-turbo")
        self.system_prompt = llm_cfg.get("system_prompt", "")

        # 视觉副模型配置（用于主模型不支持视觉时的回退）
        vision_cfg = config.get("vision", {}) or {}
        self.vision_enabled = config.get("setting", {}).get("vision_enabled", False) and bool(vision_cfg)
        self.vision_api_key = vision_cfg.get("api_key", "")
        self.vision_api_url = vision_cfg.get("api_url", "") or self.api_url
        self.vision_model = vision_cfg.get("model", "")  # 副模型名称（OpenAI兼容）
        # 内部检测缓存（来自UI写入的隐藏字段，可选）
        self._vision_internal = vision_cfg.get("_internal", {})

        # 上下文管理配置
        self.enable_limit = llm_cfg.get("enable_limit", True)
        self.max_messages = llm_cfg.get("max_messages", 10)

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
        # 关键配置日志（不打印密钥）
        logger.debug(
            f"[init] api_url={self.api_url}; model={self.model}; vision_enabled={self.vision_enabled}; "
            f"vision_api_url={self.vision_api_url}; enable_limit={self.enable_limit}; max_messages={self.max_messages}"
        )

    # ===== 日志辅助 =====
    def _log_preview(self, label: str, text: Any, max_len: int = 120):
        """统一的文本预览日志（避免刷屏）。"""
        try:
            if text is None:
                logger.debug(f"{label}: <None>")
                return
            if isinstance(text, (bytes, bytearray)):
                s = f"<bytes:{len(text)}>"
            elif isinstance(text, str):
                s = text.strip()
            else:
                # 容忍对象，尽量可读
                s = json.dumps(text, ensure_ascii=False, default=str)
            preview = s[:max_len] + ('…' if len(s) > max_len else '')
            logger.debug(f"{label}: len={len(s)}; preview='{preview}'")
        except Exception:
            pass

    def set_callbacks(self, on_llm_output: Optional[Callable[[str], Coroutine]] = None):
        """设置回调函数"""
        self.on_llm_output_callback = on_llm_output
        logger.info("设置LLM回调函数... [ 成功 ]")
        logger.debug(f"[callbacks] on_llm_output set? {bool(on_llm_output)}")
    
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
            self._log_preview(f"[messages] add role={role}", content)
        else:
            self.messages.append({
                "role": role,
                "content": [
                    {"type": "text", "text": content},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            })
            self._log_preview(f"[messages] add(role={role}) with image", content)
        
        # 裁剪消息
        if self.enable_limit:
            before = len(self.messages)
            self.trim_messages()
            after = len(self.messages)
            if after != before:
                logger.debug(f"[messages] trim from {before} -> {after} (max={self.max_messages})")
        
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
        logger.debug(f"[messages] trim_messages完成: total={len(self.messages)}; system={len(system_msgs)}; non_system={len(non_system_msgs)}")
    
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
            # 重置中断标志
            self.interrupt_flag = False
            logger.debug(f"[send] start: stream={stream}; has_image={bool(image_data)}; tools={bool(tools)}; use_tool_call={bool(use_tool_call)}")
            
            # 如果包含图像且主模型不支持视觉，但副模型支持，则先用副模型识图，注入文本再转主模型
            if image_data and await self._should_fallback_vision():
                logger.debug("[send] 进入视觉回退路径 -> 副模型先识图")
                vision_text = await self._call_vision_sidecar(text, image_data)
                if vision_text:
                    # 将识别结果注入上下文，作为系统说明，避免污染用户原话
                    inject_note = (
                        "[视觉识别摘要] 已用备用视觉模型将用户提供的图片进行识别，结果如下：\n"
                        f"{vision_text}\n"
                        "请在后续回答中仅基于该摘要进行推理，不再需要访问原始图像。"
                    )
                    self.add_message("system", inject_note)
                    # 之后按无图片的普通文本继续
                    self.add_message("user", text, image_data=None)
                else:
                    # 识图失败则退化为纯文本
                    logger.debug("[send] 视觉回退失败，退化为纯文本路径")
                    self.add_message("user", text, image_data=None)
            else:
                # 正常路径：主模型自己支持视觉或无图片
                logger.debug("[send] 正常路径：添加用户消息")
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
            logger.debug(f"[send] 发送给LLM的消息数: {len(self.messages)}")
            # 保留原有详细消息日志（可能很长）
            logger.info(self.messages)
            
            # 组装完整的API URL
            api_url = f"{self.api_url}/chat/completions" if not self.api_url.endswith('/chat/completions') else self.api_url
            logger.debug(f"[send] api_url={api_url}; stream={stream}")
            
            # 处理响应
            if stream:
                logger.debug("[send] 走流式响应路径")
                return await self._handle_streaming_response(api_url, request_data)
            else:
                logger.debug("[send] 走普通响应路径")
                return await self._handle_normal_response(api_url, request_data)
        
        except Exception as e:
            logger.error(f"LLM请求错误: {e}")
            if self.event_bus:
                await self.event_bus.publish("llm_error", {"error": str(e)})
            raise

    def _main_supports_vision(self) -> bool:
        """根据模型名与隐藏检测信息，判断主模型是否具备视觉能力。"""
        model_l = (self.model or "").lower()
        if self._vision_internal and isinstance(self._vision_internal, dict):
            flag = self._vision_internal.get('main_supports_vision')
            if isinstance(flag, bool):
                return flag
        vision_models = [
            'gpt-4-vision', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo',
            'claude-3', 'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku', 'claude-3-5-sonnet',
            'gemini-pro-vision', 'gemini-1.5-pro', 'gemini-1.5-flash',
            'qwen-vl', 'qwen2-vl', 'internvl', 'llava', 'moondream'
        ]
        supported = any(vm in model_l for vm in vision_models)
        logger.debug(f"[vision] main_supports_vision={supported} ({self.model})")
        return supported

    async def _should_fallback_vision(self) -> bool:
        """主模型不支持视觉且副模型可用时返回True。"""
        if not self.vision_enabled:
            logger.debug("[vision] 未启用视觉回退")
            return False
        if self._main_supports_vision():
            logger.debug("[vision] 主模型支持视觉，无需回退")
            return False
        ok = bool(self.vision_api_key and (self.vision_model or self.model) and self.vision_api_url)
        logger.debug(f"[vision] 可回退? {ok}; model={self.vision_model or self.model}; api_url={self.vision_api_url}")
        return ok

    async def _call_vision_sidecar(self, user_text: str, image_b64: str) -> str:
        """使用副模型（OpenAI兼容）进行图像理解，返回纯文本摘要。"""
        try:
            logger.debug("[vision] 调用副模型进行图片识别")
            url = self.vision_api_url
            api_url = f"{url}/chat/completions" if not url.endswith('/chat/completions') else url
            model = self.vision_model or self.model
            logger.debug(f"[vision] sidecar api_url={api_url}; model={model}")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.vision_api_key}"
            }
            prompt = (
                "你将看到一张图片与一段用户文本，请先基于图片进行描述，再结合用户文字说明，"
                "输出简洁、客观的要点摘要，不超过200字。只输出中文摘要，不要包含多余标记。"
            )
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text or "请识别图片"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}
            ]
            payload = {"model": model, "messages": messages, "stream": False}
            self._log_preview("[vision] sidecar payload.user_text", user_text)
            async with self.session.post(api_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    logger.error(f"视觉副模型调用失败: {resp.status}, {txt}")
                    return ""
                data = await resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                self._log_preview("[vision] sidecar 返回摘要", content)
                return content or ""
        except Exception as e:
            logger.error(f"视觉副模型调用异常: {e}")
            return ""
    
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
            logger.debug(f"[stream] POST -> {api_url}")
            
            async with self.session.post(api_url, json=request_data, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM服务器错误: {response.status}, {error_text}")
                logger.debug(f"[stream] 响应状态: {response.status}")
                
                # 使用异步生成器处理流
                async for chunk in self._process_stream(response):
                    full_response += chunk
                    self._log_preview("[stream] chunk", chunk, max_len=60)

                    if self.on_llm_output_callback:
                        # 通知增量
                        await self.on_llm_output_callback({
                            "text": chunk,
                            "full_text": full_response,
                            "is_final": False
                        })

            # 处理工具调用
            if self.usetool and self.tool_name and self.tool_args:
                try:
                    logger.debug(f"[tools] 检测到工具调用: name={self.tool_name}; args_len={len(self.tool_args)}")
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
                    self._log_preview("[tools] 工具结果预览", result_text)
                    
                    # 添加工具使用记录到消息历史
                    self.add_message("assistant", f"use_tool {self.tool_name} with args{tool_args_dict} get result {result_text}")
                    
                    # 重置状态
                    self.tool_name = ""
                    self.tool_args = ""
                    self.usetool = False
                
                    # 递归调用处理工具结果，传入空字符串避免重复用户输入
                    logger.debug("[tools] 将工具结果注入后，递归继续对话")
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
                    logger.debug(f"[stream] 完成，回调最终文本，len={len(full_response)}")
                    await self.on_llm_output_callback({
                        "text": '',
                        "full_text": full_response,
                        "is_final": True
                    })
            
            # 发布完成事件
            if self.event_bus:
                logger.debug("[stream] 发布 llm_complete 事件")
                await self.event_bus.publish("llm_complete", {
                    "text": full_response,
                    "message_count": len(self.messages)
                })
            
            self._log_preview("[stream] 返回完整响应", full_response)
            return full_response
            
        except Exception as e:
            logger.error(f"流式响应处理失败: {e}")
            raise

    async def _process_stream(self, response):
        """处理流式响应"""
        has_tool_call = False
        async for line in response.content:
            # 检查中断标志
            if self.interrupt_flag:
                logger.info("LLM输出被中断")
                break
                
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
                                logger.debug(f"[stream] tool_call: name={tool_name}")
                            
                            # 累加工具参数（字符串形式）
                            tool_args = function_info.get('arguments', '')
                            if tool_args:
                                self.tool_args += tool_args
                                logger.debug(f"[stream] tool_call: args_len(+)= {len(tool_args)}; total_args_len={len(self.tool_args)}")
                            
                            self.usetool = True
                
                # 只有在整个响应中没有工具调用时才输出内容
                if content and not has_tool_call:
                    # 按片吐出文本
                    self._log_preview("[stream] content增量", content, max_len=60)
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
                    logger.debug(f"[normal] 响应状态: {response.status}")
                    
                    # 解析响应
                    response_data = await response.json()
                    
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        message = response_data['choices'][0].get('message', {})
                        response_text = message.get('content', '')
                        self._log_preview("[normal] 返回文本预览", response_text)
                        
                        # 将AI响应添加到上下文
                        if response_text.strip():
                            self.add_message("assistant", response_text)
                        
                        # 发布完成事件
                        if self.event_bus:
                            logger.debug("[normal] 发布 llm_complete 事件")
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
    
    def interrupt(self):
        """中断当前LLM输出"""
        self.interrupt_flag = True
        logger.info("LLM输出已被中断")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def close(self):
        """关闭资源 - 确保正确释放连接"""
        if not self.session.closed:
            await self.session.close()
            logger.debug("[session] aiohttp ClientSession 已关闭")

    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.close()