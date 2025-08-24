#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动聊天模块测试脚本 - 完全异步版本
"""

import sys
import os
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_auto_chat")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自动聊天模块和事件总线
from ai.auto_chat import AutoChatModule
from core.event_bus import EventBus

class MockLLMClient:
    """模拟LLM客户端"""
    def __init__(self):
        self.messages = []
    
    async def send_message(self, text):
        logger.info(f"🤖 MockLLM收到消息: {text}")
        # 模拟处理延迟
        await asyncio.sleep(0.5)
        
        # 模拟不同的回复
        responses = [
            "你好！我注意到你好像在忙别的事情呢~",
            "要不我们聊聊今天的天气吧？",
            "主人，你在做什么有趣的事情吗？",
            "感觉有点安静呢，要听个笑话吗？",
            "我在这里陪着你哦~"
        ]
        
        import random
        response = random.choice(responses)
        logger.info(f"🤖 MockLLM返回响应: {response}")
        return response

class MockTTSClient:
    """模拟TTS客户端 - 异步版本"""
    def __init__(self):
        self._active = False
        self._playback_task = None
    
    async def speak(self, text):
        """异步播放文本"""
        logger.info(f"🔊 MockTTS开始播放: {text}")
        self._active = True
        
        # 模拟播放时间（2秒）
        self._playback_task = asyncio.create_task(self._playback_simulation())
        await self._playback_task
    
    async def _playback_simulation(self):
        """模拟播放过程"""
        await asyncio.sleep(2)  # 模拟2秒播放时间
        self._active = False
        logger.info("🔇 MockTTS播放完成")
    
    async def is_active(self):
        """检查是否正在播放"""
        return self._active
    
    def stop_playback(self):
        """停止播放"""
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
        self._active = False

async def test_auto_chat():
    """测试自动聊天模块的基本功能"""
    # 创建配置和事件总线
    config = {
        "auto_chat": {
            "enabled": True,
            "interval": 2000,      # 2秒检查一次（测试用短间隔）
            "min_interval": 5000,  # 最小5秒触发一次
            "max_interval": 30000, # 最大30秒触发一次
            "idle_time": 4000      # 4秒无交互触发（测试用短时间）
        }
    }
    event_bus = EventBus()
    
    # 创建模拟客户端
    mock_llm = MockLLMClient()
    mock_tts = MockTTSClient()
    
    # 记录收到的自动对话
    auto_chat_requests = []
    auto_chat_responses = []
    
    # 创建事件来通知测试脚本
    request_received_event = asyncio.Event()
    response_received_event = asyncio.Event()
    
    # 自动对话请求处理函数
    async def handle_auto_chat_request(data):
        prompt = data.get("prompt", "")
        source = data.get("source", "unknown")
        logger.info(f"📨 收到自动对话请求 (来源: {source}): {prompt}")
        auto_chat_requests.append(prompt)
        request_received_event.set()
    
    # 自动对话响应处理函数
    async def handle_auto_chat_response(data):
        text = data.get("text", "")
        source = data.get("source", "unknown")
        logger.info(f"💬 收到自动对话响应 (来源: {source}): {text}")
        auto_chat_responses.append(text)
        response_received_event.set()
        
        # 模拟TTS播放响应
        if mock_tts:
            await mock_tts.speak(text)
    
    auto_chat = None
    try:
        # 订阅事件（注意需要await）
        await event_bus.subscribe("auto_chat_request", handle_auto_chat_request)
        await event_bus.subscribe("auto_chat_response", handle_auto_chat_response)
        
        # 创建自动聊天模块
        logger.info("🚀 创建自动聊天模块...")
        auto_chat = AutoChatModule(config, event_bus, mock_llm, mock_tts)
        
        # 启动自动聊天（注意需要await）
        logger.info("▶️ 启动自动聊天...")
        await auto_chat.start()
        
        print("\n" + "="*60)
        print("🧪 自动聊天模块测试")
        print("="*60)
        
        # 测试1: 基本空闲触发
        logger.info("🧪 测试1: 基本空闲触发")
        print("模拟用户交互，然后等待空闲触发...")
        
        # 模拟用户交互（注意需要await）
        await event_bus.publish("user_speaking", {"is_speaking": True})
        await asyncio.sleep(0.5)
        await event_bus.publish("user_speaking", {"is_speaking": False})
        
        # 等待自动聊天触发
        logger.info("⏳ 等待自动聊天触发（应该在4秒左右）...")
        
        try:
            await asyncio.wait_for(request_received_event.wait(), timeout=8.0)
            logger.info("✅ 测试1通过：收到自动对话请求")
        except asyncio.TimeoutError:
            logger.error("❌ 测试1失败：超时未收到自动对话请求")
            return False
        
        # 等待响应
        try:
            await asyncio.wait_for(response_received_event.wait(), timeout=5.0)
            logger.info("✅ 收到自动对话响应")
        except asyncio.TimeoutError:
            logger.warning("⚠️ 超时未收到自动对话响应")
        
        # 测试2: TTS播放期间不触发
        logger.info("\n🧪 测试2: TTS播放期间不触发")
        print("模拟TTS播放期间，应该不触发自动对话...")
        
        # 重置事件
        request_received_event.clear()
        auto_chat_requests.clear()
        
        # 模拟TTS播放（注意需要await）
        await event_bus.publish("tts_start", {})
        await asyncio.sleep(1)
        
        # 在TTS播放期间等待一段时间，不应该触发自动对话
        try:
            await asyncio.wait_for(request_received_event.wait(), timeout=3.0)
            logger.warning("⚠️ 测试2部分失败：TTS播放期间仍触发了自动对话")
        except asyncio.TimeoutError:
            logger.info("✅ 测试2通过：TTS播放期间正确抑制了自动对话")
        
        # 结束TTS播放
        await event_bus.publish("tts_end", {})
        
        # 测试3: 用户说话期间不触发
        logger.info("\n🧪 测试3: 用户说话期间不触发")
        print("模拟用户说话期间，应该不触发自动对话...")
        
        # 重置事件
        request_received_event.clear()
        auto_chat_requests.clear()
        
        # 模拟用户一直在说话
        await event_bus.publish("user_speaking", {"is_speaking": True})
        
        # 等待一段时间，不应该触发自动对话
        try:
            await asyncio.wait_for(request_received_event.wait(), timeout=3.0)
            logger.warning("⚠️ 测试3部分失败：用户说话期间仍触发了自动对话")
        except asyncio.TimeoutError:
            logger.info("✅ 测试3通过：用户说话期间正确抑制了自动对话")
        
        # 用户停止说话
        await event_bus.publish("user_speaking", {"is_speaking": False})
        
        # 测试4: 再次空闲触发
        logger.info("\n🧪 测试4: 再次空闲触发")
        print("用户停止说话后，再次等待空闲触发...")
        
        # 重置事件
        request_received_event.clear()
        response_received_event.clear()
        
        # 等待自动聊天再次触发
        try:
            await asyncio.wait_for(request_received_event.wait(), timeout=8.0)
            logger.info("✅ 测试4通过：再次成功触发自动对话")
        except asyncio.TimeoutError:
            logger.warning("⚠️ 测试4失败：超时未再次触发自动对话")
        
        # 显示测试结果
        print("\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)
        print(f"收到的自动对话请求数: {len(auto_chat_requests)}")
        print(f"收到的自动对话响应数: {len(auto_chat_responses)}")
        
        if auto_chat_requests:
            print("\n自动对话请求:")
            for i, request in enumerate(auto_chat_requests, 1):
                print(f"  {i}. {request}")
        
        if auto_chat_responses:
            print("\n自动对话响应:")
            for i, response in enumerate(auto_chat_responses, 1):
                print(f"  {i}. {response}")
        
        # 停止自动聊天（注意需要await）
        logger.info("\n🛑 停止自动聊天...")
        await auto_chat.stop()
        
        # 停止模拟TTS
        mock_tts.stop_playback()
        
        # 等待一会儿，确保所有处理都已完成
        await asyncio.sleep(1)
        
        logger.info("✅ 自动聊天模块测试完成")
        
        # 如果收到了至少一个请求，则测试通过
        success = len(auto_chat_requests) > 0
        return success
        
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 确保资源被清理
        if auto_chat:
            try:
                await auto_chat.stop()
            except Exception as e:
                logger.warning(f"清理自动聊天模块时出错: {e}")
        
        # 关闭事件总线
        logger.info("🧹 关闭事件总线...")
        await event_bus.shutdown()

if __name__ == "__main__":
    try:
        # 设置事件循环策略（Windows兼容）
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        async def main():
            logger.info("🎬 开始自动聊天模块测试")
            
            # 运行测试
            result = await test_auto_chat()
            
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