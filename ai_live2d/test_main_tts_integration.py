#!/usr/bin/env python3
"""
豆包TTS主程序集成测试
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.tts_client import TTSClient

async def test_main_tts():
    """测试主程序中的豆包TTS功能"""
    try:
        # 使用与配置文件相同的设置
        config = {
            'tts': {
                'tts_type': '豆包TTS',
                'doubao_app_id': '9732033966',
                'doubao_access_token': 's0FmSeo36OWS3V2jeVRYGSvOJSxrJZyw',
                'doubao_resource_id': 'volc.service_type.10029',
                'doubao_voice_type': 'zh_female_cancan_mars_bigtts',
                'doubao_encoding': 'wav'
            }
        }

        print("🚀 初始化TTS客户端...")
        client = TTSClient(config)

        print("🎵 开始语音合成...")
        test_text = "你好，这是豆包TTS WebSocket集成测试。"
        result = await client._convert_with_doubao(test_text)

        if result:
            print(f"✅ 合成成功！音频大小: {len(result)} bytes")

            # 保存测试音频
            output_file = "test_output/main_tts_test.wav"
            with open(output_file, 'wb') as f:
                f.write(result)
            print(f"🎵 音频已保存: {output_file}")

            return True
        else:
            print("❌ 合成失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_main_tts())
    if success:
        print("\n🎊 主程序豆包TTS集成测试通过！")
    else:
        print("\n💥 主程序豆包TTS集成测试失败")
