"""
ASR客户端模块 - 负责语音识别和处理
"""

import asyncio
import websockets
import json
import numpy as np
import time
import aiohttp
import wave
import io
import logging
import sounddevice as sd
import gzip
import base64
import hmac
import uuid
import struct
from hashlib import sha256
from urllib.parse import urlparse
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator

logger = logging.getLogger("asr_client")

# SAUC协议常量
class ProtocolVersion:
    V1 = 0b0001

class MessageType:
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111

class MessageTypeSpecificFlags:
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011

class SerializationType:
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001

class CompressionType:
    GZIP = 0b0001

# 豆包ASR协议常量 (保留兼容性)
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

PROTOCOL_VERSION_BITS = 4
HEADER_BITS = 4
MESSAGE_TYPE_BITS = 4
MESSAGE_TYPE_SPECIFIC_FLAGS_BITS = 4
MESSAGE_SERIALIZATION_BITS = 4
MESSAGE_COMPRESSION_BITS = 4
RESERVED_BITS = 8

# Message Type:
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000  # no check sequence
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_SEQUENCE_1 = 0b0011

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111

# Message Compression
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111

class CommonUtils:
    @staticmethod
    def gzip_compress(data: bytes) -> bytes:
        return gzip.compress(data)

    @staticmethod
    def gzip_decompress(data: bytes) -> bytes:
        return gzip.decompress(data)

class AsrRequestHeader:
    def __init__(self):
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def with_message_type(self, message_type: int) -> 'AsrRequestHeader':
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int) -> 'AsrRequestHeader':
        self.message_type_specific_flags = flags
        return self

    def with_serialization_type(self, serialization_type: int) -> 'AsrRequestHeader':
        self.serialization_type = serialization_type
        return self

    def with_compression_type(self, compression_type: int) -> 'AsrRequestHeader':
        self.compression_type = compression_type
        return self

    def with_reserved_data(self, reserved_data: bytes) -> 'AsrRequestHeader':
        self.reserved_data = reserved_data
        return self

    def to_bytes(self) -> bytes:
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

    @staticmethod
    def default_header() -> 'AsrRequestHeader':
        return AsrRequestHeader()

class RequestBuilder:
    @staticmethod
    def new_auth_headers(appid: str, token: str, resource_id: str) -> dict:
        reqid = str(uuid.uuid4())
        return {
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": reqid,
            "X-Api-Access-Key": token,
            "X-Api-App-Key": appid
        }

    @staticmethod
    def new_full_client_request(seq: int, uid: str, sample_rate: int) -> bytes:
        header = AsrRequestHeader.default_header() \
            .with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)

        payload = {
            "user": {
                "uid": uid
            },
            "audio": {
                "format": "wav",
                "codec": "raw",
                "rate": sample_rate,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                "enable_nonstream": False
            }
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        compressed_payload = CommonUtils.gzip_compress(payload_bytes)
        payload_size = len(compressed_payload)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack('>i', seq))
        request.extend(struct.pack('>I', payload_size))
        request.extend(compressed_payload)

        return bytes(request)

    @staticmethod
    def new_audio_only_request(seq: int, segment: bytes, is_last: bool = False) -> bytes:
        header = AsrRequestHeader.default_header()
        if is_last:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.NEG_WITH_SEQUENCE)
            seq = -seq
        else:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
        header.with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack('>i', seq))

        compressed_segment = CommonUtils.gzip_compress(segment)
        request.extend(struct.pack('>I', len(compressed_segment)))
        request.extend(compressed_segment)

        return bytes(request)

class AsrResponse:
    def __init__(self):
        self.code = 0
        self.event = 0
        self.is_last_package = False
        self.payload_sequence = 0
        self.payload_size = 0
        self.payload_msg = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "event": self.event,
            "is_last_package": self.is_last_package,
            "payload_sequence": self.payload_sequence,
            "payload_size": self.payload_size,
            "payload_msg": self.payload_msg
        }

class ResponseParser:
    @staticmethod
    def parse_response(msg: bytes) -> AsrResponse:
        response = AsrResponse()

        header_size = msg[0] & 0x0f
        message_type = msg[1] >> 4
        message_type_specific_flags = msg[1] & 0x0f
        serialization_method = msg[2] >> 4
        message_compression = msg[2] & 0x0f

        payload = msg[header_size*4:]

        # 解析message_type_specific_flags
        if message_type_specific_flags & 0x01:
            response.payload_sequence = struct.unpack('>i', payload[:4])[0]
            payload = payload[4:]
        if message_type_specific_flags & 0x02:
            response.is_last_package = True
        if message_type_specific_flags & 0x04:
            response.event = struct.unpack('>i', payload[:4])[0]
            payload = payload[4:]

        # 解析message_type
        if message_type == MessageType.SERVER_FULL_RESPONSE:
            response.payload_size = struct.unpack('>I', payload[:4])[0]
            payload = payload[4:]
        elif message_type == MessageType.SERVER_ERROR_RESPONSE:
            response.code = struct.unpack('>i', payload[:4])[0]
            response.payload_size = struct.unpack('>I', payload[4:8])[0]
            payload = payload[8:]

        if not payload:
            return response

        # 解压缩
        if message_compression == CompressionType.GZIP:
            try:
                payload = CommonUtils.gzip_decompress(payload)
            except Exception as e:
                logger.error(f"Failed to decompress payload: {e}")
                return response

        # 解析payload
        try:
            if serialization_method == SerializationType.JSON:
                response.payload_msg = json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to parse payload: {e}")

        return response

logger = logging.getLogger("asr_client")

