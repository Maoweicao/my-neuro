#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络连接测试脚本
"""

import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_network_connection():
    """测试网络连接"""
    try:
        logger.info("测试连接到豆包服务器...")

        # 测试HTTPS连接
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://openspeech.bytedance.com', timeout=10) as resp:
                    logger.info(f"HTTPS连接成功，状态码: {resp.status}")
            except Exception as e:
                logger.error(f"HTTPS连接失败: {e}")

        # 测试WebSocket连接（不发送认证头）
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream',
                    timeout=10
                ) as ws:
                    logger.info("WebSocket连接成功")
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")

    except Exception as e:
        logger.error(f"网络测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_network_connection())
