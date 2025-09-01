#!/usr/bin/env python3
"""
豆包ASR测试脚本
"""

import asyncio
import sys
import os
import json
import wave
import numpy as np
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.asr_client import DoubaoASRClient

logger = logging.getLogger(__name__)

async def test_doubao_asr():
    """测试豆包ASR功能"""
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info("=== 豆包ASR测试 ===")

        # 获取配置参数
        asr_config = config.get('asr', {})
        appid = asr_config.get('doubao_appid', '')
        token = asr_config.get('doubao_token', '')
        cluster = asr_config.get('doubao_cluster', 'volcano_tts')
        ws_url = asr_config.get('doubao_ws_url', 'wss://openspeech.bytedance.com/api/v2/asr')
        language = asr_config.get('doubao_language', 'zh-CN')
        format_type = asr_config.get('doubao_format', 'wav')
        sample_rate = asr_config.get('doubao_sample_rate', 16000)
        seg_duration = asr_config.get('doubao_seg_duration', 15000)
        resource_id = asr_config.get('doubao_resource_id', 'volc.service_type.10032')

        if not appid or not token:
            logger.error("❌ 豆包ASR APPID或Token未配置")
            return False

        logger.info(f"APPID: {appid}")
        logger.info(f"Cluster: {cluster}")
        logger.info(f"Language: {language}")
        logger.info(f"Format: {format_type}")
        logger.info(f"Sample Rate: {sample_rate}")

        # 创建豆包ASR客户端
        doubao_client = DoubaoASRClient(
            appid=appid,
            token=token,
            cluster=cluster,
            ws_url=ws_url,
            language=language,
            format=format_type,
            sample_rate=sample_rate,
            seg_duration=seg_duration,
            resource_id=resource_id
        )

        # 生成测试音频（1秒的正弦波）
        logger.info("生成测试音频...")
        duration = 2  # 2秒
        frequency = 440  # 440Hz
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(frequency * 2 * np.pi * t)
        audio_data = (audio_data * 32767).astype(np.int16)

        # 转换为WAV格式
        import io
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()
        logger.info(f"测试音频大小: {len(wav_data)} bytes")

        # 调用豆包ASR进行识别
        logger.info("开始语音识别...")
        result = await doubao_client.recognize_audio(wav_data)

        if result:
            logger.info(f"识别结果: {result}")
            
            if 'payload_msg' in result:
                payload = result['payload_msg']
                if payload.get('code') == doubao_client.success_code:
                    logger.info("✅ 豆包ASR测试成功！")
                    return True
                else:
                    logger.error(f"❌ 豆包ASR识别失败: {payload}")
            else:
                logger.error(f"❌ 豆包ASR响应异常: {result}")
        else:
            logger.error("❌ 豆包ASR未返回结果")

        return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 开始豆包ASR测试")

    success = await test_doubao_asr()

    if success:
        logger.info("\n🎊 豆包ASR测试全部通过！")
        logger.info("💡 豆包ASR流式识别功能正常")
    else:
        logger.error("\n💥 豆包ASR测试失败")
        logger.info("🔧 请检查配置参数和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 测试被用户中断")
