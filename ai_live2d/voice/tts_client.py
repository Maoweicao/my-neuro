"""
TTS客户端模块 - 负责文本转语音并处理音频播放
"""

import json
import asyncio
import aiohttp
import io
import numpy as np
import logging
import re
import wave
import sounddevice as sd  # 高性能异步音频库
import os
import websockets
import uuid
from typing import Dict, List, Any, Optional, Callable, Coroutine

import websockets
import uuid
from typing import Dict, List, Any, Optional, Callable, Coroutine

logger = logging.getLogger("tts_client")

# 导入豆包TTS协议模块
try:
    from voice.volcengine_unidirectional_stream_demo.protocols import (
        EventType, MsgType, full_client_request, receive_message
    )
    PROTOCOLS_AVAILABLE = True
except ImportError:
    logger.warning("豆包TTS协议模块未找到，将使用HTTP流式API")
    PROTOCOLS_AVAILABLE = False

class TTSClient:
    def __init__(self, config:dict, event_bus=None):
        """初始化TTS客户端"""
        self.config = config
        self.event_bus = event_bus
        self.tts_type = config.get("tts", {}).get("tts_type", "本地TTS")
        self.tts_url = config.get("tts", {}).get("url", "http://localhost:6006/v3")
        self.language = config.get("tts", {}).get("language", "zh")

        # 根据TTS类型初始化相应的客户端
        self.tts_client = None
        self._init_tts_client()

        # 创建持久化HTTP连接池（用于本地TTS）
        if self.tts_type == "本地TTS":
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit_per_host=4),
                timeout=aiohttp.ClientTimeout(total=50)
            )
        else:
            self.session = None
        
        # 音频处理相关
        self.audio_chunk_size = 1024
        
        # 异步任务管理
        self.processing_task = None
        self.playback_task = None
        self.text_animation_task = None
        self.is_processing = False
        self.is_playing_audio = False  # 播放状态标志
        self.shutdown_event = asyncio.Event()
        
        # 文本处理队列
        self.text_segment_queue = asyncio.Queue()
        self.audio_data_queue = asyncio.Queue()
        
        # 当前显示的文本
        self.current_full_text = ''
        self.displayed_text = ''
        self.current_segment_text = ''
        
        # 标点符号定义 - 用于分割文本
        self.punctuations = ('.', '。', '!', '！', '?', '？', ',', '，', ';', '；', ':', '：', '~')
        
        # 回调函数
        self.on_audio_data_callback = None  # 音频数据回调(用于控制模型嘴部动作)
        self.on_text_update_callback = None # 文本更新回调(用于显示字幕)
        
        logger.info(f"初始化TTS客户端 ({self.tts_type})... [ 完成 ]")

    def _init_tts_client(self):
        """根据TTS类型初始化相应的客户端"""
        if self.tts_type == "Fish Audio":
            self.tts_client = self._create_fish_audio_client()
        elif self.tts_type == "豆包TTS":
            self.tts_client = self._create_doubao_client()
        elif self.tts_type == "本地TTS":
            self.tts_client = self._create_local_client()
        else:
            logger.warning(f"未知的TTS类型: {self.tts_type}，使用本地TTS")
            self.tts_client = self._create_local_client()

    def _create_fish_audio_client(self):
        """创建Fish Audio客户端"""
        try:
            api_key = self.config.get('tts', {}).get('fish_audio_api_key', '')
            if not api_key:
                logger.error("Fish Audio API Key未配置")
                return None
            
            logger.info(f"正在初始化Fish Audio客户端，API Key: {api_key[:10]}...")
            
            from fish_audio_sdk import WebSocketSession, TTSRequest, ReferenceAudio
            session = WebSocketSession(api_key)
            
            logger.info("Fish Audio客户端初始化成功")
            return {
                'type': 'fish_audio',
                'session': session
            }
        except ImportError as e:
            logger.error(f"Fish Audio SDK未安装: {e}")
            return None
        except Exception as e:
            logger.error(f"Fish Audio客户端初始化失败: {e}")
            return None

    def _create_doubao_client(self):
        """创建豆包TTS客户端"""
        try:
            app_id = self.config.get('tts', {}).get('doubao_app_id', '')
            access_token = self.config.get('tts', {}).get('doubao_access_token', '')
            voice_type = self.config.get('tts', {}).get('doubao_voice_type', '')
            encoding = self.config.get('tts', {}).get('doubao_encoding', 'wav')
            resource_id = self.config.get('tts', {}).get('doubao_resource_id', '')

            if not app_id or not access_token:
                logger.error("豆包TTS APP ID或Access Token未配置")
                return None

            logger.info("正在初始化豆包TTS客户端...")

            return {
                'type': 'doubao',
                'app_id': app_id,  # 用于WebSocket的X-Api-App-Key
                'access_token': access_token,
                'resource_id': resource_id,
                'voice_type': voice_type,
                'encoding': encoding,
                'websocket_url': 'wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream',
                'http_url': 'https://openspeech.bytedance.com/api/v3/tts/unidirectional',
                'app_key': 'aGjiRDfUWi'  # 固定值，用于HTTP的X-Api-App-Key
            }
        except Exception as e:
            logger.error(f"创建豆包TTS客户端失败: {e}")
            return None

    def _create_local_client(self):
        """创建本地TTS客户端"""
        return {'type': 'local'}

    async def start(self):
        """启动处理任务"""
        logger.info("启动ASR客户端... [ 进行中 ]")
        self.shutdown_event.clear()
        self.processing_task = asyncio.create_task(self._process_text_loop())
        self.playback_task = asyncio.create_task(self._playback_loop())
        logger.info("启动ASR客户端... [ 完成 ]")

    async def stop(self):
        """安全停止所有任务"""
        self.shutdown_event.set()
        
        # 取消所有任务
        tasks = [t for t in [self.processing_task, self.playback_task, self.text_animation_task] 
                 if t is not None and not t.done()]
        
        for task in tasks:
            task.cancel()
        
        # 等待任务完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 关闭Fish Audio会话
        if self.tts_client and self.tts_type == "Fish Audio":
            try:
                if 'session' in self.tts_client and self.tts_client['session']:
                    self.tts_client['session'].close()
            except Exception as e:
                logger.error(f"关闭Fish Audio会话错误: {e}")
        
        # 关闭豆包TTS WebSocket连接 (如果存在)
        if self.tts_client and self.tts_type == "豆包TTS":
            try:
                if 'websocket' in self.tts_client and self.tts_client['websocket']:
                    await self.tts_client['websocket'].close()
                    logger.info("豆包TTS WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"关闭豆包TTS WebSocket连接错误: {e}")
        
        # 关闭HTTP会话
        if self.session and not self.session.closed:
            await self.session.close()
        
        # 重置状态
        await self.reset()
        
        await self.event_bus.publish("tts_end", {})
    
    def set_callbacks(self, 
                     on_audio_data: Optional[Callable[[float], Coroutine]] = None,
                     on_text_update: Optional[Callable[[str], Coroutine]] = None):
        """设置回调函数"""
        self.on_audio_data_callback = on_audio_data
        self.on_text_update_callback = on_text_update
        logger.info("设置TTS回调函数... [ 成功 ]")

    async def _process_text_loop(self):
        """异步文本处理循环 - 负责将文本转换为音频"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # 等待队列中的文本
                    segment = await asyncio.wait_for(
                        self.text_segment_queue.get(),
                        timeout=0.1
                    )
                    self.is_processing = True
                    
                    # 将文本转换为语音
                    audio_data = await self._convert_text_to_speech(segment)
                    if audio_data:
                        await self.audio_data_queue.put({
                            'audio': audio_data,
                            'text': segment
                        })
                    else:
                        # 处理TTS失败的情况
                        if segment and self.event_bus:
                            # 更新显示的文本
                            self.displayed_text += segment
                            if self.on_text_update_callback:
                                await self.on_text_update_callback(self.displayed_text)
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"文本处理错误: {e}")
                    if self.event_bus:
                        await self.event_bus.publish("tts_error", {"error": str(e)})
                finally:
                    self.is_processing = False
        except asyncio.CancelledError:
            logger.debug("文本处理任务被取消")
        except Exception as e:
            logger.error(f"文本处理循环异常: {e}")

    async def _playback_loop(self):
        """异步音频播放循环"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    audio_package = await self.audio_data_queue.get()
                    await self._play_audio(audio_package)  # 直接调用播放函数
                except Exception as e:
                    logger.error(f"播放循环错误: {e}")
                    # 发布错误事件
                    if self.event_bus:
                        await self.event_bus.publish("tts_error", {"error": str(e)})

        except asyncio.CancelledError:
            logger.debug("播放任务被取消")
        except Exception as e:
            logger.error(f"播放循环异常: {e}")
        finally:
            # 确保在播放循环结束时发布结束事件
            if self.event_bus:
                await self.event_bus.publish("tts_end", {})

    async def _text_animation_task(self, segment_text, audio_length):
        """异步文本动画任务"""
        try:
            # 通知字幕管理器TTS开始
            if self.event_bus:
                await self.event_bus.publish("tts_start", {})

            segment_length = len(segment_text)
            char_interval = audio_length / segment_length if segment_length > 0 else 0.1
            char_interval = max(0.03, min(0.2, char_interval))
            
            char_display_index = 0
            start_time = asyncio.get_event_loop().time()
            
            while char_display_index < segment_length and not self.shutdown_event.is_set():
                elapsed = asyncio.get_event_loop().time() - start_time
                target_index = min(segment_length, int(elapsed / char_interval))
                
                if target_index > char_display_index:
                    char_display_index = target_index
                    current_display = self.displayed_text + segment_text[:char_display_index]
                    
                    # 触发文本更新回调
                    if self.on_text_update_callback:
                        await self.on_text_update_callback(current_display)
                
                await asyncio.sleep(0.01)
            
            # 更新最终显示的文本
            self.displayed_text += segment_text
            if self.on_text_update_callback:
                await self.on_text_update_callback(self.displayed_text)
        
        except asyncio.CancelledError:
            logger.debug("文本动画任务被取消")
        except Exception as e:
            logger.error(f"文本动画任务异常: {e}")
        finally:
            # 通知字幕管理器TTS结束
            if self.event_bus:
                await self.event_bus.publish("tts_end", {})

    def _preprocess_text_for_tts(self, text):
        """预处理文本用于TTS，移除特殊格式标记等"""
        if not text:
            return ""
            
        # 移除括号内容
        text = re.sub(r'（.*?）|\(.*?\)', '', text)
        
        # 移除星号包裹的内容
        text = re.sub(r'\*.*?\*', '', text)
        
        # 确保文本不是空的
        processed_text = text.strip()
        return processed_text
    
    async def _convert_text_to_speech(self, text):
        """将文本转换为语音"""
        try:
            if not text or len(text.strip()) == 0:
                logger.warning("尝试转换空文本，跳过TTS请求")
                return None
            
            # 预处理文本
            text_for_tts = self._preprocess_text_for_tts(text)
            
            if not text_for_tts:
                logger.warning("处理后的文本为空，跳过TTS请求")
                return None
            
            # 根据TTS类型调用相应的转换方法
            if self.tts_type == "Fish Audio":
                return await self._convert_with_fish_audio(text_for_tts)
            elif self.tts_type == "豆包TTS":
                return await self._convert_with_doubao(text_for_tts)
            elif self.tts_type == "本地TTS":
                return await self._convert_with_local(text_for_tts)
            else:
                logger.warning(f"未知的TTS类型: {self.tts_type}，使用本地TTS")
                return await self._convert_with_local(text_for_tts)
        
        except Exception as e:
            logger.error(f"TTS转换错误: {e}")
            return None
    
    async def _play_audio(self, audio_package):
        """异步播放音频并同步显示文本"""
        audio_data = audio_package.get('audio')
        segment_text = audio_package.get('text', '')
        
        if not audio_data:
            return
        
        try:
            # 检测音频格式并转换为WAV
            audio_data = self._convert_to_wav(audio_data)
            if not audio_data:
                logger.error("音频格式转换失败")
                return
            
            # 解析WAV音频数据
            with io.BytesIO(audio_data) as wav_io:
                with wave.open(wav_io, 'rb') as wave_file:
                    sample_width = wave_file.getsampwidth()
                    channels = wave_file.getnchannels()
                    framerate = wave_file.getframerate()
                    num_frames = wave_file.getnframes()
                    frames = wave_file.readframes(num_frames)
            
            # 计算音频长度
            audio_length = len(frames) / (framerate * channels * sample_width)
            
            self.is_playing_audio = True
            
            # 启动文本动画任务
            self.text_animation_task = asyncio.create_task(
                self._text_animation_task(segment_text, audio_length)
            )
            
            # 将音频数据转换为numpy数组
            dtype = np.int16 if sample_width == 2 else np.int8
            audio_array = np.frombuffer(frames, dtype=dtype)
            # 转换为浮点数并归一化
            audio_float = audio_array.astype(np.float32) / 32767.0
            
            # 重塑为多声道
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)

            # 嘴型匹配
            if self.on_audio_data_callback:
                asyncio.create_task(self.on_audio_data_callback({
                    'num_frames': num_frames,
                    'framerate': framerate,
                    'sample_width': sample_width,
                    'channels': channels,
                    'frames': frames,
                    'pcm_data': audio_float.copy()
                }))
            
            sd.play(audio_float, samplerate=framerate, blocking=False)

            while sd.get_stream().active:
                await asyncio.sleep(0.01)  # 每10ms检查一次播放状态
            
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
        finally:
            # 确保结束回调被触发
            await self.event_bus.publish("tts_end", {})
            self.is_playing_audio = False
            
            # 取消文本动画任务（如果还在运行）
            if self.text_animation_task and not self.text_animation_task.done():
                self.text_animation_task.cancel()
                try:
                    await self.text_animation_task
                except asyncio.CancelledError:
                    pass

    def _convert_to_wav(self, audio_data):
        """将音频数据转换为WAV格式"""
        try:
            # 如果数据已经是WAV格式，直接返回
            if len(audio_data) > 12 and audio_data[:4] == b'RIFF':
                logger.debug("音频已经是WAV格式")
                return audio_data
            
            # 检测MP3格式
            if len(audio_data) > 2 and audio_data[:2] == b'\xff\xfb':
                logger.info("检测到MP3格式，正在转换为WAV...")
                try:
                    from pydub import AudioSegment
                    
                    # 从MP3数据创建AudioSegment
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    
                    # 转换为WAV格式
                    wav_buffer = io.BytesIO()
                    audio_segment.export(wav_buffer, format='wav')
                    wav_data = wav_buffer.getvalue()
                    
                    logger.info(f"MP3转换为WAV成功，大小: {len(wav_data)} bytes")
                    return wav_data
                    
                except ImportError:
                    logger.error("pydub未安装，无法转换MP3格式")
                    return None
                except Exception as e:
                    logger.error(f"MP3转换失败: {e}")
                    return None
            
            # 检测FLAC格式
            if len(audio_data) > 4 and audio_data[:4] == b'fLaC':
                logger.info("检测到FLAC格式，正在转换为WAV...")
                try:
                    from pydub import AudioSegment
                    
                    # 从FLAC数据创建AudioSegment
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format='flac')
                    
                    # 转换为WAV格式
                    wav_buffer = io.BytesIO()
                    audio_segment.export(wav_buffer, format='wav')
                    wav_data = wav_buffer.getvalue()
                    
                    logger.info(f"FLAC转换为WAV成功，大小: {len(wav_data)} bytes")
                    return wav_data
                    
                except ImportError:
                    logger.error("pydub未安装，无法转换FLAC格式")
                    return None
                except Exception as e:
                    logger.error(f"FLAC转换失败: {e}")
                    return None
            
            # 其他格式或未知格式
            logger.warning(f"未知音频格式，尝试直接处理。数据头: {audio_data[:12].hex() if len(audio_data) > 12 else 'N/A'}")
            return audio_data
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            return None

    async def add_streaming_text(self, text):
        """添加流式文本进行处理
        
        Args:
            text: 文本片段
        """
        if self.shutdown_event.is_set():
            return
        await self.text_segment_queue.put(text)
    
    def _segment_text(self, text):
        """根据标点符号将文本分段
        
        Args:
            text: 要分段的文本
        """
        segments = []
        current_segment = ""
        ready_to_cut, cut = False, False
        for char in text:
            current_segment += char    
            
            # 遇到标点符号时分段
            if char not in self.punctuations and current_segment.strip(): cut = True
            if cut and ready_to_cut:
                segments.append(current_segment[:-1])
                current_segment = char
            
            ready_to_cut = True if char in self.punctuations else False
            if cut: cut = False
 
        # 处理剩余文本
        if current_segment.strip():
            segments.append(current_segment)
        
        return segments
    
    async def speak(self, text):
        """播放完整文本
        
        Args:
            text: 要播放的文本
        """
        if not text.strip():
            return
        
        # 重置状态
        await self.reset()
        
        # 分段处理文本
        segments = self._segment_text(text)
        for segment in segments:
            await self.text_segment_queue.put(segment)
    
    async def reset(self):
        """重置所有状态"""
        # 清空文本
        self.current_full_text = ''
        self.displayed_text = ''
        self.current_segment_text = ''
        
        # 安全清空队列
        while not self.text_segment_queue.empty():
            try:
                self.text_segment_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        while not self.audio_data_queue.empty():
            try:
                self.audio_data_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def is_active(self):
        """判断是否正在播放或处理"""
        # 检查文本队列和音频队列是否都为空
        has_text_queue = not self.text_segment_queue.empty()
        has_audio_queue = not self.audio_data_queue.empty()
        has_animation_task = (self.text_animation_task and 
                            not self.text_animation_task.done())
        
        is_active = has_text_queue or has_audio_queue or has_animation_task or self.is_processing or self.is_playing_audio
        
        # 如果从活跃变为非活跃，发布结束事件
        if not is_active and hasattr(self, '_was_active') and self._was_active:
            if self.event_bus:
                await self.event_bus.publish("tts_end", {})
        
        self._was_active = is_active
        return is_active, has_text_queue, has_audio_queue, has_animation_task, self.is_playing_audio
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def _convert_with_fish_audio(self, text):
        """使用Fish Audio转换文本为语音"""
        try:
            # 如果客户端未初始化，尝试重新初始化
            if not self.tts_client:
                logger.info("Fish Audio客户端未初始化，尝试重新初始化...")
                self.tts_client = self._create_fish_audio_client()
                if not self.tts_client:
                    logger.error("Fish Audio客户端重新初始化失败")
                    return None
            
            # 获取配置
            api_key = self.config.get('tts', {}).get('fish_audio_api_key', '')
            if not api_key:
                logger.error("Fish Audio API Key未配置")
                return None
            
            reference_id = self.config.get('tts', {}).get('fish_audio_reference_id', '')
            backend = self.config.get('tts', {}).get('fish_audio_backend', 'speech-1.6')
            temperature = self.config.get('tts', {}).get('fish_audio_temperature', 0.7)
            top_p = self.config.get('tts', {}).get('fish_audio_top_p', 0.7)
            
            logger.info(f"开始Fish Audio TTS转换，文本长度: {len(text)}")
            
            # 导入Fish Audio SDK
            try:
                from fish_audio_sdk import TTSRequest, ReferenceAudio
            except ImportError:
                logger.error("Fish Audio SDK未安装")
                return None
                return None
            
            # 创建TTS请求
            if reference_id:
                # 使用预设的reference_id
                tts_request = TTSRequest(
                    text=text,
                    reference_id=reference_id,
                    temperature=temperature,
                    top_p=top_p
                )
            else:
                # 使用参考音频文件
                ref_audio_path = self.config.get('tts', {}).get('fish_audio_ref_audio', '')
                ref_text = self.config.get('tts', {}).get('fish_audio_ref_text', '')
                
                if not ref_audio_path or not os.path.exists(ref_audio_path):
                    logger.error("Fish Audio参考音频文件不存在")
                    return None
                
                with open(ref_audio_path, 'rb') as f:
                    ref_audio_data = f.read()
                
                tts_request = TTSRequest(
                    text=text,
                    references=[
                        ReferenceAudio(
                            audio=ref_audio_data,
                            text=ref_text
                        )
                    ],
                    temperature=temperature,
                    top_p=top_p
                )
            
            # 生成语音
            audio_data = bytearray()
            
            def text_stream():
                """文本流生成器"""
                for word in text.split():
                    yield word + " "
            
            # 调用TTS API
            session = self.tts_client['session']
            for chunk in session.tts(
                tts_request,
                text_stream(),
                backend=backend
            ):
                audio_data.extend(chunk)
            
            return bytes(audio_data)
            
        except Exception as e:
            logger.error(f"Fish Audio TTS转换错误: {e}")
            return None

    async def _convert_with_doubao(self, text):
        """使用豆包TTS转换文本为语音"""
        try:
            if not self.tts_client:
                logger.error("豆包TTS客户端未初始化")
                return await self._convert_with_local(text)

            # 根据协议模块可用性选择API
            if PROTOCOLS_AVAILABLE:
                return await self._convert_with_doubao_websocket(text)
            else:
                return await self._convert_with_doubao_rest(text)

        except Exception as e:
            logger.error(f"豆包TTS转换错误: {e}")
            return await self._convert_with_local(text)

    async def _convert_with_doubao_rest(self, text):
        """使用豆包TTS REST API转换文本为语音（HTTP单向流式接口）"""
        try:
            import aiohttp
            import base64

            # 豆包TTS HTTP单向流式API URL
            api_url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

            # 构建请求头
            headers = {
                "X-Api-App-Id": self.tts_client['app_id'],  # HTTP版本使用App-Id
                "X-Api-Access-Key": self.tts_client['access_token'],
                "X-Api-Resource-Id": self.tts_client['resource_id'] or self._get_resource_id(self.tts_client['voice_type']),
                "X-Api-App-Key": self.tts_client['app_key'],  # 固定值
                "Content-Type": "application/json",
                "Connection": "keep-alive"
            }

            # 构建请求体
            request_data = {
                "user": {
                    "uid": "doubao_tts_user"
                },
                "req_params": {
                    "text": text,
                    "speaker": self.tts_client['voice_type'],
                    "audio_params": {
                        "format": self.tts_client['encoding'],
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

            logger.info(f"发送豆包TTS HTTP流式请求: {text[:50]}...")

            # 用于存储音频数据
            audio_data = bytearray()

            # 发送POST请求并处理流式响应
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=request_data) as response:
                    logger.info(f"豆包TTS响应状态码: {response.status}")
                    logger.info(f"豆包TTS响应头: {dict(response.headers)}")

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
                                logger.debug(f"豆包TTS流式数据: {data}")

                                # 处理音频数据
                                if data.get("code") == 0 and "data" in data and data["data"]:
                                    chunk_audio = base64.b64decode(data["data"])
                                    audio_data.extend(chunk_audio)
                                    logger.debug(f"收到音频块，大小: {len(chunk_audio)} bytes")

                                # 处理句子信息
                                elif data.get("code") == 0 and "sentence" in data and data["sentence"]:
                                    logger.info(f"句子信息: {data['sentence']}")

                                # 处理结束标记
                                elif data.get("code") == 20000000:
                                    logger.info("豆包TTS流式响应结束")
                                    break

                                # 处理错误
                                elif data.get("code", 0) > 0:
                                    logger.error(f"豆包TTS流式响应错误: {data}")
                                    return None

                            except json.JSONDecodeError as e:
                                logger.warning(f"解析JSON数据失败: {e}, 原始数据: {line_str}")
                                continue
                            except Exception as e:
                                logger.error(f"处理流式数据时出错: {e}")
                                continue

                        # 检查是否收到了音频数据
                        if audio_data:
                            logger.info(f"豆包TTS合成成功，音频总大小: {len(audio_data)} bytes")
                            return bytes(audio_data)
                        else:
                            logger.error("豆包TTS未收到音频数据")
                            return None

                    else:
                        logger.error(f"豆包TTS HTTP请求失败: {response.status}")
                        error_text = await response.text()
                        logger.error(f"错误详情: {error_text}")
                        return None

        except Exception as e:
            logger.error(f"豆包TTS HTTP流式API调用失败: {e}")
            return None

    async def _convert_with_doubao_websocket(self, text):
        """使用豆包TTS WebSocket流式API转换文本为语音"""
        try:
            # WebSocket端点
            websocket_url = "wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream"

            # 构建请求头
            headers = {
                "X-Api-App-Key": self.tts_client['app_id'],  # 注意：使用App-Key而不是App-Id
                "X-Api-Access-Key": self.tts_client['access_token'],
                "X-Api-Resource-Id": self.tts_client['resource_id'] or self._get_resource_id(self.tts_client['voice_type']),
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }

            logger.info(f"连接豆包TTS WebSocket: {websocket_url}")
            logger.info(f"请求头: {headers}")

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
                        "speaker": self.tts_client['voice_type'],
                        "audio_params": {
                            "format": self.tts_client['encoding'],
                            "sample_rate": 24000,
                            "enable_timestamp": True,
                        },
                        "text": text,
                        "additions": json.dumps({
                            "disable_markdown_filter": False,
                        }),
                    },
                }

                # 发送请求
                await full_client_request(websocket, json.dumps(request_data).encode())
                logger.info(f"发送豆包TTS请求: {text[:50]}...")

                # 接收音频数据
                audio_data = bytearray()
                while True:
                    msg = await receive_message(websocket)

                    if msg.type == MsgType.FullServerResponse:
                        if msg.event == EventType.SessionFinished:
                            break
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                        logger.debug(f"收到音频块，大小: {len(msg.payload)} bytes")
                    else:
                        logger.error(f"TTS转换失败: {msg}")
                        return None

                # 检查是否收到了音频数据
                if not audio_data:
                    logger.error("豆包TTS未收到音频数据")
                    return None

                logger.info(f"豆包TTS合成成功，音频总大小: {len(audio_data)} bytes")
                return bytes(audio_data)

            finally:
                await websocket.close()
                logger.info("WebSocket连接已关闭")

        except Exception as e:
            logger.error(f"豆包TTS WebSocket流式API调用失败: {e}")
            return None

    def _get_resource_id(self, voice_type):
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



    async def _convert_with_local(self, text):
        """使用本地TTS转换文本为语音"""
        try:
            if not self.session:
                logger.error("本地TTS会话未初始化")
                return None
            
            # 使用aiohttp发送异步请求
            async with self.session.post(
                self.tts_url,
                headers={'Content-Type': 'application/json'},
                json={'text': text, 'text_language': self.language}
            ) as response:
                    
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"本地TTS请求失败: {response.status}")
                    try:
                        error_info = await response.json()
                        logger.error(f"服务器返回错误信息: {error_info}")
                    except:
                        pass
                    return None
        
        except Exception as e:
            logger.error(f"本地TTS转换错误: {e}")
            return None