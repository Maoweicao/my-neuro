#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM客户端测试脚本 - 完全异步版本
"""

import sys
import os
import asyncio
import logging
import json
import aiohttp
from unittest.mock import AsyncMock

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_llm_client")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入LLM客户端和事件总线
from core.event_bus import EventBus

# 尝试多个可能的配置路径
possible_config_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"),  # 项目根目录
    "config.json",  # 当前目录
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),  # 测试脚本目录
]

config = None
for config_path in possible_config_paths:
    try:
        if os.path.exists(config_path):
            logger.info(f"尝试加载配置: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"成功加载配置: {config_path}")
            break
    except Exception as e:
        logger.warning(f"加载配置失败: {config_path} - {e}")

# 如果没有找到配置文件，使用模拟API
if not config:
    logger.warning("未找到配置文件，使用模拟API测试")
    # 创建测试配置
    config = {
        "llm": {
            "api_key": "test_key",
            "api_url": "http://localhost:8000/v1",
            "model": "test-model",
            "system_prompt": "你是一个测试助手。"
        },
        "context": {
            "enable_limit": True,
            "max_messages": 10
        }
    }
    use_mock = True
else:
    use_mock = False

# 模拟LLM客户端类 - 异步版本
class MockLLMClient:
    def __init__(self, config=None, event_bus=None):
        self.config = config or {}
        self.event_bus = event_bus
        self.messages = []
        
        # 添加系统提示词
        system_prompt = self.config.get("llm", {}).get("system_prompt")
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        logger.info("模拟LLM客户端初始化完成")
    
    async def set_system_prompt(self, prompt):
        """设置系统提示词 - 异步版本"""
        # 移除旧的系统提示词
        self.messages = [msg for msg in self.messages if msg["role"] != "system"]
        
        # 添加新的系统提示词
        if prompt:
            self.messages.insert(0, {
                "role": "system",
                "content": prompt
            })
            
        logger.info("模拟系统提示词已更新")
        
        # 发布事件
        if self.event_bus:
            await self.event_bus.publish("llm_system_prompt_updated", {
                "prompt": prompt
            })
    
    async def send_message(self, text, image_path=None, stream=True):
        """发送消息 - 异步版本"""
        # 发布开始事件
        if self.event_bus:
            await self.event_bus.publish("llm_start", {
                "text": text,
                "has_image": image_path is not None
            })
        
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": text
        })
        
        # 模拟处理延迟
        await asyncio.sleep(0.5)
        
        # 生成模拟响应
        if "错误" in text or "error" in text.lower():
            # 模拟错误响应
            if self.event_bus:
                await self.event_bus.publish("llm_error", {
                    "error": "模拟错误：请求包含错误关键词"
                })
            raise Exception("模拟错误：请求包含错误关键词")
        
        # 生成不同类型的响应
        if "长回复" in text:
            response = "这是一个很长很长的回复，用来测试流式响应功能。它包含很多字符，可以很好地展示逐字输出的效果。"
        elif "简短" in text:
            response = "好的！"
        else:
            response = f"这是对'{text}'的模拟回复，包含{len(text)}个字符。"
        
        # 模拟流式响应
        if stream and self.event_bus:
            for i, char in enumerate(response):
                await self.event_bus.publish("llm_streaming", {
                    "text": char,
                    "full_text": response[:i+1],
                    "is_final": False
                })
                await asyncio.sleep(0.02)  # 模拟流式响应延迟
            
            # 发布流式响应结束
            await self.event_bus.publish("llm_streaming", {
                "text": "",
                "full_text": response,
                "is_final": True
            })
        
        # 添加助手回复
        self.messages.append({
            "role": "assistant",
            "content": response
        })
        
        # 发布完成事件
        if self.event_bus:
            await self.event_bus.publish("llm_complete", {
                "text": response,
                "message_count": len(self.messages)
            })
        
        return response
    
    def get_messages(self):
        """获取消息历史"""
        return self.messages.copy()
    
    async def get_context_info(self):
        """获取上下文信息"""
        system_count = len([msg for msg in self.messages if msg["role"] == "system"])
        user_count = len([msg for msg in self.messages if msg["role"] == "user"])
        assistant_count = len([msg for msg in self.messages if msg["role"] == "assistant"])
        
        return {
            "total_messages": len(self.messages),
            "system_messages": system_count,
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "max_messages": 10,
            "enable_limit": True
        }
    
    async def clear_messages(self, keep_system=True):
        """清空消息历史"""
        if keep_system:
            self.messages = [msg for msg in self.messages if msg["role"] == "system"]
        else:
            self.messages = []
        
        if self.event_bus:
            await self.event_bus.publish("llm_messages_cleared", {
                "keep_system": keep_system,
                "remaining_count": len(self.messages)
            })

async def test_api_connectivity():
    """测试API连接性"""
    if use_mock:
        logger.info("使用模拟API，跳过连接性测试")
        return True
    
    try:
        api_url = config.get("llm", {}).get("api_url", "")
        if not api_url:
            logger.warning("配置中未找到API URL")
            return False
        
        # 简单的连接测试
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=5) as response:
                    logger.info(f"API连接测试: {response.status}")
                    return response.status in [200, 404, 401]  # 这些状态码说明服务在运行
            except Exception as e:
                logger.warning(f"API连接测试失败: {e}")
                return False
    except Exception as e:
        logger.error(f"API连接性测试错误: {e}")
        return False

async def test_llm_client():
    """测试LLM客户端的基本功能"""
    global config, use_mock
    
    event_bus = EventBus()
    
    # 记录事件
    streaming_chunks = []
    complete_responses = []
    errors = []
    
    # 事件回调 - 异步版本
    async def on_llm_start(data):
        text = data.get("text", "")
        has_image = data.get("has_image", False)
        logger.info(f"🚀 LLM开始处理: {text} (包含图片: {has_image})")
    
    async def on_llm_streaming(data):
        text = data.get("text", "")
        full_text = data.get("full_text", "")
        is_final = data.get("is_final", False)
        
        if text:
            print(text, end="", flush=True)  # 实时显示流式输出
            streaming_chunks.append(text)
        
        if is_final:
            print()  # 换行
            logger.info("📝 流式响应结束")
    
    async def on_llm_complete(data):
        text = data.get("text", "")
        message_count = data.get("message_count", 0)
        complete_responses.append(text)
        logger.info(f"✅ LLM完成响应: {len(text)}字符, 消息数: {message_count}")
    
    async def on_llm_error(data):
        error = data.get("error", "")
        errors.append(error)
        logger.error(f"❌ LLM错误: {error}")
    
    async def on_system_prompt_updated(data):
        prompt = data.get("prompt", "")
        logger.info(f"📋 系统提示词已更新: {prompt[:50]}...")
    
    llm_client = None
    try:
        # 订阅事件（注意需要await）
        await event_bus.subscribe("llm_start", on_llm_start)
        await event_bus.subscribe("llm_streaming", on_llm_streaming)
        await event_bus.subscribe("llm_complete", on_llm_complete)
        await event_bus.subscribe("llm_error", on_llm_error)
        await event_bus.subscribe("llm_system_prompt_updated", on_system_prompt_updated)
        
        print("\n" + "="*60)
        print("🧪 LLM客户端测试")
        print("="*60)
        
        # 测试API连接性
        if not use_mock:
            logger.info("🔍 测试API连接性...")
            if not await test_api_connectivity():
                logger.warning("API连接失败，切换到模拟模式")
                use_mock = True
        
        # 创建LLM客户端
        if use_mock:
            logger.info("🎭 使用模拟LLM客户端")
            llm_client = MockLLMClient(config, event_bus)
        else:
            logger.info("🌐 使用真实LLM客户端")
            from ai.llm_client import LLMClient
            llm_client = LLMClient(config, event_bus)
        
        # 测试1: 系统提示词设置
        logger.info("\n🧪 测试1: 系统提示词设置")
        system_prompt = "你是一个友好的AI助手，用简洁的语言回答问题。"
        await llm_client.set_system_prompt(system_prompt)
        
        # 测试2: 基本对话
        logger.info("\n🧪 测试2: 基本对话")
        test_message = "你好，请简单介绍一下自己。"
        logger.info(f"📤 发送消息: {test_message}")
        print("🤖 AI回复: ", end="")
        
        try:
            response = await asyncio.wait_for(
                llm_client.send_message(test_message, stream=True), 
                timeout=10.0
            )
            logger.info(f"✅ 收到完整响应: {len(response)}字符")
        except asyncio.TimeoutError:
            logger.error("⏰ LLM响应超时")
            if not use_mock:
                raise
        
        # 测试3: 短回复
        logger.info("\n🧪 测试3: 短回复")
        short_message = "请给我一个简短的回复"
        logger.info(f"📤 发送消息: {short_message}")
        print("🤖 AI回复: ", end="")
        
        response2 = await llm_client.send_message(short_message)
        
        # 测试4: 长回复（流式测试）
        logger.info("\n🧪 测试4: 长回复（流式测试）")
        long_message = "请给我一个长回复来测试流式输出"
        logger.info(f"📤 发送消息: {long_message}")
        print("🤖 AI回复: ", end="")
        
        response3 = await llm_client.send_message(long_message, stream=True)
        
        # 测试5: 上下文信息
        logger.info("\n🧪 测试5: 上下文信息")
        context_info = await llm_client.get_context_info()
        logger.info(f"📊 上下文信息: {context_info}")
        
        # 测试6: 消息历史
        logger.info("\n🧪 测试6: 消息历史")
        messages = llm_client.get_messages()
        logger.info(f"📚 消息历史数量: {len(messages)}")
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = str(msg["content"])[:50] + "..." if len(str(msg["content"])) > 50 else str(msg["content"])
            logger.info(f"  {i+1}. {role}: {content}")
        
        # 测试7: 错误处理（仅模拟模式）
        if use_mock:
            logger.info("\n🧪 测试7: 错误处理")
            try:
                await llm_client.send_message("请触发一个错误")
            except Exception as e:
                logger.info(f"✅ 成功捕获预期错误: {e}")
        
        # 测试8: 清空消息
        logger.info("\n🧪 测试8: 清空消息")
        await llm_client.clear_messages(keep_system=True)
        final_messages = llm_client.get_messages()
        logger.info(f"🧹 清空后消息数量: {len(final_messages)}")
        
        # 测试结果统计
        print("\n" + "="*60)
        print("📊 测试结果统计")
        print("="*60)
        print(f"流式响应块数: {len(streaming_chunks)}")
        print(f"完整响应数: {len(complete_responses)}")
        print(f"错误数: {len(errors)}")
        
        if complete_responses:
            print("\n收到的响应:")
            for i, response in enumerate(complete_responses, 1):
                preview = response[:100] + "..." if len(response) > 100 else response
                print(f"  {i}. {preview}")
        
        logger.info("✅ LLM客户端测试完成")
        return len(complete_responses) > 0  # 如果收到响应则测试通过
        
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 清理资源
        if llm_client and hasattr(llm_client, '__aexit__'):
            try:
                await llm_client.__aexit__(None, None, None)
            except:
                pass
        
        # 关闭事件总线
        logger.info("🧹 关闭事件总线...")
        await event_bus.shutdown()

if __name__ == "__main__":
    try:
        # 设置事件循环策略（Windows兼容）
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        async def main():
            logger.info("🎬 开始LLM客户端测试")
            
            # 运行测试
            result = await test_llm_client()
            
            logger.info("=" * 50)
            logger.info(f"📊 测试结果: {'🎉 测试通过' if result else '❌ 测试失败'}")
            return result
        
        # 运行测试
        result = asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())