class ASRClient:
    def __init__(self, config, event_bus=None):
        """初始化ASR客户端
        
        Args:
            config: 配置信息，包含ASR服务URL等
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus
        
        # 从配置中读取ASR类型和相关参数
        self.asr_type = config.get("asr", {}).get("asr_type", "本地ASR")
        
        # 本地ASR配置
        self.vad_url = config.get("asr", {}).get("vad_url", "ws://localhost:6006/v1/ws/vad")
        self.asr_url = config.get("asr", {}).get("asr_url", "http://localhost:6006/v1/upload_audio")
        
        # Fish Audio ASR配置
        self.fish_audio_api_key = config.get("asr", {}).get("fish_audio_api_key", "")
        self.fish_audio_language = config.get("asr", {}).get("fish_audio_language", "zh")
        self.fish_audio_ignore_timestamps = config.get("asr", {}).get("fish_audio_ignore_timestamps", True)
        
        # 豆包ASR配置
        self.doubao_appid = config.get("asr", {}).get("doubao_appid", "")
        self.doubao_token = config.get("asr", {}).get("doubao_token", "")
        self.doubao_cluster = config.get("asr", {}).get("doubao_cluster", "volcano_asr")
        self.doubao_ws_url = config.get("asr", {}).get("doubao_ws_url", "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream")
        self.doubao_language = config.get("asr", {}).get("doubao_language", "zh-CN")
        self.doubao_format = config.get("asr", {}).get("doubao_format", "wav")
        self.doubao_sample_rate = config.get("asr", {}).get("doubao_sample_rate", 16000)
        self.doubao_seg_duration = config.get("asr", {}).get("doubao_seg_duration", 15000)
        self.doubao_resource_id = config.get("asr", {}).get("doubao_resource_id", "volc.bigasr.sauc.duration")
        
        # 初始化Fish Audio客户端
        self.fish_audio_session = None
        self._init_fish_audio_client()
        
        # 初始化豆包ASR客户端
        self.doubao_ws_client = None
        self._init_doubao_client()
        
        # 音频相关参数
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = np.float32
        self.block_size = 512  # 每次处理的音频帧大小
        
        # 状态标志
        self.is_processing_audio = False  # 是否正在处理音频
        self.asr_locked = True           # ASR是否被锁定
        self.is_recording = False         # 是否正在录音
        self.should_stop = False          # 是否应该停止
        self.is_running = False           # 客户端是否正在运行
        self.interrupt_flag = False       # 中断标志
        
        # 音频处理相关
        self.websocket = None
        self.retry_count = 0
        self.max_retries = 5

        # 音频流对象
        self.audio_stream = None
        
        # 缓冲区设置
        self.continuous_buffer = []       # 连续的音频缓冲区
        self.recording_start_index = 0    # 录音开始的索引
        self.pre_record_time = 1          # 预录制时间（秒）
        self.pre_record_samples = self.sample_rate * self.pre_record_time
        
        # 静音检测
        self.last_speech_time = 0         # 上次检测到语音的时间
        self.silence_threshold = 500      # 静音阈值（毫秒）
        self.silence_timeout_task = None       # 静音超时计时器
        
        # 音频数据队列 - 用于从回调线程向WebSocket发送线程传递数据
        self.audio_data_queue = asyncio.Queue(maxsize=100)
        
        # 任务管理
        self.tasks = set()  # 跟踪所有异步任务
        
        logger.info(f"初始化ASR客户端 ({self.asr_type})... [ 完成 ]")

    def _init_fish_audio_client(self):
        """初始化Fish Audio ASR客户端"""
        if self.asr_type == "Fish Audio":
            try:
                if not self.fish_audio_api_key:
                    logger.error("Fish Audio API Key未配置")
                    return
                
                logger.info("正在初始化Fish Audio ASR客户端...")
                from fish_audio_sdk import Session
                self.fish_audio_session = Session(self.fish_audio_api_key)
                logger.info("Fish Audio ASR客户端初始化成功")
                
            except ImportError as e:
                logger.error(f"Fish Audio SDK未安装: {e}")
            except Exception as e:
                logger.error(f"Fish Audio ASR客户端初始化失败: {e}")
        else:
            logger.info("使用本地ASR服务")
    
    def _init_doubao_client(self):
        """初始化豆包ASR客户端"""
        if self.asr_type == "豆包ASR":
            try:
                if not self.doubao_appid or not self.doubao_token:
                    logger.error("豆包ASR APPID或Token未配置")
                    return
                
                logger.info("正在初始化豆包ASR客户端...")
                self.doubao_ws_client = DoubaoASRClient(
                    appid=self.doubao_appid,
                    token=self.doubao_token,
                    cluster=self.doubao_cluster,
                    ws_url=self.doubao_ws_url,
                    language=self.doubao_language,
                    format=self.doubao_format,
                    sample_rate=self.doubao_sample_rate,
                    seg_duration=self.doubao_seg_duration,
                    resource_id=self.doubao_resource_id
                )
                logger.info("豆包ASR客户端初始化成功")
                
            except Exception as e:
                logger.error(f"豆包ASR客户端初始化失败: {e}")
        else:
            logger.info("不使用豆包ASR服务")
    
    async def setup_websocket(self):
        """设置WebSocket连接"""
        try:
            if self.websocket:
                try:
                    await self.websocket.close()
                except Exception as e:
                    logger.warning(f"- 关闭旧WebSocket连接时出错: {e}")
            
            # 连接到VAD服务
            self.websocket = await websockets.connect(self.vad_url)
            logger.info("连接VAD WebSocket... [ 完成 ]")
            
            # 添加短暂延迟，确保连接稳定
            await asyncio.sleep(0.2)
            
            self.retry_count = 0
            
            return self.websocket
        except Exception as e:
            logger.error(f"- WebSocket连接错误: {e}")
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                logger.info(f"- ASR尝试重新连接... ({self.retry_count}/{self.max_retries})")
                await asyncio.sleep(1)
                return await self.setup_websocket()
            else:
                raise e
    
    def audio_callback(self, indata, frames, time, status):
        """sounddevice音频回调函数
        
        Args:
            indata: 输入音频数据
            frames: 帧数
            time: 时间信息
            status: 状态信息
        """
        if status:
            logger.warning(f"ASR音频回调状态: {status}")
        
        # 转换音频数据
        audio_data = indata.flatten().astype(np.float32)

        # 动态缓冲区管理 - 根据录音状态调整大小
        if self.is_recording:
            # 录音时保持更长的缓冲区
            max_buffer_size = self.sample_rate * 120  # 120秒
        else:
            # 非录音时只保持短缓冲区
            max_buffer_size = self.sample_rate * 3   # 3秒
        
        # 高效的缓冲区更新
        if len(self.continuous_buffer) == 0:
            self.continuous_buffer = audio_data.copy()
        else:
            self.continuous_buffer = np.concatenate([
                self.continuous_buffer[-max_buffer_size:], 
                audio_data
            ])
        
        # 异步放入队列（非阻塞）
        if not self.is_processing_audio and not self.asr_locked:
            try:
                # 直接传递numpy数组
                self.audio_data_queue.put_nowait(audio_data.copy())
            except asyncio.QueueFull:
                # 丢弃最旧的数据，保持实时性
                try:
                    self.audio_data_queue.get_nowait()
                    self.audio_data_queue.put_nowait(audio_data.copy())
                except asyncio.QueueEmpty:
                    pass

    async def audio_processor_task(self):
        """异步音频处理任务"""
        logger.info("启动ASR音频处理任务... [ 完成 ]")
        
        # 初始化批处理变量
        batch = bytearray()
        batch_duration = 0
        last_process_time = time.perf_counter()
        
        while not self.should_stop:
            try:
                # 检查中断标志
                if self.interrupt_flag:
                    # 清空队列
                    while not self.audio_data_queue.empty():
                        try:
                            self.audio_data_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    # 重置批次
                    batch = bytearray()
                    batch_duration = 0
                    last_process_time = time.perf_counter()
                    self.interrupt_flag = False
                    continue
                
                # 动态批处理 - 基于时间和大小
                current_time = time.perf_counter()
                time_elapsed = current_time - last_process_time
                
                # 处理队列中的所有可用数据
                while not self.audio_data_queue.empty():
                    try:
                        data = self.audio_data_queue.get_nowait()
                        batch.extend(data)
                        batch_duration += len(data) / self.sample_rate
                        
                        # 达到批处理条件：100ms或50%的缓冲区
                        if batch_duration >= 0.1 or time_elapsed >= 0.05:
                            break
                    except asyncio.QueueEmpty:
                        break
                
                # 处理批次数据
                if batch:
                    # 零复制转换
                    audio_array = np.frombuffer(batch, dtype=np.float32)
                    
                    if (self.websocket and 
                        not self.is_processing_audio and 
                        not self.asr_locked):
                        
                        try:
                            # 高效发送
                            await self.websocket.send(audio_array.tobytes())
                        except Exception as e:
                            logger.error(f"ASR发送音频失败: {e}")
                            # 快速重连
                            try:
                                self.websocket = await self.setup_websocket()
                            except Exception as reconnect_e:
                                logger.error(f"ASR重连失败: {reconnect_e}")
                    
                    # 重置批次
                    batch = bytearray()
                    batch_duration = 0
                    last_process_time = time.perf_counter()
                
                # 智能休眠 - 基于队列深度
                queue_depth = self.audio_data_queue.qsize()
                sleep_time = max(0.001, min(0.05, 0.01 * (10 / (queue_depth + 1))))
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"ASR音频处理异常: {e}")
                # 防止快速循环出错
                await asyncio.sleep(0.1)
        
        logger.info("音频处理引擎... [ 已停止 ]")

    async def websocket_listener(self):
        """WebSocket监听器"""
        logger.info("启动WebSocket监听器... [ 完成 ]")
        
        while not self.should_stop:
            try:
                if not self.websocket:
                    logger.info("连接/重连VAD WebSocket...")
                    self.websocket = await self.setup_websocket()
                
                message = await self.websocket.recv()
                data = json.loads(message)
                is_speaking = data.get("is_speech", False)
                
                # 添加调试日志
                if is_speaking:
                    logger.debug("VAD检测到语音")
                
                # 如果ASR被锁定，则忽略所有VAD输入
                if self.is_processing_audio or self.asr_locked:
                    if is_speaking:
                        logger.debug("ASR已锁定，忽略VAD输入")
                    continue
                
                if is_speaking:
                    await self.handle_speech()
                else:
                    await self.handle_silence()
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("VAD WebSocket连接关闭")
                await asyncio.sleep(1)
                try:
                    self.websocket = await self.setup_websocket()
                except Exception as e:
                    logger.error(f"重新连接WebSocket失败: {e}")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"WebSocket监听错误: {e}")
                await asyncio.sleep(1)

    async def handle_speech(self):
        """处理检测到的语音"""
        # 如果ASR被锁定，则忽略语音
        if self.is_processing_audio or self.asr_locked:
            return
        
        logger.debug("ASR开始处理语音输入")
        
        # 设置处理用户输入标志
        if self.event_bus:
            await self.event_bus.publish("user_speaking", {"is_speaking": True})
        
        self.last_speech_time = time.time() * 1000  # 毫秒
        
        # 取消静音超时
        if self.silence_timeout_task:
            self.silence_timeout_task.cancel()
            self.silence_timeout_task = None
        
        # 开始录音
        if not self.is_recording:
            self.is_recording = True
            # 记录当前缓冲区长度作为录音起点
            self.recording_start_time = time.time()
            # 计算预录制的样本数（0.7秒预录制）
            self.pre_record_samples = int(self.sample_rate * 0.7)
            # 确保有足够的预录制数据
            buffer_length = len(self.continuous_buffer)
            self.recording_start_index = max(0, buffer_length - self.pre_record_samples)
            logger.info(f"开始录音，缓冲区长度: {buffer_length}, 起始索引: {self.recording_start_index}")

    async def handle_silence(self):
        """处理检测到的静音"""
        # 如果ASR被锁定，则忽略静音
        if self.is_processing_audio or self.asr_locked:
            return
        
        if self.is_recording:
            current_time = time.time() * 1000  # 毫秒
            silence_duration = current_time - self.last_speech_time
            
            if not self.silence_timeout_task and silence_duration >= self.silence_threshold:
                # 创建静音超时任务
                self.silence_timeout_task = asyncio.create_task(
                    self.silence_timeout_handler()
                )
        else:
            # 如果不是在录音状态，通知事件总线
            if self.event_bus:
                await self.event_bus.publish("user_speaking", {"is_speaking": False})

    async def silence_timeout_handler(self):
        """静音超时处理器"""
        try:
            await asyncio.sleep(self.silence_threshold / 1000)  # 转换为秒
            await self.finish_recording()
        except asyncio.CancelledError:
            logger.debug("静音超时任务被取消")
        finally:
            self.silence_timeout_task = None

    async def start(self):
        """启动ASR客户端"""
        if self.is_running:
            logger.warning("ASR客户端... [ 运行中 ]")
            return
        
        self.should_stop = False
        self.is_running = True
        
        try:
            logger.info("启动ASR客户端... [ 进行中 ]")
            
            # 检查音频设备
            try:
                devices = sd.query_devices()
                logger.info(f"- ASR可用音频设备数量: {len(devices)}")
                
                # 找到默认输入设备
                default_input = sd.default.device[0] if sd.default.device[0] is not None else 0
                logger.info(f"- ASR默认输入设备: {devices[default_input]['name']}")
            except Exception as e:
                logger.warning(f"- 检查音频设备失败: {e}")
            
            # 启动音频流
            logger.info("ASR启动音频流... [ 进行中 ]")
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.block_size,
                callback=self.audio_callback
            )
            self.audio_stream.start()
            logger.info("ASR启动音频流... [ 成功 ]")
            
            # 启动异步任务
            logger.info("ASR启动异步处理任务... [ 成功 ]")
            audio_task = asyncio.create_task(self.audio_processor_task())
            websocket_task = asyncio.create_task(self.websocket_listener())
            
            # 跟踪任务
            self.tasks.add(audio_task)
            self.tasks.add(websocket_task)
            
            # 任务完成后自动清理
            audio_task.add_done_callback(lambda t: self.tasks.discard(t))
            websocket_task.add_done_callback(lambda t: self.tasks.discard(t))
            
            logger.info("启动ASR客户端... [ 完成 ]")
            
            # 等待一下确保所有组件都启动
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"- 启动ASR客户端失败: {e}")
            await self.stop()
            raise e
    
    def interrupt(self):
        """中断当前ASR识别，但保持连接"""
        self.interrupt_flag = True
        logger.info("ASR识别已被中断")
    
    async def stop(self):
        """停止ASR客户端"""
        if not self.is_running:
            return
        
        self.should_stop = True
        self.is_running = False
        
        logger.info("停止ASR客户端... [ 进行中 ]")
        
        # 停止音频流
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception as e:
                logger.warning(f"- ASR关闭音频流时出错: {e}")
            self.audio_stream = None
        
        # 取消所有任务
        for task in list(self.tasks):
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # 取消静音超时任务
        if self.silence_timeout_task:
            self.silence_timeout_task.cancel()
            self.silence_timeout_task = None
        
        # 关闭WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"- ASR关闭WebSocket时出错: {e}")
            self.websocket = None
        
        # 清空队列
        while not self.audio_data_queue.empty():
            try:
                self.audio_data_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self.is_recording = False
        logger.info("ASR客户端... [ 已停止 ]")

    async def finish_recording(self):
        """结束录音并处理录音数据"""
        if not self.is_recording or self.is_processing_audio or self.asr_locked:
            return
        
        self.is_recording = False
        
        # 在开始处理录音时锁定ASR
        self.asr_locked = True
        logger.info("ASR锁定：开始处理录音")
        
        try:
            # 改进的音频片段提取
            current_buffer_length = len(self.continuous_buffer)
            
            # 确保录音起始点有效
            actual_start_index = max(0, min(self.recording_start_index, current_buffer_length - 1))
            
            # 提取完整的录音片段
            recorded_samples = self.continuous_buffer[actual_start_index:current_buffer_length].copy()
            
            # 检查录音质量
            duration = len(recorded_samples) / self.sample_rate
            logger.info(f"录音时长: {duration:.2f}秒, 样本数: {len(recorded_samples)}")
            
            # 音频质量检查
            if len(recorded_samples) > self.sample_rate * 0.3:  # 至少0.3秒
                # 音频预处理 - 去除静音段
                processed_samples = self._remove_silence(recorded_samples)
                
                if len(processed_samples) > self.sample_rate * 0.2:  # 处理后至少0.2秒
                    wav_blob = self.float32_to_wav(processed_samples)
                    logger.info(f"发送音频到ASR服务，大小: {len(wav_blob)}字节")
                    await self.process_recording(wav_blob)
                else:
                    logger.info("处理后录音太短，丢弃")
                    self._unlock_asr()
            else:
                logger.info("录音太短，丢弃")
                self._unlock_asr()
        
        finally:
            # 清理缓存 - 只保留最近的少量数据
            self._cleanup_audio_buffer()

    def _remove_silence(self, audio_data, threshold=0.01):
        """移除音频开头和结尾的静音段"""
        # 计算音频能量
        energy = np.abs(audio_data)
        
        # 找到开始和结束的非静音位置
        start_idx = 0
        end_idx = len(audio_data)
        
        # 从开头找到第一个非静音位置
        for i in range(len(energy)):
            if energy[i] > threshold:
                start_idx = max(0, i - int(0.1 * self.sample_rate))  # 保留0.1秒缓冲
                break
        
        # 从结尾找到最后一个非静音位置
        for i in range(len(energy) - 1, -1, -1):
            if energy[i] > threshold:
                end_idx = min(len(audio_data), i + int(0.1 * self.sample_rate))  # 保留0.1秒缓冲
                break
        
        return audio_data[start_idx:end_idx]

    def _cleanup_audio_buffer(self):
        """清理音频缓冲区"""
        # 只保留最近1秒的数据作为下次的预录制
        keep_samples = self.sample_rate * 1
        if len(self.continuous_buffer) > keep_samples:
            self.continuous_buffer = self.continuous_buffer[-keep_samples:].copy()
        
        logger.debug(f"缓冲区清理完成，保留样本数: {len(self.continuous_buffer)}")

    def _unlock_asr(self):
        """解锁ASR并通知事件总线"""
        self.asr_locked = False
        if self.event_bus:
            asyncio.create_task(self.event_bus.publish("user_speaking", {"is_speaking": False}))

    def float32_to_wav(self, samples):
        """将float32音频数据转换为WAV格式
        
        Args:
            samples: float32格式的音频数据
            
        Returns:
            WAV格式的音频数据
        """
        # 转换为int16
        samples = (samples * 32767).astype(np.int16)
        
        # 创建WAV文件
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())
        
        return buffer.getvalue()
    
    async def process_recording(self, audio_blob):
        """处理录音数据并发送到ASR服务
        
        Args:
            audio_blob: WAV格式的音频数据
        """
        try:
            if self.asr_type == "Fish Audio":
                return await self._process_with_fish_audio(audio_blob)
            elif self.asr_type == "豆包ASR":
                return await self._process_with_doubao_asr(audio_blob)
            else:
                return await self._process_with_local_asr(audio_blob)
        
        except Exception as e:
            logger.error(f"处理录音失败: {e}")
        
        finally:
            self._unlock_asr()
            # 清理音频数据
            self._cleanup_audio_queue()

    async def _process_with_fish_audio(self, audio_blob):
        """使用Fish Audio进行语音识别"""
        try:
            if not self.fish_audio_session:
                logger.error("Fish Audio ASR客户端未初始化")
                return None
            
            logger.info("开始Fish Audio语音识别...")
            
            # 导入Fish Audio ASR相关类
            from fish_audio_sdk import ASRRequest
            
            # 创建ASR请求
            asr_request = ASRRequest(
                audio=audio_blob,
                language=self.fish_audio_language,
                ignore_timestamps=self.fish_audio_ignore_timestamps
            )
            
            # 发送识别请求
            response = self.fish_audio_session.asr(asr_request)
            
            # 处理响应
            recognized_text = response.text.strip()
            logger.info(f"Fish Audio识别结果: {recognized_text}")
            
            # 记录时间戳信息（如果有）
            if hasattr(response, 'segments') and response.segments:
                logger.debug("识别时间戳:")
                for segment in response.segments:
                    logger.debug(f"  {segment.text} ({segment.start:.2f}s - {segment.end:.2f}s)")
            
            # 通知事件总线
            if self.event_bus:
                await self.event_bus.publish("speech_recognized", {"text": recognized_text})
            
            return recognized_text
            
        except Exception as e:
            logger.error(f"Fish Audio ASR失败: {e}")
            return None

    async def _process_with_local_asr(self, audio_blob):
        """使用本地ASR服务进行语音识别"""
        try:
            # 使用连接池优化HTTP请求
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', 
                            audio_blob, 
                            filename='recording.wav',
                            content_type='audio/wav')
                
                async with session.post(self.asr_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get("status") == "success" and result.get("text"):
                            recognized_text = result.get("text").strip()
                            logger.info(f"本地ASR识别结果: {recognized_text}")
                            
                            # 通知事件总线
                            if self.event_bus:
                                await self.event_bus.publish("speech_recognized", {"text": recognized_text})
                            
                            return recognized_text
                        else:
                            logger.error(f"本地ASR失败: {result.get('message', '未知错误')}")
                    else:
                        logger.error(f"本地ASR请求失败: {response.status}")
                        response_text = await response.text()
                        logger.error(f"响应内容: {response_text}")
        
        except asyncio.TimeoutError:
            logger.error("本地ASR请求超时")
        except Exception as e:
            logger.error(f"本地ASR处理失败: {e}")
        
        return None

    async def _process_with_doubao_asr(self, audio_blob):
        """使用豆包ASR进行语音识别"""
        try:
            if not self.doubao_ws_client:
                logger.error("豆包ASR客户端未初始化")
                return None
            
            logger.info("开始豆包ASR语音识别...")
            
            # 调用豆包ASR客户端进行识别
            result = await self.doubao_ws_client.recognize_audio(audio_blob)
            
            if result and 'payload_msg' in result:
                payload = result['payload_msg']
                
                if payload.get('code') == self.doubao_ws_client.success_code:
                    # 提取识别结果
                    utterances = payload.get('result', [])
                    recognized_text = ""
                    
                    for utterance in utterances:
                        if utterance.get('text'):
                            recognized_text += utterance['text']
                    
                    recognized_text = recognized_text.strip()
                    
                    if recognized_text:
                        logger.info(f"豆包ASR识别结果: {recognized_text}")
                        
                        # 通知事件总线
                        if self.event_bus:
                            await self.event_bus.publish("speech_recognized", {"text": recognized_text})
                        
                        return recognized_text
                    else:
                        logger.warning("豆包ASR未识别到有效文本")
                else:
                    logger.error(f"豆包ASR失败: {payload}")
            else:
                logger.error(f"豆包ASR响应异常: {result}")
        
        except Exception as e:
            logger.error(f"豆包ASR处理失败: {e}")
        
        return None

    def _cleanup_audio_queue(self):
        """清理音频队列"""
        while not self.audio_data_queue.empty():
            try:
                self.audio_data_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.debug("音频队列清理完成")
    
    def pause_recording(self):
        """暂停录音 - 在TTS播放时调用"""
        self.is_processing_audio = True
        logger.info("ASR录音已暂停")
    
    def resume_recording(self):
        """恢复录音 - 在TTS播放结束时调用"""
        self.is_processing_audio = False
        
        # 解锁ASR
        self.asr_locked = False
        logger.info("ASR录音已恢复，ASR已解锁")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.stop()
    
    def __del__(self):
        """析构函数 - 清理资源"""
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except:
                pass


class DoubaoASRClient:
    """豆包ASR WebSocket客户端 - 基于SAUC协议"""

    def __init__(self, appid, token, cluster, ws_url, language="zh-CN",
                 format="wav", sample_rate=16000, seg_duration=15000, resource_id="volc.bigasr.sauc.duration"):
        self.appid = appid
        self.token = token
        self.cluster = cluster
        self.ws_url = ws_url
        self.language = language
        self.format = format
        self.sample_rate = sample_rate
        self.seg_duration = seg_duration
        self.resource_id = resource_id or "volc.bigasr.sauc.duration"
        self.success_code = 1000
        self.uid = "doubao_asr_client"
        self.session = None
        self.conn = None
        self.seq = 1
        
    def generate_header(self, version=PROTOCOL_VERSION, message_type=CLIENT_FULL_REQUEST,
                       message_type_specific_flags=NO_SEQUENCE, serial_method=JSON,
                       compression_type=GZIP, reserved_data=0x00, extension_header=bytes()):
        """生成协议头"""
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header

    def parse_response(self, res):
        """解析响应"""
        protocol_version = res[0] >> 4
        header_size = res[0] & 0x0f
        message_type = res[1] >> 4
        message_type_specific_flags = res[1] & 0x0f
        serialization_method = res[2] >> 4
        message_compression = res[2] & 0x0f
        reserved = res[3]
        header_extensions = res[4:header_size * 4]
        payload = res[header_size * 4:]
        result = {}
        payload_msg = None
        payload_size = 0
        
        if message_type == SERVER_FULL_RESPONSE:
            payload_size = int.from_bytes(payload[:4], "big", signed=True)
            payload_msg = payload[4:]
        elif message_type == SERVER_ACK:
            seq = int.from_bytes(payload[:4], "big", signed=True)
            result['seq'] = seq
            if len(payload) >= 8:
                payload_size = int.from_bytes(payload[4:8], "big", signed=False)
                payload_msg = payload[8:]
        elif message_type == SERVER_ERROR_RESPONSE:
            code = int.from_bytes(payload[:4], "big", signed=False)
            result['code'] = code
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
            
        if payload_msg is None:
            return result
            
        if message_compression == GZIP:
            payload_msg = gzip.decompress(payload_msg)
        if serialization_method == JSON:
            payload_msg = json.loads(str(payload_msg, "utf-8"))
        elif serialization_method != NO_SERIALIZATION:
            payload_msg = str(payload_msg, "utf-8")
            
        result['payload_msg'] = payload_msg
        result['payload_size'] = payload_size
        return result

    def construct_request(self, reqid):
        """构建请求"""
        logger.info(f"构建请求 - appid: {self.appid}, cluster: {self.cluster}, resource_id: {self.resource_id}")
        req = {
            'app': {
                'appid': self.appid,
                'cluster': self.cluster,
                'token': self.token
            },
            'user': {
                'uid': self.uid
            },
            'request': {
                'reqid': reqid,
                'nbest': 1,
                'workflow': 'audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate',
                'show_language': False,
                'show_utterances': False,
                'result_type': 'full',
                "sequence": 1
            },
            'audio': {
                'format': self.format,
                'rate': self.sample_rate,
                'language': self.language,
                'bits': 16,
                'channel': 1,
                'codec': 'raw'
            }
        }
        
        return req

    @staticmethod
    def slice_data(data: bytes, chunk_size: int):
        """切分数据"""
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset: offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset: data_len], True

    def token_auth(self):
        """Token认证 - 使用SAUC格式"""
        logger.info("生成SAUC协议认证头...")
        logger.info(f"APP ID: {self.appid}")
        logger.info(f"Token: {self.token[:10]}..." if self.token else "Token: None")
        logger.info(f"Resource ID: {self.resource_id}")

        headers = RequestBuilder.new_auth_headers(self.appid, self.token, self.resource_id)

        logger.info("认证头生成完成")
        logger.info(f"X-Api-App-Key: {headers.get('X-Api-App-Key', 'None')}")
        logger.info(f"X-Api-Access-Key: {headers.get('X-Api-Access-Key', 'None')[:10]}..." if headers.get('X-Api-Access-Key') else "X-Api-Access-Key: None")
        logger.info(f"X-Api-Resource-Id: {headers.get('X-Api-Resource-Id', 'None')}")
        logger.info(f"X-Api-Request-Id: {headers.get('X-Api-Request-Id', 'None')}")

        return headers

    async def __aenter__(self):
        logger.info("创建aiohttp会话...")
        self.session = aiohttp.ClientSession()
        logger.info("aiohttp会话创建成功")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logger.info("清理ASR客户端资源...")
        if self.conn and not self.conn.closed:
            logger.info("关闭WebSocket连接...")
            await self.conn.close()
            logger.info("WebSocket连接已关闭")
        if self.session and not self.session.closed:
            logger.info("关闭aiohttp会话...")
            await self.session.close()
            logger.info("aiohttp会话已关闭")

    async def create_connection(self) -> None:
        """创建WebSocket连接"""
        logger.info("开始创建WebSocket连接...")
        logger.info(f"目标URL: {self.ws_url}")

        headers = self.token_auth()
        logger.info("生成认证头...")
        logger.info(f"认证头: {headers}")

        try:
            logger.info("正在连接到WebSocket服务器...")
            self.conn = await self.session.ws_connect(
                self.ws_url,
                headers=headers
            )
            logger.info(f"✅ WebSocket连接成功建立: {self.ws_url}")
            logger.info(f"连接状态: {self.conn.closed}")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"❌ 网络连接错误: {e}")
            logger.error(f"请检查网络连接和URL: {self.ws_url}")
            raise
        except aiohttp.WSServerHandshakeError as e:
            logger.error(f"❌ WebSocket握手错误: {e}")
            logger.error(f"服务器可能拒绝连接，请检查认证信息")
            raise
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"URL: {self.ws_url}")
            logger.error(f"Headers: {headers}")
            raise

    async def send_full_client_request(self) -> None:
        """发送完整客户端请求"""
        logger.info("准备发送完整客户端请求...")
        logger.info(f"当前序列号: {self.seq}")

        request = RequestBuilder.new_full_client_request(self.seq, self.uid, self.sample_rate)
        logger.info(f"构建的请求大小: {len(request)} bytes")
        logger.info(f"采样率: {self.sample_rate}, UID: {self.uid}")

        self.seq += 1
        logger.info(f"序列号递增为: {self.seq}")

        try:
            logger.info("正在发送完整客户端请求...")
            await self.conn.send_bytes(request)
            logger.info(f"✅ 完整客户端请求发送成功 (seq: {self.seq-1})")

            logger.info("等待服务器响应...")
            msg = await self.conn.receive()
            logger.info(f"收到服务器消息，类型: {msg.type}")

            if msg.type == aiohttp.WSMsgType.BINARY:
                response = ResponseParser.parse_response(msg.data)
                logger.info("✅ 服务器响应解析成功")
                logger.info(f"响应详情: {response.to_dict()}")
            else:
                logger.error(f"❌ 意外的消息类型: {msg.type}")
                if hasattr(msg, 'data'):
                    logger.error(f"消息数据: {msg.data}")
        except Exception as e:
            logger.error(f"❌ 发送完整客户端请求失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            raise

    async def send_audio_segments(self, segments: List[bytes]) -> AsyncGenerator[None, None]:
        """发送音频段"""
        total_segments = len(segments)
        logger.info(f"开始发送音频段，共 {total_segments} 个段")

        for i, segment in enumerate(segments):
            segment_num = i + 1
            is_last = (i == len(segments) - 1)

            logger.info(f"准备发送音频段 {segment_num}/{total_segments}")
            logger.info(f"段大小: {len(segment)} bytes, 是否最后一段: {is_last}")

            request = RequestBuilder.new_audio_only_request(
                self.seq,
                segment,
                is_last=is_last
            )

            logger.info(f"构建的音频请求大小: {len(request)} bytes")

            try:
                logger.info(f"正在发送音频段 (seq: {self.seq})...")
                await self.conn.send_bytes(request)
                logger.info(f"✅ 音频段 {segment_num} 发送成功 (seq: {self.seq}, last: {is_last})")

                if not is_last:
                    self.seq += 1
                    logger.info(f"序列号递增为: {self.seq}")

                # 等待一段时间再发送下一个段
                wait_time = self.seg_duration / 1000
                logger.info(f"等待 {wait_time:.2f} 秒后发送下一个段...")
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"❌ 发送音频段 {segment_num} 失败: {e}")
                logger.error(f"错误类型: {type(e).__name__}")
                raise

            yield

    async def receive_responses(self) -> AsyncGenerator[AsrResponse, None]:
        """接收响应"""
        logger.info("开始监听WebSocket响应...")

        try:
            async for msg in self.conn:
                logger.info(f"📨 收到WebSocket消息，类型: {msg.type}")

                if msg.type == aiohttp.WSMsgType.BINARY:
                    logger.info("解析二进制消息...")
                    response = ResponseParser.parse_response(msg.data)
                    logger.info("✅ 响应解析成功")
                    logger.info(f"响应详情: {response.to_dict()}")

                    # 检查响应状态
                    if response.code != 0:
                        logger.warning(f"⚠️ 服务器返回错误码: {response.code}")

                    if response.is_last_package:
                        logger.info("📦 收到最后一个数据包")

                    yield response

                    # 只有在错误或连接关闭时才break
                    if response.code != 0:
                        logger.info("由于错误响应，结束接收")
                        break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"❌ WebSocket错误: {msg.data}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("🔌 WebSocket连接已关闭")
                    break
                else:
                    logger.warning(f"⚠️ 未知消息类型: {msg.type}")
                    if hasattr(msg, 'data'):
                        logger.info(f"消息数据: {msg.data}")

        except Exception as e:
            logger.error(f"❌ 接收消息时出错: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            raise

    @staticmethod
    def split_audio(data: bytes, segment_size: int) -> List[bytes]:
        """分割音频数据"""
        if segment_size <= 0:
            return []

        segments = []
        for i in range(0, len(data), segment_size):
            end = i + segment_size
            if end > len(data):
                end = len(data)
            segments.append(data[i:end])
        return segments

    def get_segment_size(self, content: bytes) -> int:
        """计算分段大小"""
        logger.info("🔍 开始计算音频分段大小...")
        logger.info(f"音频文件大小: {len(content)} bytes")

        try:
            # 简单的WAV解析
            if len(content) < 44:
                logger.warning("⚠️ WAV文件头不完整，使用默认分段大小")
                # 使用默认分段大小：采样率 * 通道数 * 位深度/8 * 时间(ms)/1000
                default_size = self.sample_rate * 1 * 2 * (self.seg_duration // 1000)
                logger.info(f"默认分段大小: {default_size} bytes (采样率: {self.sample_rate}, 时长: {self.seg_duration}ms)")
                return default_size

            # 解析WAV头
            sample_rate = struct.unpack('<I', content[24:28])[0]
            bits_per_sample = struct.unpack('<H', content[34:36])[0]
            num_channels = struct.unpack('<H', content[22:24])[0]

            logger.info("✅ WAV文件解析成功:")
            logger.info(f"  • 采样率: {sample_rate} Hz")
            logger.info(f"  • 位深度: {bits_per_sample} bits")
            logger.info(f"  • 通道数: {num_channels}")

            # 计算每秒字节数
            bytes_per_second = sample_rate * num_channels * (bits_per_sample // 8)
            logger.info(f"每秒字节数: {bytes_per_second}")

            # 计算分段大小（毫秒转换为秒）
            segment_size = bytes_per_second * (self.seg_duration // 1000)
            logger.info(f"✅ 计算分段大小: {segment_size} bytes")
            logger.info(f"分段时间: {self.seg_duration} ms")

            return segment_size
        except Exception as e:
            logger.error(f"❌ 计算分段大小失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            # 返回默认分段大小
            default_size = self.sample_rate * 1 * 2 * (self.seg_duration // 1000)
            logger.info(f"使用默认分段大小: {default_size} bytes")
            return default_size

    async def segment_data_processor(self, wav_data: bytes, segment_size: int):
        """分段处理音频数据 - 使用SAUC协议"""
        logger.info("🚀 开始SAUC协议音频处理")
        logger.info(f"音频数据大小: {len(wav_data)} bytes")
        logger.info(f"分段大小: {segment_size} bytes")

        self.seq = 1
        logger.info("重置序列号为: 1")

        try:
            logger.info("步骤1: 创建WebSocket连接")
            await self.create_connection()

            logger.info("步骤2: 发送完整客户端请求")
            await self.send_full_client_request()

            logger.info("步骤3: 分割音频数据")
            segments = self.split_audio(wav_data, segment_size)
            logger.info(f"音频分割完成，共 {len(segments)} 个段")

            logger.info("步骤4: 启动发送和接收任务")
            async def sender():
                logger.info("启动音频段发送任务")
                async for _ in self.send_audio_segments(segments):
                    pass
                logger.info("音频段发送任务完成")

            sender_task = asyncio.create_task(sender())
            logger.info("发送任务已启动")

            try:
                logger.info("开始监听服务器响应...")
                final_result = None
                async for response in self.receive_responses():
                    logger.info(f"处理响应: is_last={response.is_last_package}, code={response.code}")

                    if response.payload_msg:
                        logger.info("响应包含有效数据，开始解析文本")

                        # 检查result.text或直接的text字段
                        text = ''
                        if 'result' in response.payload_msg and 'text' in response.payload_msg['result']:
                            text = response.payload_msg['result']['text']
                            logger.info("从 result.text 提取文本")
                        elif 'text' in response.payload_msg:
                            text = response.payload_msg['text']
                            logger.info("从直接 text 字段提取文本")

                        if text:
                            logger.info(f"✅ 识别结果: {text}")
                            final_result = {
                                'code': response.code,
                                'text': text,
                                'payload_msg': response.payload_msg
                            }

                            # 如果是最后一个包，立即返回结果
                            if response.is_last_package:
                                logger.info("📦 收到最后一个包，返回最终结果")
                                return final_result
                        else:
                            logger.info("响应中未找到文本内容")
                    elif response.code != 0:
                        logger.error(f"❌ ASR服务器错误: {response.code}")
                        logger.error(f"错误详情: {response.payload_msg}")
                        return {
                            'code': response.code,
                            'payload_msg': response.payload_msg
                        }

                # 如果循环结束还没有返回，检查是否有结果
                if final_result:
                    logger.info("🔄 响应循环结束，返回最终结果")
                    return final_result
                else:
                    logger.error("❌ 未收到任何识别结果")
                    return {
                        'code': -1,
                        'error': 'No recognition result received'
                    }

            finally:
                logger.info("清理发送任务...")
                sender_task.cancel()
                try:
                    await sender_task
                    logger.info("发送任务清理完成")
                except asyncio.CancelledError:
                    logger.info("发送任务已被取消")

        except Exception as e:
            logger.error(f"❌ SAUC协议处理失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")
            return {
                'code': -1,
                'error': str(e)
            }
        finally:
            logger.info("清理WebSocket连接...")
            if self.conn:
                await self.conn.close()
                logger.info("WebSocket连接已清理")

    async def recognize_audio(self, audio_data: bytes):
        """识别音频数据"""
        logger.info("🎤 开始音频识别处理")
        logger.info(f"输入音频大小: {len(audio_data)} bytes")

        try:
            # 计算分段大小
            logger.info("计算音频分段参数...")
            segment_size = self.get_segment_size(audio_data)
            logger.info(f"✅ 分段大小计算完成: {segment_size} bytes")

            logger.info("启动SAUC协议客户端...")
            async with self as client:
                logger.info("SAUC客户端启动成功，开始处理音频")
                result = await self.segment_data_processor(audio_data, segment_size)

                if result and 'text' in result:
                    logger.info(f"🎉 识别成功! 文本: {result['text']}")
                elif result and 'error' in result:
                    logger.error(f"❌ 识别失败: {result['error']}")
                else:
                    logger.warning("⚠️ 识别结果异常")

                return result

        except Exception as e:
            logger.error(f"❌ 音频识别失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            return {
                'code': -1,
                'error': str(e)
            }