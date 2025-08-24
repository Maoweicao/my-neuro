#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS客户端测试脚本 - 修正版
适配异步TTS客户端
"""

import sys
import os
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_tts_client")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入TTS客户端和事件总线
from voice.tts_client import TTSClient
from core.event_bus import EventBus

async def test_tts_client():
    """测试TTS客户端的基本功能"""
    # 创建配置和事件总线
    config = {
        "tts": {
            "url": "http://localhost:6006/v3",  # 注意这里加了 /v3 路径
            "language": "zh"
        }
    }
    event_bus = EventBus()
    
    # 异步回调函数 - 注意这里改成了async！
    async def on_audio_data(value):
        logger.info(f"🔊 音频数据回调: {value}")
    
    async def on_text_update(text):
        logger.info(f"📝 文本更新回调: {text}")
    
    # 事件总线订阅回调
    async def on_tts_error(data):
        logger.error(f"❌ TTS错误事件: {data}")
    
    async def on_start_lip_sync(data):
        logger.info(f"👄 开始唇形同步事件")

    tts_client = None
    try:
        # 创建TTS客户端
        logger.info("🚀 创建TTS客户端...")
        tts_client = TTSClient(config, event_bus)
        
        # 设置回调函数
        tts_client.set_callbacks(
            on_audio_data=on_audio_data,
            on_text_update=on_text_update
        )
        
        # 订阅事件总线事件
        await event_bus.subscribe("tts_error", on_tts_error)
        await event_bus.subscribe("start_lip_sync", on_start_lip_sync)
        
        # 启动TTS客户端 - 这个很重要！
        logger.info("▶️ 启动TTS客户端...")
        await tts_client.start()
        
        # 测试1: 基本播放功能
        logger.info("=" * 50)
        logger.info("🧪 测试1: 基本播放功能")
        test_text = "你好，这是一个TTS客户端测试上的数据发送到发货的手机号多少。（说就是纠结啊）我会说话了！"
        logger.info(f"📢 测试播放文本: {test_text}")
        
        await tts_client.speak(test_text)
        
        # 等待播放完成
        logger.info("⏳ 等待播放完成...")
        while (await tts_client.is_active())[0]:
            print(await tts_client.is_active())
            await asyncio.sleep(0.5)
            logger.debug("播放中...")
        
        logger.info("✅ 基本播放测试完成")
        
        # 测试2: 流式文本
        logger.info("=" * 50)
        logger.info("🧪 测试2: 流式文本")
        await tts_client.reset()  # 重置状态
        
        await tts_client.add_streaming_text("这是（sansaj）流式")
        await asyncio.sleep(0.5)  # 模拟流式间隔
        await tts_client.add_streaming_text("文本(sscjshjj)的")
        await asyncio.sleep(0.5)
        await tts_client.add_streaming_text("测试。")
        await asyncio.sleep(0.5)
        await tts_client.add_streaming_text("很酷对吧？")
        
        # 等待流式播放完成
        logger.info("⏳ 等待流式播放完成...")
        while (await tts_client.is_active())[0]:
            print(await tts_client.is_active())
            await asyncio.sleep(0.5)
            logger.debug("流式播放中...")
        
        logger.info("✅ 流式文本测试完成")
        
        # 测试3: 停止功能
        logger.info("=" * 50)
        logger.info("🧪 测试3: 停止功能")
        
        # 开始一个长文本播放
        long_text = "这是一段很长的文本，用来测试停止功能。它应该会被中途打断。"
        await tts_client.speak(long_text)
        
        # 等待一点时间，然后停止
        await asyncio.sleep(2)
        logger.info("⏹️ 停止播放...")
        await tts_client.stop()
        
        logger.info("✅ 停止功能测试完成")
        
        # 测试4: 上下文管理器
        logger.info("=" * 50)
        logger.info("🧪 测试4: 上下文管理器")
        
        async with TTSClient(config, event_bus) as ctx_tts:
            ctx_tts.set_callbacks(on_text_update=on_text_update)
            await ctx_tts.speak("这是上下文管理器的测试。")
            
            while (await ctx_tts.is_active())[0]:
                await asyncio.sleep(0.5)
        
        logger.info("✅ 上下文管理器测试完成")
        
        logger.info("🎉 所有TTS客户端测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 清理资源
        if tts_client:
            logger.info("🧹 清理TTS客户端...")
            await tts_client.stop()
        
        logger.info("🧹 关闭事件总线...")
        await event_bus.shutdown()

async def test_health_check():
    """测试TTS服务健康检查"""
    import aiohttp
    
    # 使用完整的TTS端点URL
    tts_url = "http://localhost:6006/v3"
    logger.info(f"🏥 检查TTS服务健康状态: {tts_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 发送一个简单的POST请求测试TTS端点
            test_data = {
                "text": "测试",
                "text_language": "zh"
            }
            
            async with session.post(
                tts_url, 
                json=test_data,
                timeout=10
            ) as response:
                if response.status == 200:
                    logger.info("✅ TTS服务运行正常")
                    return True
                else:
                    logger.warning(f"⚠️ TTS服务响应异常: {response.status}")
                    # 尝试读取错误信息
                    try:
                        error_text = await response.text()
                        logger.warning(f"错误详情: {error_text}")
                    except:
                        pass
                    return False
    except asyncio.TimeoutError:
        logger.error("❌ TTS服务连接超时")
        return False
    except Exception as e:
        logger.error(f"❌ TTS服务连接失败: {e}")
        logger.warning("💡 请确保TTS服务正在运行在 http://127.0.0.1:5000")
        return False

if __name__ == "__main__":
    try:
        # 设置事件循环策略（Windows兼容）
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        async def main():
            logger.info("🎬 开始TTS客户端测试")
            
            # 先检查TTS服务
            if not await test_health_check():
                logger.error("❌ TTS服务不可用，跳过测试")
                return False
            
            # 运行主测试
            result = await test_tts_client()
            
            logger.info("=" * 50)
            logger.info(f"📊 测试结果: {'🎉 全部通过' if result else '❌ 测试失败'}")
            return result
        
        # 运行测试
        result = asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())