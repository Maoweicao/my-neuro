#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ASR客户端测试脚本 - 异步版本
"""

import sys
import os
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 调整websockets库的日志级别
logging.getLogger('websockets').setLevel(logging.WARNING)
logger = logging.getLogger("test_asr_client")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入ASR客户端
from voice.asr_client import ASRClient
from core.event_bus import EventBus

async def on_speech_recognized(text):
    """语音识别回调 - 异步版本"""
    logger.info(f"🎙️ 识别到语音: '{text}'")
    print(f"\n✅ 用户说: {text}\n")

async def on_user_speaking(data):
    """用户说话状态回调 - 改为异步"""
    is_speaking = data.get("is_speaking", False)
    if is_speaking:
        print("🎤", end="", flush=True)  # 显示用户正在说话的指示符
    else:
        print("", end="", flush=True)

async def test_asr_client():
    """测试ASR客户端的基本功能"""
    # 创建配置和事件总线
    config = {
        "asr": {
            "vad_url": "ws://localhost:6006/v1/ws/vad",
            "asr_url": "http://localhost:6006/v1/upload_audio"
        }
    }
    event_bus = EventBus()
    asr_client = None
    
    try:
        
        
        logger.info("🚀 创建ASR客户端...")
        
        # 订阅事件（注意这里需要await）
        await event_bus.subscribe("user_speaking", on_user_speaking)
        
        # 创建ASR客户端
        asr_client = ASRClient(config, event_bus)
        
        # 设置回调
        asr_client.set_on_speech_recognized(on_speech_recognized)
        
        # 启动ASR客户端（注意方法名变了）
        logger.info("▶️ 启动ASR客户端...")
        await asr_client.start()  # 之前是start_recording()
        
        print("\n" + "="*50)
        print("🎤 语音识别测试")
        print("="*50)
        print("请对着麦克风说话...")
        print("程序会自动检测语音并进行识别")
        print("测试将在20秒后自动结束")
        print("正在录音中... 🎙️")
        print("说话指示符: 🎤")
        print("-"*50)
        
        # 等待20秒进行测试
        for i in range(20):
            await asyncio.sleep(1)
            if i % 5 == 0 and i > 0:
                print(f"\n⏱️ 还剩 {20-i} 秒...")
        
        print("\n" + "="*50)
        print("⏹️ 测试结束，停止录音")
        
        # 停止ASR客户端（注意方法名和需要await）
        logger.info("🛑 停止ASR客户端...")
        await asr_client.stop()  # 之前是stop_recording()
        
        logger.info("✅ ASR客户端测试完成")
        return True
        
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 确保资源被清理（异步清理）
        if asr_client:
            try:
                await asr_client.stop()
            except Exception as e:
                logger.warning(f"清理ASR客户端时出错: {e}")
        
        # 关闭事件总线
        logger.info("🧹 关闭事件总线...")
        await event_bus.shutdown()

if __name__ == "__main__":
    try:
        # 设置事件循环策略（Windows兼容）
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        async def main():
            logger.info("🎬 开始ASR客户端测试")
            
            # 运行测试
            result = await test_asr_client()
            
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