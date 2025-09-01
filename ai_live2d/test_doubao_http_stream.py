#!/usr/bin/env python3
"""
豆包TTS HTTP流式API测试脚本
测试新的HTTP单向流式接口
"""

import asyncio
import logging
import sys
import os
import json
import aiohttp
import base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_doubao_http_stream():
    """测试豆包TTS HTTP流式API"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info("=== 豆包TTS HTTP流式API测试 ===")

        # 获取配置参数
        app_id = config['tts'].get('doubao_app_id', '')
        access_token = config['tts'].get('doubao_access_token', '')
        resource_id = config['tts'].get('doubao_resource_id', '')
        voice_type = config['tts'].get('doubao_voice_type', '')
        encoding = config['tts'].get('doubao_encoding', 'wav')

        if not app_id or not access_token:
            logger.error("❌ APP ID或Access Token未配置")
            return False

        logger.info(f"APP ID: {app_id}")
        logger.info(f"Resource ID: {resource_id}")
        logger.info(f"音色类型: {voice_type}")
        logger.info(f"编码格式: {encoding}")

        # API URL
        api_url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

        # 构建请求头
        headers = {
            "X-Api-App-Id": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": resource_id,
            "X-Api-App-Key": "aGjiRDfUWi",
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

        # 测试文本
        test_text = "你好，这是一个豆包TTS HTTP流式API测试。"
        logger.info(f"测试文本: {test_text}")

        # 构建请求体
        request_data = {
            "user": {
                "uid": "doubao_test_user"
            },
            "req_params": {
                "text": test_text,
                "speaker": voice_type,
                "audio_params": {
                    "format": encoding,
                    "sample_rate": 24000,
                    "enable_timestamp": True
                },
                "additions": json.dumps({
                    "explicit_language": "zh",
                    "disable_markdown_filter": True,
                    "enable_timestamp": True
                })
            }
        }

        logger.info("发送HTTP流式请求...")

        # 用于存储音频数据
        audio_data = bytearray()

        # 发送POST请求并处理流式响应
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=request_data) as response:
                logger.info(f"响应状态码: {response.status}")
                logger.info(f"响应头: {dict(response.headers)}")

                if response.status == 200:
                    # 处理流式响应
                    async for line in response.content:
                        if not line:
                            continue

                        try:
                            # 解析JSON数据
                            line_str = line.decode('utf-8').strip()
                            if not line_str:
                                continue

                            data = json.loads(line_str)
                            logger.debug(f"流式数据: {data}")

                            # 处理音频数据
                            if data.get("code") == 0 and "data" in data and data["data"]:
                                chunk_audio = base64.b64decode(data["data"])
                                audio_data.extend(chunk_audio)
                                logger.info(f"收到音频块，大小: {len(chunk_audio)} bytes")

                            # 处理句子信息
                            elif data.get("code") == 0 and "sentence" in data and data["sentence"]:
                                logger.info(f"句子信息: {data['sentence']}")

                            # 处理结束标记
                            elif data.get("code") == 20000000:
                                logger.info("流式响应结束")
                                break

                            # 处理错误
                            elif data.get("code", 0) > 0:
                                logger.error(f"API错误: {data}")
                                return False

                        except json.JSONDecodeError as e:
                            logger.warning(f"解析JSON失败: {e}, 原始数据: {line_str}")
                            continue
                        except Exception as e:
                            logger.error(f"处理流式数据出错: {e}")
                            continue

                    # 检查是否收到了音频数据
                    if audio_data:
                        logger.info(f"✅ 合成成功，音频总大小: {len(audio_data)} bytes")

                        # 保存音频文件
                        output_dir = "test_output"
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, "doubao_http_stream_test.ogg")

                        with open(output_file, 'wb') as f:
                            f.write(bytes(audio_data))

                        logger.info(f"🎵 音频文件已保存: {output_file}")
                        logger.info("🎉 豆包TTS HTTP流式API测试通过！")

                        return True
                    else:
                        logger.error("❌ 未收到音频数据")
                        return False

                else:
                    logger.error(f"❌ HTTP请求失败: {response.status}")
                    error_text = await response.text()
                    logger.error(f"错误详情: {error_text}")
                    return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 开始豆包TTS HTTP流式API测试")

    success = await test_doubao_http_stream()

    if success:
        logger.info("\n🎊 豆包TTS HTTP流式API测试全部通过！")
        logger.info("💡 新的HTTP流式接口工作正常")
    else:
        logger.error("\n💥 豆包TTS HTTP流式API测试失败")
        logger.info("🔧 请检查配置参数和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 测试被用户中断")
