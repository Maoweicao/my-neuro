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
        
        # 从配置中读取VAD和ASR服务的URL
        self.vad_url = config.get("asr", {}).get("vad_url", "ws://localhost:6006/v1/ws/vad")
        self.asr_url = config.get("asr", {}).get("asr_url", "http://localhost:6006/v1/upload_audio")
        
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
        
        logger.info("初始化ASR客户端... [ 完成 ]")
    
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
        """处理录音数据并发送到ASR服务 - 使用aiohttp异步请求
        
        Args:
            audio_blob: WAV格式的音频数据
        """
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
                            logger.info(f"用户: {recognized_text}")
                            
                            # 通知事件总线
                            if self.event_bus:
                                await self.event_bus.publish("speech_recognized", {"text": recognized_text})
                            
                            return recognized_text
                        else:
                            logger.error(f"ASR失败: {result.get('message', '未知错误')}")
                    else:
                        logger.error(f"ASR请求失败: {response.status}")
                        response_text = await response.text()
                        logger.error(f"响应内容: {response_text}")
        
        except asyncio.TimeoutError:
            logger.error("ASR请求超时")
        except Exception as e:
            logger.error(f"处理录音失败: {e}")
        
        finally:
            self._unlock_asr()
            # 清理音频数据
            self._cleanup_audio_queue()

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