"""
语音模块 - 提供文本转语音和语音识别功能
"""

from .tts_client import TTSClient
from .asr_client import ASRClient

__all__ = ['TTSClient', 'ASRClient']