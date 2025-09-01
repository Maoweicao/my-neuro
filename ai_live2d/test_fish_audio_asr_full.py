#!/usr/bin/env python3
"""
Fish Audio ASR 功能测试脚本
测试实际的语音识别功能
"""

import asyncio
import logging
import sys
import os
import tempfile
import sounddevice as sd
import numpy as np
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.asr_client import ASRClient
from utils.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_fish_audio_asr_functionality():
    """测试Fish Audio ASR的实际功能"""
    try:
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.load()

        logger.info("=== Fish Audio ASR 功能测试 ===")
        logger.info(f"ASR类型: {config['asr']['asr_type']}")

        # 初始化ASR客户端
        asr_client = ASRClient(config)
        logger.info("ASR客户端初始化成功")

        # 创建临时音频文件用于测试
        logger.info("正在录制测试音频...")

        # 录制参数
        duration = 3  # 录制3秒
        sample_rate = 16000
        channels = 1

        # 录制音频
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=channels, dtype=np.int16)
        sd.wait()

        # 保存为临时WAV文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name

        # 转换为numpy数组并保存
        import wave
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        logger.info(f"测试音频已保存到: {temp_path}")

        # 测试ASR识别
        logger.info("正在进行语音识别...")
        
        # 读取音频文件为字节数据
        with open(temp_path, 'rb') as f:
            audio_blob = f.read()
        
        result = await asr_client.process_recording(audio_blob)

        if result:
            logger.info(f"识别结果: {result}")
            logger.info("Fish Audio ASR功能测试: 成功")
        else:
            logger.warning("未获得识别结果")
            logger.info("Fish Audio ASR功能测试: 部分成功（客户端工作但无结果）")

        # 清理临时文件
        os.unlink(temp_path)
        logger.info("临时文件已清理")

    except Exception as e:
        logger.error(f"Fish Audio ASR功能测试失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False

    return True

async def test_fish_audio_asr_config():
    """测试Fish Audio ASR配置"""
    try:
        config_loader = ConfigLoader()
        config = config_loader.load()

        logger.info("=== Fish Audio ASR 配置测试 ===")
        logger.info(f"ASR类型: {config['asr']['asr_type']}")
        logger.info(f"API Key: {'已设置' if config['asr']['fish_audio_api_key'] else '未设置'}")
        logger.info(f"语言: {config['asr']['fish_audio_language']}")
        logger.info(f"忽略时间戳: {config['asr']['fish_audio_ignore_timestamps']}")

        # 初始化客户端
        asr_client = ASRClient(config)
        logger.info("Fish Audio ASR客户端初始化成功")

        # 测试客户端属性
        if hasattr(asr_client, 'fish_audio_client'):
            logger.info("Fish Audio客户端属性存在")
        else:
            logger.warning("Fish Audio客户端属性不存在")

        logger.info("Fish Audio ASR配置测试: 成功")

    except Exception as e:
        logger.error(f"Fish Audio ASR配置测试失败: {e}")
        return False

    return True

async def main():
    """主测试函数"""
    logger.info("开始Fish Audio ASR综合测试")

    # 测试配置
    config_success = await test_fish_audio_asr_config()

    # 测试功能
    if config_success:
        functionality_success = await test_fish_audio_asr_functionality()
    else:
        functionality_success = False
        logger.error("由于配置测试失败，跳过功能测试")

    # 总结
    logger.info("=== 测试总结 ===")
    logger.info(f"配置测试: {'通过' if config_success else '失败'}")
    logger.info(f"功能测试: {'通过' if functionality_success else '失败'}")

    if config_success and functionality_success:
        logger.info("🎉 Fish Audio ASR集成测试全部通过！")
        return True
    else:
        logger.error("❌ Fish Audio ASR集成测试失败")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试过程中发生未预期的错误: {e}")
        sys.exit(1)
