#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视觉客户端测试脚本 - 适配优化版本
"""

import sys
import os
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_vision_client")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入视觉客户端和事件总线
from vision.vision_client import VisionClient
from core.event_bus import EventBus

async def test_vision_client():
    """测试视觉客户端的基本功能 - 适配优化版本"""
    # 创建配置和事件总线
    config = {
        "vision": {
            "enabled": True,
            "check_url": "http://localhost:6006/v4/check",
            "screenshot_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_screenshot.jpg")
        }
    }
    event_bus = EventBus()
    
    # 截图事件回调
    async def on_screenshot_taken(data):
        path = data.get("path", "")
        logger.info(f"📸 截图事件: {path}")
    
    try:
        # 订阅事件 - 使用异步方式
        await event_bus.subscribe("screenshot_taken", on_screenshot_taken)
        
        # 创建视觉客户端 - 使用异步上下文管理器
        async with VisionClient(config, event_bus) as vision_client:
            # 模拟API响应，实现一个假的check_vision_needed方法
            async def mock_check_vision_needed(text):
                logger.info(f"🔍 模拟检查是否需要截图: {text}")
                # 简单规则：包含"看"或"截图"的文本需要截图
                return "看" in text or "截图" in text
            
            # 替换原方法为模拟方法
            vision_client.check_vision_needed = mock_check_vision_needed
            
            # 测试检查不需要截图的文本
            logger.info("🧪 测试不需要截图的文本")
            result = await vision_client.check_vision_needed("这是一条普通消息")
            logger.info(f"📊 检查结果: {result}")
            
            # 测试检查需要截图的文本
            logger.info("🧪 测试需要截图的文本")
            result = await vision_client.check_vision_needed("请看一下我的桌面")
            logger.info(f"📊 检查结果: {result}")
            
            # 测试截图功能
            logger.info("📸 测试截图功能")
            screenshot_path = await vision_client.take_screenshot()
            
            if screenshot_path and os.path.exists(screenshot_path):
                logger.info(f"✅ 截图成功: {screenshot_path}")
                
                # 测试图片转base64
                logger.info("🔢 测试图片转base64")
                base64_data = await vision_client.image_to_base64(screenshot_path)
                logger.info(f"📐 Base64数据长度: {len(base64_data) if base64_data else 0}")
                
                # 清理截图
                try:
                    os.remove(screenshot_path)
                    logger.info(f"🧹 已删除测试截图: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"⚠️ 删除测试截图失败: {e}")
            else:
                logger.warning("❌ 截图失败或文件不存在")
        
        logger.info("🎉 视觉客户端测试完成")
        return True
        
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        # 设置事件循环策略
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 运行测试
        result = asyncio.run(test_vision_client())
        logger.info(f"📊 测试结果: {'✅ 通过' if result else '❌ 失败'}")
    except Exception as e:
        logger.error(f"💥 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())