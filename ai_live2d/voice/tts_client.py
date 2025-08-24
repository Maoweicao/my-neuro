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
from typing import Dict, List, Any, Optional, Callable, Coroutine

logger = logging.getLogger("tts_client")

class TTSClient:
    def __init__(self, config:dict, event_bus=None):
        """初始化TTS客户端"""
        self.config = config
        self.event_bus = event_bus
        self.tts_url = config.get("tts", {}).get("url", "http://localhost:6006/v3")
        self.language = config.get("tts", {}).get("language", "zh")

        # 创建持久化HTTP连接池
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit_per_host=4),
            timeout=aiohttp.ClientTimeout(total=50)
        )
        
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
        
        logger.info("初始化TTS客户端... [ 完成 ]")

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
        
        # 关闭HTTP会话
        if not self.session.closed:
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
            
            # 使用aiohttp发送异步请求
            async with self.session.post(
                self.tts_url,
                headers={'Content-Type': 'application/json'},
                json={'text': text_for_tts, 'text_language': self.language}
            ) as response:
                    
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"TTS请求失败: {response.status}")
                    try:
                        error_info = await response.json()
                        logger.error(f"服务器返回错误信息: {error_info}")
                    except:
                        pass
                    return None
        
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

    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.stop()