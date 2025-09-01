#!/usr/bin/env python3
"""
豆包TTS WebSocket流式API测试脚本
测试新的WebSocket单向流式接口
"""

import asyncio
import logging
import sys
import os
import json
import websockets
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入协议模块
try:
    from voice.volcengine_unidirectional_stream_demo.protocols import (
        EventType, MsgType, full_client_request, receive_message
    )
    PROTOCOLS_AVAILABLE = True
    logger.info("✅ 豆包TTS协议模块加载成功")
except ImportError as e:
    PROTOCOLS_AVAILABLE = False
    logger.error(f"❌ 豆包TTS协议模块加载失败: {e}")
    sys.exit(1)

def get_resource_id(voice_type: str) -> str:
    """根据音色类型获取资源ID"""
    # 根据豆包TTS官方文档，不同的音色类型对应不同的资源ID
    if voice_type.startswith("S_"):
        return "volc.megatts.default"
    elif voice_type.startswith("zh_"):
        return "volc.btts.voice"  # 中文音色使用这个资源ID
    elif voice_type.startswith("en_"):
        return "volc.btts.voice.en"  # 英文音色使用这个资源ID
    else:
        return "volc.service_type.10029"  # 默认值

async def test_doubao_websocket_stream():
    """测试豆包TTS WebSocket流式API"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info("=== 豆包TTS WebSocket流式API测试 ===")

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
        logger.info(f"Resource ID: {resource_id or get_resource_id(voice_type)}")
        logger.info(f"音色类型: {voice_type}")
        logger.info(f"编码格式: {encoding}")

        # WebSocket端点
        websocket_url = "wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream"

        # 构建请求头
        headers = {
            "X-Api-App-Key": app_id,  # WebSocket版本使用App-Key
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": resource_id or get_resource_id(voice_type),
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        logger.info(f"连接WebSocket: {websocket_url}")
        logger.info(f"请求头: {headers}")

        # 测试文本
        test_text = "你好，我是火山引擎的语音合成服务。这是一个美好的旅程。"
        logger.info(f"测试文本: {test_text}")

        # 连接WebSocket
        websocket = await websockets.connect(
            websocket_url,
            additional_headers=headers,
            max_size=10 * 1024 * 1024
        )

        try:
            # 记录连接日志
            logger.info(f"WebSocket连接成功")

            # 准备请求数据
            request_data = {
                "user": {
                    "uid": str(uuid.uuid4()),
                },
                "req_params": {
                    "speaker": voice_type,
                    "audio_params": {
                        "format": encoding,
                        "sample_rate": 24000,
                        "enable_timestamp": True,
                    },
                    "text": test_text,
                    "additions": json.dumps({
                        "disable_markdown_filter": False,
                    }),
                },
            }

            # 发送请求
            await full_client_request(websocket, json.dumps(request_data).encode())
            logger.info("发送TTS请求...")

            # 接收音频数据
            audio_data = bytearray()
            while True:
                msg = await receive_message(websocket)

                if msg.type == MsgType.FullServerResponse:
                    if msg.event == EventType.SessionFinished:
                        logger.info("会话结束")
                        break
                elif msg.type == MsgType.AudioOnlyServer:
                    audio_data.extend(msg.payload)
                    logger.info(f"收到音频块，大小: {len(msg.payload)} bytes")
                else:
                    logger.error(f"TTS转换失败: {msg}")
                    return False

            # 检查是否收到了音频数据
            if audio_data:
                logger.info(f"✅ 合成成功，音频总大小: {len(audio_data)} bytes")

                # 保存音频文件
                output_dir = "test_output"
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, "doubao_websocket_test.ogg")

                with open(output_file, 'wb') as f:
                    f.write(bytes(audio_data))

                logger.info(f"🎵 音频文件已保存: {output_file}")
                logger.info("🎉 豆包TTS WebSocket流式API测试通过！")

                return True
            else:
                logger.error("❌ 未收到音频数据")
                return False

        finally:
            await websocket.close()
            logger.info("WebSocket连接已关闭")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 开始豆包TTS WebSocket流式API测试")

    success = await test_doubao_websocket_stream()

    if success:
        logger.info("\n🎊 豆包TTS WebSocket流式API测试全部通过！")
        logger.info("💡 新的WebSocket流式接口工作正常")
    else:
        logger.error("\n💥 豆包TTS WebSocket流式API测试失败")
        logger.info("🔧 请检查配置参数和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 测试被用户中断")
