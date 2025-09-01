#!/usr/bin/env python3
"""
测试Fish Audio ASR集成
"""

import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fish_audio_asr_integration():
    """测试Fish Audio ASR集成"""

    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 模拟ASR客户端的Fish Audio集成
    asr_config = config.get('asr', {})
    asr_type = asr_config.get('asr_type', '本地ASR')

    logger.info(f"ASR类型: {asr_type}")

    if asr_type == "Fish Audio":
        try:
            api_key = asr_config.get('fish_audio_api_key', '')
            if not api_key:
                logger.error("Fish Audio API Key未配置")
                return False

            logger.info("正在初始化Fish Audio ASR客户端...")

            # 模拟ASR客户端初始化逻辑
            from fish_audio_sdk import Session, ASRRequest

            session = Session(api_key)
            logger.info("Fish Audio ASR客户端初始化成功")

            # 测试ASR请求创建
            test_request = ASRRequest(
                audio=b"test_audio_data",
                language=asr_config.get('fish_audio_language', 'zh'),
                ignore_timestamps=asr_config.get('fish_audio_ignore_timestamps', True)
            )
            logger.info("Fish Audio ASR请求创建成功")

            logger.info("Fish Audio ASR集成测试成功")
            return True

        except ImportError as e:
            logger.error(f"Fish Audio SDK未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"Fish Audio ASR集成测试失败: {e}")
            return False
    else:
        logger.info("当前配置不是Fish Audio ASR")
        return True

if __name__ == "__main__":
    success = test_fish_audio_asr_integration()
    print(f"Fish Audio ASR集成测试: {'成功' if success else '失败'}")
