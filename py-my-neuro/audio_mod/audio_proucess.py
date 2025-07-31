from queue import Queue
import pygame
from io import BytesIO
import requests
import time
import threading
import tempfile
import os
import keyboard
import wave
import logging

logger = logging.getLogger("audio_player")

class AudioProcess:

    def tts_inference(self, text):
        """只做TTS推理，返回音频数据"""
        data = {'text': text, 'text_language': 'zh'}
        url = 'http://127.0.0.1:5000'
        response = requests.post(url, json=data)
        return response.content

    def get_audio_duration(self, audio_data):
        """获取音频时长"""
        try:
            # 将音频数据写入临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            # 读取音频文件获取时长
            with wave.open(temp_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate

            # 清理临时文件
            os.remove(temp_path)
            return duration
        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return 0.0

    def play_audio(self, audio_data):
        """只播放音频数据"""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        audio_buffer = BytesIO(audio_data)
        pygame.mixer.init()
        pygame.mixer.music.load(audio_buffer)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    def play_merge_audio(self, text):
        """输入文本播放音频"""
        audio_data = self.tts_inference(text)
        self.play_audio(audio_data)


class AudioPlayer:

    def __init__(self, live_model=None, emotion_handler=None):
        self.audio_process = AudioProcess()
        self.text_queue = Queue()
        self.audio_queue = Queue()
        self.text_buffer = ''
        self.punc = {',', '，', '。', '！', '!', '?'}
        self.stream_text = None
        self.live_model = live_model  # Live2D模型引用
        self.emotion_handler = emotion_handler  # 情绪处理器引用
        self.is_interrupted = False  # 打断标志位
        
        # 新增：同步相关
        self.sync_data_queue = Queue()  # 存储同步数据的队列
        
        self.start_tts_thread()
        keyboard.add_hotkey('ctrl+i', self.interrupt_audio)

    def clear_queue(self):
        """清空所有队列"""
        while not self.text_queue.empty():
            self.text_queue.get()
        while not self.audio_queue.empty():
            self.audio_queue.get()
        while not self.sync_data_queue.empty():
            self.sync_data_queue.get()

    def interrupt_audio(self):
        """打断操作"""
        print("🔇 音频被打断")
        pygame.mixer.music.stop()  # 停止当前播放
        self.clear_queue()  # 清空队列
        self.is_interrupted = True  # 设置打断标志
        
        # 停止情绪同步
        if self.emotion_handler:
            self.emotion_handler.stop_audio_sync()

    def cut_text(self, ai_content):
        """处理流式文本输入"""
        self.is_interrupted = False  # 开始新对话时重置打断状态
        for char in ai_content:
            if self.is_interrupted:  # 检查是否被打断
                break
            self.text_buffer += char
            if char in self.punc:
                # 处理包含情绪标签的文本段落
                self.process_text_segment(self.text_buffer)
                self.text_buffer = ''

    def finish_current_text(self):
        """在AI回复完全结束时调用，处理剩余文本"""
        if self.text_buffer.strip() and not self.is_interrupted:
            # 处理最后一段文本
            self.process_text_segment(self.text_buffer.strip())
            self.text_buffer = ''

    def process_text_segment(self, text_segment):
        """
        处理文本段落，提取情绪标签并准备同步数据
        
        Args:
            text_segment: 文本段落
        """
        if not text_segment.strip():
            return
        
        # 如果有情绪处理器，预处理文本
        if self.emotion_handler:
            processed_data = self.emotion_handler.prepare_text_for_audio(text_segment)
            clean_text = processed_data['clean_text']
            emotion_markers = processed_data['emotion_markers']
            
            # 将文本和情绪标记信息一起放入队列
            sync_data = {
                'original_text': text_segment,
                'clean_text': clean_text,
                'emotion_markers': emotion_markers
            }
            self.sync_data_queue.put(sync_data)
            
            # 静默处理，不输出日志
        else:
            # 没有情绪处理器，直接处理
            sync_data = {
                'original_text': text_segment,
                'clean_text': text_segment,
                'emotion_markers': []
            }
            self.sync_data_queue.put(sync_data)

    def run_tts(self):
        """TTS转换线程 - 从同步数据队列取数据，转换成音频"""
        while True:
            # 从同步数据队列里面取出数据
            sync_data = self.sync_data_queue.get()

            # 检查是否被打断
            if self.is_interrupted:
                continue

            clean_text = sync_data['clean_text']
            emotion_markers = sync_data['emotion_markers']

            # 使用纯文本进行TTS推理
            audio_data = self.audio_process.tts_inference(clean_text)
            
            # 获取音频时长
            audio_duration = self.audio_process.get_audio_duration(audio_data)
            
            # 将音频数据和同步信息一起放入音频队列
            audio_item = {
                'audio_data': audio_data,
                'clean_text': clean_text,
                'emotion_markers': emotion_markers,
                'audio_duration': audio_duration
            }
            
            self.audio_queue.put(audio_item)

    def play_audio_data(self):
        """音频播放线程 - 播放音频并启动情绪同步"""
        while True:
            # 从音频队列里面取出音频项
            audio_item = self.audio_queue.get()

            # 检查是否被打断
            if self.is_interrupted:
                continue

            audio_data = audio_item['audio_data']
            clean_text = audio_item['clean_text']
            emotion_markers = audio_item['emotion_markers']
            audio_duration = audio_item['audio_duration']

            try:
                # 启动情绪同步（在音频播放之前）
                if self.emotion_handler and emotion_markers:
                    self.emotion_handler.start_audio_sync(
                        clean_text, 
                        emotion_markers, 
                        audio_duration
                    )
                # 静默启动情绪同步

                # 如果有Live2D模型，启动嘴型同步
                if self.live_model:
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_path = temp_file.name

                    try:
                        self.live_model.start_lip_sync(temp_path)
                        # 播放音频
                        self.audio_process.play_audio(audio_data)
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    # 没有Live2D模型，只播放音频
                    self.audio_process.play_audio(audio_data)

                # 音频播放结束后，停止情绪同步
                if self.emotion_handler:
                    self.emotion_handler.stop_audio_sync()

            except pygame.error as e:
                # 静默跳过坏音频
                continue  # 静默跳过坏音频
            except Exception as e:
                # 静默处理错误
                # 确保停止情绪同步
                if self.emotion_handler:
                    self.emotion_handler.stop_audio_sync()

    def add_text_to_queue(self, text):
        """添加文本到队列（保留兼容性）"""
        self.is_interrupted = False
        self.process_text_segment(text)

    def start_tts_thread(self):
        """启动TTS双线程"""
        run_tts_thread = threading.Thread(target=self.run_tts, daemon=True)
        play_audio_data_thread = threading.Thread(target=self.play_audio_data, daemon=True)
        run_tts_thread.start()
        play_audio_data_thread.start()

    def set_live_model(self, live_model):
        """设置Live2D模型"""
        self.live_model = live_model

    def set_emotion_handler(self, emotion_handler):
        """设置情绪处理器"""
        self.emotion_handler = emotion_handler
