#!/usr/bin/env python3
"""
测试Fish Audio返回的音频数据格式
"""

import json
import logging
import io

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fish_audio_format():
    """测试Fish Audio返回的数据格式"""

    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 模拟TTSClient的Fish Audio逻辑
    tts_config = config.get('tts', {})
    api_key = tts_config.get('fish_audio_api_key', '')
    reference_id = tts_config.get('fish_audio_reference_id', '')
    backend = tts_config.get('fish_audio_backend', 'speech-1.6')
    temperature = tts_config.get('fish_audio_temperature', 0.7)
    top_p = tts_config.get('fish_audio_top_p', 0.7)

    if not api_key:
        logger.error("Fish Audio API Key未配置")
        return

    if not reference_id:
        logger.error("Fish Audio reference_id未配置")
        return

    try:
        from fish_audio_sdk import WebSocketSession, TTSRequest, ReferenceAudio

        logger.info("正在初始化Fish Audio客户端...")
        session = WebSocketSession(api_key)

        # 创建TTS请求
        tts_request = TTSRequest(
            text="你好，这是一个测试",
            reference_id=reference_id,
            temperature=temperature,
            top_p=top_p
        )

        logger.info("开始生成音频...")

        # 生成语音
        audio_data = bytearray()

        def text_stream():
            """文本流生成器"""
            for word in "你好，这是一个测试".split():
                yield word + " "

        # 调用TTS API
        for chunk in session.tts(
            tts_request,
            text_stream(),
            backend=backend
        ):
            audio_data.extend(chunk)

        logger.info(f"音频数据大小: {len(audio_data)} bytes")

        # 检查数据头
        if len(audio_data) > 12:
            header = audio_data[:12]
            logger.info(f"数据头 (hex): {header.hex()}")
            logger.info(f"数据头 (bytes): {header}")

            # 检查是否是WAV格式
            if header.startswith(b'RIFF'):
                logger.info("✅ 数据是WAV格式")
            elif header.startswith(b'ID3') or header.startswith(b'\xff\xfb'):
                logger.info("🎵 数据是MP3格式")
            elif header.startswith(b'fLaC'):
                logger.info("🎵 数据是FLAC格式")
            else:
                logger.info("❓ 未知音频格式")

        # 保存音频数据用于进一步分析
        with open('test_audio.mp3', 'wb') as f:
            f.write(audio_data)

        logger.info("音频数据已保存到 test_audio.mp3")

        # 测试音频转换
        logger.info("测试音频格式转换...")
        try:
            from pydub import AudioSegment
            
            # 从MP3数据创建AudioSegment
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
            logger.info(f"MP3加载成功，长度: {len(audio_segment)}ms, 采样率: {audio_segment.frame_rate}Hz")
            
            # 转换为WAV格式
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format='wav')
            wav_data = wav_buffer.getvalue()
            
            logger.info(f"WAV转换成功，大小: {len(wav_data)} bytes")
            
            # 保存WAV文件
            with open('test_audio.wav', 'wb') as f:
                f.write(wav_data)
            
            logger.info("WAV文件已保存到 test_audio.wav")
            
        except Exception as e:
            logger.error(f"音频转换测试失败: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        logger.error(f"Fish Audio测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fish_audio_format()
