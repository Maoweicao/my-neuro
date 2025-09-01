#!/usr/bin/env python3
"""
豆包TTS配置验证脚本
验证APP ID和Access Token是否正确
"""

import asyncio
import aiohttp
import json
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_doubao_auth():
    """测试豆包TTS认证"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        app_id = config['tts']['doubao_app_id']
        access_token = config['tts']['doubao_access_token']

        logger.info("=== 豆包TTS认证测试 ===")
        logger.info(f"APP ID: {app_id}")
        logger.info(f"Access Token: {access_token[:20]}...")

        # 测试豆包TTS API
        api_url = "https://openspeech.bytedance.com/api/v1/tts"

        headers = {
            "Authorization": f"Bearer;{access_token}",
            "Content-Type": "application/json"
        }

        # 构建一个简单的测试请求
        test_data = {
            "app": {
                "appid": app_id,
                "token": access_token,
                "cluster": "volcano_tts"
            },
            "user": {
                "uid": "test_user_123"
            },
            "audio": {
                "voice_type": "zh_female_qingxinnvsheng_mars_bigtts",
                "encoding": "wav"
            },
            "request": {
                "reqid": "test_req_123",
                "text": "测试",
                "operation": "query",
                "with_timestamp": 1,
                "extra_param": '{"disable_markdown_filter": false}'
            }
        }

        logger.info("发送认证测试请求...")

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=test_data) as response:
                logger.info(f"HTTP状态码: {response.status}")

                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 认证成功! 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 认证失败: {response.status}")
                    logger.error(f"错误详情: {error_text}")

                    # 分析常见错误
                    if response.status == 401:
                        logger.error("💡 建议: 检查Access Token是否正确")
                    elif response.status == 403:
                        logger.error("💡 建议: 检查APP ID是否有权限，或资源是否被授权")
                    elif response.status == 400:
                        logger.error("💡 建议: 检查请求参数格式")

                    return False

    except Exception as e:
        logger.error(f"❌ 认证测试失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 开始豆包TTS认证测试")

    success = await test_doubao_auth()

    if success:
        logger.info("\n🎊 豆包TTS认证测试通过！API配置正确。")
    else:
        logger.error("\n💥 豆包TTS认证测试失败")
        logger.info("🔧 请检查以下配置:")
        logger.info("   1. APP ID是否正确")
        logger.info("   2. Access Token是否有效")
        logger.info("   3. 应用是否有TTS权限")
        logger.info("   4. 网络连接是否正常")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 认证测试被用户中断")
    except Exception as e:
        logger.error(f"💥 测试过程中发生意外错误: {e}")
