#!/usr/bin/env python3
"""
Fish Audio ASR 演示脚本
展示Fish Audio ASR的基本使用方法
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

async def demo_fish_audio_asr():
    """演示Fish Audio ASR的使用"""
    try:
        # 加载配置
        config_loader = ConfigLoader()
        config = config_loader.load()

        logger.info("🎤 Fish Audio ASR 演示")
        logger.info("=" * 50)

        # 显示当前配置
        logger.info("📋 当前ASR配置:")
        logger.info(f"   类型: {config['asr']['asr_type']}")
        logger.info(f"   语言: {config['asr']['fish_audio_language']}")
        logger.info(f"   API Key: {'✓ 已配置' if config['asr']['fish_audio_api_key'] else '✗ 未配置'}")

        # 初始化ASR客户端
        asr_client = ASRClient(config)
        logger.info("🔧 ASR客户端初始化完成")

        # 录制音频
        logger.info("\n🎙️  正在录制音频 (3秒)...")
        logger.info("   请对着麦克风说话...")

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

        logger.info(f"💾 音频已保存: {temp_path}")

        # 进行语音识别
        logger.info("\n🧠 正在进行语音识别...")
        with open(temp_path, 'rb') as f:
            audio_blob = f.read()

        result = await asr_client.process_recording(audio_blob)

        # 显示结果
        logger.info("\n📝 识别结果:")
        logger.info("=" * 30)
        if result:
            logger.info(f"🎯 识别文本: '{result}'")
            logger.info("✅ Fish Audio ASR 识别成功！")
        else:
            logger.info("❌ 未获得识别结果")
            logger.info("💡 可能是音频质量问题或网络问题")

        # 清理临时文件
        os.unlink(temp_path)
        logger.info("🗑️  临时文件已清理")

        logger.info("\n🎉 演示完成！")

    except Exception as e:
        logger.error(f"❌ 演示失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False

    return True

async def main():
    """主函数"""
    logger.info("🚀 启动Fish Audio ASR演示")

    success = await demo_fish_audio_asr()

    if success:
        logger.info("\n🎊 Fish Audio ASR演示成功完成！")
        logger.info("💡 提示: 您现在可以在主应用程序中使用Fish Audio ASR了")
    else:
        logger.error("\n💥 Fish Audio ASR演示失败")
        logger.info("🔧 请检查配置和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 演示被用户中断")
    except Exception as e:
        logger.error(f"💥 演示过程中发生意外错误: {e}")
