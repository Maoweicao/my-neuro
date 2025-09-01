#!/usr/bin/env python3
"""
豆包TTS功能测试脚本
测试豆包TTS的完整功能
"""

import asyncio
import logging
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.tts_client import TTSClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_doubao_tts():
    """测试豆包TTS功能"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info("=== 豆包TTS功能测试 ===")
        logger.info(f"TTS类型: {config['tts']['tts_type']}")
        logger.info(f"豆包APP ID: {config['tts']['doubao_app_id']}")
        logger.info(f"豆包Resource ID: {config['tts'].get('doubao_resource_id', 'N/A')}")
        logger.info(f"豆包音色: {config['tts']['doubao_voice_type']}")
        logger.info(f"豆包编码: {config['tts']['doubao_encoding']}")
        logger.info(f"豆包API URL: {config['tts'].get('doubao_url', 'N/A')}")

        # 创建TTS客户端
        tts_client = TTSClient(config)
        logger.info("TTS客户端创建成功")

        # 检查豆包客户端是否正确初始化
        if tts_client.tts_client and tts_client.tts_client.get('type') == 'doubao':
            logger.info("✅ 豆包TTS客户端初始化成功")
            logger.info(f"   APP ID: {tts_client.tts_client.get('app_id', 'N/A')}")
            logger.info(f"   Access Token: {tts_client.tts_client.get('access_token', 'N/A')[:10]}...")
            logger.info(f"   Resource ID: {tts_client.tts_client.get('resource_id', 'N/A')}")
            logger.info(f"   音色类型: {tts_client.tts_client.get('voice_type', 'N/A')}")
            logger.info(f"   编码格式: {tts_client.tts_client.get('encoding', 'N/A')}")
            logger.info(f"   API URL: {tts_client.tts_client.get('api_url', 'N/A')}")
        else:
            logger.error("❌ 豆包TTS客户端初始化失败")
            return False

        # 测试文本转换
        test_text = "你好，这是一个豆包TTS功能测试。"
        logger.info(f"正在测试文本转换: '{test_text}'")

        # 调用转换方法
        audio_data = await tts_client._convert_with_doubao(test_text)

        if audio_data:
            logger.info(f"✅ 豆包TTS转换成功，音频大小: {len(audio_data)} bytes")

            # 保存音频文件用于验证
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "doubao_test.ogg")

            with open(output_file, 'wb') as f:
                f.write(audio_data)

            logger.info(f"🎵 音频文件已保存: {output_file}")
            logger.info("🎉 豆包TTS功能测试通过！")

            return True
        else:
            logger.error("❌ 豆包TTS转换失败")
            return False

    except Exception as e:
        logger.error(f"❌ 豆包TTS测试失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False
    finally:
        # 清理资源
        if 'tts_client' in locals():
            await tts_client.stop()

async def main():
    """主函数"""
    logger.info("🚀 开始豆包TTS功能测试")

    success = await test_doubao_tts()

    if success:
        logger.info("\n🎊 豆包TTS功能测试全部通过！")
        logger.info("💡 现在您可以在主应用程序中使用豆包TTS了")
    else:
        logger.error("\n💥 豆包TTS功能测试失败")
        logger.info("🔧 请检查配置和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 测试被用户中断")
    except Exception as e:
        logger.error(f"💥 测试过程中发生意外错误: {e}")
