#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SAUC协议的Doubao ASR客户端
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.asr_client import DoubaoASRClient
from utils.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_sauc_asr():
    """测试SAUC协议的ASR功能"""
    try:
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.load()

        # 从配置中提取豆包ASR参数
        asr_config = config.get("asr", {})

        # 创建ASR客户端
        asr_client = DoubaoASRClient(
            appid=asr_config.get("doubao_appid", ""),
            token=asr_config.get("doubao_token", ""),
            cluster=asr_config.get("doubao_cluster", "volcano_asr"),
            ws_url=asr_config.get("doubao_ws_url", ""),
            language=asr_config.get("doubao_language", "zh-CN"),
            format=asr_config.get("doubao_format", "wav"),
            sample_rate=asr_config.get("doubao_sample_rate", 16000),
            seg_duration=asr_config.get("doubao_seg_duration", 15000),
            resource_id=asr_config.get("doubao_resource_id", "volc.bigasr.sauc.duration")
        )

        # 使用真实的WAV文件进行测试
        wav_file_path = r"f:\my-neuro\ai_live2d\voice\volcengine_unidirectional_stream_demo\zh_female_cancan_mars_bigtts.wav"
        
        try:
            with open(wav_file_path, 'rb') as f:
                audio_bytes = f.read()
            logger.info(f"成功加载WAV文件: {wav_file_path}, 大小: {len(audio_bytes)} bytes")
        except FileNotFoundError:
            logger.warning(f"WAV文件不存在: {wav_file_path}，使用生成的测试音频")
            # 生成测试音频数据（模拟音频流）
            # 这里生成一个简单的WAV文件
            import numpy as np
            import io
            import wave
            import struct

            # 生成1秒的16kHz音频数据
            sample_rate = 16000
            duration = 1.0
            frequency = 440  # A4音符

            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(frequency * 2 * np.pi * t)

            # 转换为16位PCM
            audio_data = (audio_data * 32767).astype(np.int16)

            # 创建标准WAV文件
            buffer = io.BytesIO()

            # WAV文件头
            buffer.write(b'RIFF')  # ChunkID
            buffer.write(struct.pack('<I', 36 + len(audio_data) * 2))  # ChunkSize
            buffer.write(b'WAVE')  # Format

            # fmt子块
            buffer.write(b'fmt ')  # Subchunk1ID
            buffer.write(struct.pack('<I', 16))  # Subchunk1Size
            buffer.write(struct.pack('<H', 1))   # AudioFormat (PCM)
            buffer.write(struct.pack('<H', 1))   # NumChannels
            buffer.write(struct.pack('<I', sample_rate))  # SampleRate
            buffer.write(struct.pack('<I', sample_rate * 1 * 2))  # ByteRate
            buffer.write(struct.pack('<H', 1 * 2))  # BlockAlign
            buffer.write(struct.pack('<H', 16))  # BitsPerSample

            # data子块
            buffer.write(b'data')  # Subchunk2ID
            buffer.write(struct.pack('<I', len(audio_data) * 2))  # Subchunk2Size
            buffer.write(audio_data.tobytes())  # Data

            audio_bytes = buffer.getvalue()

        logger.info(f"测试音频数据大小: {len(audio_bytes)} bytes")

        # 测试ASR识别
        logger.info("开始测试SAUC协议ASR识别...")

        result = await asr_client.recognize_audio(audio_bytes)

        logger.info(f"识别结果: {result}")

        if result and 'text' in result:
            logger.info(f"识别文本: {result['text']}")
        else:
            logger.warning("未获取到识别文本")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sauc_asr())
