import sounddevice as sd
import numpy as np
import requests
import keyboard
import wave
import websockets.legacy.client as websockets_client
import json
import asyncio
from io import BytesIO
from queue import Queue
import threading
import time


class AudioSystem:
    def __init__(self, parent_neuro=None):
        # *** 保存MyNeuro实例的引用 ***
        self.parent_neuro = parent_neuro

        # 新增：麦克风状态控制
        self.mic_enabled = True

        # 手动录音模式
        self.manual_recording = False
        self.manual_frames = []
        self.last_result = None
        keyboard.add_hotkey('ctrl+j', self.toggle_manual)

        # VAD模式
        self.vad_audio_queue = Queue()
        self.vad_audio_frames = []
        self.vad_pre_buffer = []
        self.vad_is_recording = False
        self.vad_silence_timer = None
        self.vad_result_text = None
        self.vad_result_ready = threading.Event()
        self.vad_interrupt_audio = []
        self.vad_interrupt_detected = False
        self.vad_running = True
        self.vad_ws = None
        self.PRE_RECORD_TIME = 1
        self.PRE_BUFFER_SIZE = 16000 * self.PRE_RECORD_TIME

    def set_mic_enabled(self, enabled):
        """控制麦克风开关"""
        self.mic_enabled = enabled

    def send_audio_for_recognition(self, audio_data, is_bytes=False, print_result=False):
        """统一的音频识别函数"""
        audio_buffer = BytesIO()
        with wave.open(audio_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            if is_bytes:
                wf.writeframes(audio_data)
            else:
                wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

        files = {"file": ("audio.wav", audio_buffer.getvalue(), "audio/wav")}
        response = requests.post("http://127.0.0.1:1000/v1/upload_audio", files=files)
        text = response.json()['text']

        return text

    def toggle_manual(self):
        """手动录音开关"""
        self.manual_recording = not self.manual_recording
        if self.manual_recording:
            print("🎙️ 手动录音开始...")
            self.manual_frames = []
        else:
            print("⏹️ 手动录音停止")
            self.process_manual_audio()

    def process_manual_audio(self):
        """处理手动录音"""
        if not self.manual_frames:
            return None
        audio_data = np.concatenate(self.manual_frames, axis=0)
        result = self.send_audio_for_recognition(audio_data, is_bytes=False, print_result=True)
        self.last_result = result
        return result

    def manual_callback(self, indata, frames, time, status):
        """手动录音回调"""
        if self.manual_recording:
            self.manual_frames.append(indata.copy())

    def vad_audio_callback(self, indata, frames, time, status):
        """VAD音频回调，把数据放到队列"""
        # 检查麦克风是否启用
        if not self.mic_enabled:
            return

        audio_data = indata[:, 0].astype(np.float32)
        if len(audio_data) == 512:
            self.vad_audio_queue.put(audio_data)

    async def vad_process_audio(self):
        """VAD处理音频的异步函数"""
        uri = "ws://localhost:1000/v1/ws/vad"
        self.vad_ws = await websockets_client.connect(uri)

        while self.vad_running:
            try:
                if not self.vad_audio_queue.empty():
                    audio_data = self.vad_audio_queue.get()

                    # 发送音频数据到VAD
                    await self.vad_ws.send(audio_data.tobytes())

                    # 接收VAD结果
                    response = await self.vad_ws.recv()
                    result = json.loads(response)

                    if result["is_speech"]:
                        # 检查麦克风是否启用
                        if not self.mic_enabled:
                            continue

                        # *** 检测音频播放状态来判断是否需要打断 ***
                        import pygame
                        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                            # 只有在实时模式下才打断
                            if self.parent_neuro and self.parent_neuro.asr_real_time:
                                print("🔥🔥🔥 检测到人声，音频正在播放，立即打断！🔥🔥🔥")

                                # 停止音频播放
                                self.parent_neuro.audio_player.interrupt_audio()
                                # 也停止文本生成
                                self.parent_neuro.stop_flag = True
                                # 重置情绪处理器
                                self.parent_neuro.emotion_handler.reset_buffer()

                                print("🎤 音频已被打断，开始录制用户语音...")
                            else:
                                # 非实时模式下，忽略人声检测
                                continue
                        else:
                            # 只在第一次检测到人声时打印状态
                            if not self.vad_is_recording:
                                audio_playing = pygame.mixer.get_init() and pygame.mixer.music.get_busy() if pygame.mixer.get_init() else False
                                print(f"🎤 检测到人声! 音频播放状态: {audio_playing}")

                        if self.vad_silence_timer:
                            self.vad_silence_timer.cancel()
                            self.vad_silence_timer = None

                        if not self.vad_is_recording:
                            self.vad_is_recording = True
                            print("🎤 开始录音...")
                            # 把预录音缓冲区的数据加到录音开头
                            self.vad_audio_frames = self.vad_pre_buffer.copy()

                        # 保存音频数据
                        self.vad_audio_frames.append(audio_data.tobytes())

                    else:
                        # 检测到静音
                        if self.vad_is_recording and not self.vad_silence_timer:
                            def end_vad_recording():
                                print("🎤 录音结束，开始识别...")
                                self.vad_is_recording = False
                                current_frames = self.vad_audio_frames

                                # 合并音频数据
                                if current_frames:
                                    audio_bytes = b''.join(current_frames)
                                    # 转换为16位整数
                                    audio_float = np.frombuffer(audio_bytes, dtype=np.float32)
                                    audio_int16 = (audio_float * 32767).astype(np.int16)

                                    # 发送识别
                                    try:
                                        text = self.send_audio_for_recognition(audio_int16.tobytes(), is_bytes=True,
                                                                               print_result=False)
                                        self.vad_result_text = text
                                        print(f"📝 识别结果: {text}")

                                    except Exception as e:
                                        print(f"识别错误：{e}")
                                        self.vad_result_text = ""

                                # 清空帧缓冲
                                self.vad_audio_frames = []
                                # 触发结果就绪事件
                                self.vad_result_ready.set()

                            self.vad_silence_timer = threading.Timer(0.5, end_vad_recording)
                            self.vad_silence_timer.start()

                    # 更新预录音缓冲区（只有在麦克风启用时才更新）
                    if self.mic_enabled:
                        self.vad_pre_buffer.append(audio_data.tobytes())
                        # 保持缓冲区大小在1秒内
                        buffer_size = len(self.vad_pre_buffer) * 512
                        if buffer_size > self.PRE_BUFFER_SIZE:
                            # 移除最旧的数据
                            remove_count = (buffer_size - self.PRE_BUFFER_SIZE) // 512
                            self.vad_pre_buffer = self.vad_pre_buffer[remove_count:]

                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"VAD处理错误：{e}")
                break

        if self.vad_ws:
            await self.vad_ws.close()

    def vad_run_async_loop(self):
        """VAD在后台线程运行异步循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.vad_process_audio())

    def start_manual_mode(self):
        """启动手动录音模式"""
        print("手动模式：按 Ctrl+J 开始/停止录音")
        self.stream = sd.InputStream(callback=self.manual_callback, channels=1, samplerate=16000)
        self.stream.start()

    def stop_manual_mode(self):
        """停止手动录音模式"""
        if hasattr(self, 'stream'):
            self.stream.stop()

    async def start_vad_mode(self):
        """启动VAD自动检测模式"""
        # 启动录音
        self.vad_stream = sd.InputStream(callback=self.vad_audio_callback,
                                         channels=1,
                                         samplerate=16000,
                                         blocksize=512)
        self.vad_stream.start()

        # 启动异步处理线程
        async_thread = threading.Thread(target=self.vad_run_async_loop, daemon=True)
        async_thread.start()

        # 等待连接建立
        time.sleep(0.5)

    def stop_vad_mode(self):
        """停止VAD模式"""
        self.vad_running = False
        if hasattr(self, 'vad_stream'):
            self.vad_stream.stop()
            self.vad_stream.close()

    def simple_vad_detection(self):
        """简单的VAD人声检测函数，检测到人声就打印提示"""
        print("🎤 VAD人声检测模式启动...")

        # 创建音频队列用于VAD检测
        detection_queue = Queue()

        # 添加状态跟踪，避免重复打印
        is_currently_speaking = False

        def detection_callback(indata, frames, time, status):
            """音频回调函数"""
            audio_data = indata[:, 0].astype(np.float32)
            if len(audio_data) == 512:
                detection_queue.put(audio_data)

        async def vad_detection_process():
            """VAD检测处理"""
            nonlocal is_currently_speaking
            uri = "ws://localhost:1000/v1/ws/vad"
            detection_ws = await websockets_client.connect(uri)

            try:
                while True:
                    if not detection_queue.empty():
                        audio_data = detection_queue.get()

                        # 发送音频数据到VAD
                        await detection_ws.send(audio_data.tobytes())

                        # 接收VAD结果
                        response = await detection_ws.recv()
                        result = json.loads(response)

                        if result["is_speech"]:
                            # 只有从静音状态转换到说话状态时才打印
                            if not is_currently_speaking:
                                print("出现了人声！")
                                is_currently_speaking = True
                        else:
                            # 检测到静音，重置状态
                            is_currently_speaking = False

                    await asyncio.sleep(0.01)

            except KeyboardInterrupt:
                print("\n检测停止")
            finally:
                await detection_ws.close()

        def run_detection():
            """运行检测的异步循环"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(vad_detection_process())

        # 启动录音流
        detection_stream = sd.InputStream(callback=detection_callback,
                                          channels=1,
                                          samplerate=16000,
                                          blocksize=512)
        detection_stream.start()

        # 启动异步处理线程
        detection_thread = threading.Thread(target=run_detection, daemon=True)
        detection_thread.start()

        try:
            print("人声检测运行中，按 Ctrl+C 停止...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止人声检测...")
            detection_stream.stop()
            detection_stream.close()

    def key_asr(self):
        while True:
            self.last_result = None
            self.start_manual_mode()
            # 等待用户录音完成后获取结果
            while not self.last_result:
                time.sleep(0.1)
            result_text = self.last_result
            print(f"你: {result_text}")
            self.stop_manual_mode()
            return result_text

    def vad_asr(self):
        """VAD ASR主函数 - 每次调用都重新初始化状态"""
        # 如果麦克风被禁用，等待启用
        while not self.mic_enabled:
            print("🔇 麦克风已禁用，等待启用...")
            time.sleep(0.5)

        # 重置所有状态
        self.vad_result_text = None
        self.vad_result_ready.clear()
        self.vad_is_recording = False
        self.vad_audio_frames = []
        self.vad_running = True

        # 清空队列
        while not self.vad_audio_queue.empty():
            self.vad_audio_queue.get()

        # 启动VAD模式
        asyncio.run(self.start_vad_mode())
        print('🎤 VAD模式：开始录音，自动检测说话！')

        # 等待录音结果
        self.vad_result_ready.wait()
        result_text = self.vad_result_text

        # 停止VAD模式
        self.stop_vad_mode()

        return result_text


# 使用示例
if __name__ == "__main__":
    # 选择模式
    audio = AudioSystem()

    # 选择模式
    mode = input("选择模式 (1: 手动录音, 2: VAD自动, 3: 简单人声检测): ")

    if mode == "1":
        while True:
            audio.last_result = None
            audio.start_manual_mode()
            # 等待用户录音完成后获取结果
            while not audio.last_result:
                time.sleep(0.1)
            result_text = audio.last_result
            print(f"获取到的文本: {result_text}")
            audio.stop_manual_mode()
            # 可选：添加退出机制
            if input("继续? (y/n): ").lower() != 'y':
                break
    elif mode == "2":
        while True:
            result_text = audio.vad_asr()
            print(f"获取到的文本: {result_text}")
    elif mode == "3":
        # 新的简单人声检测模式
        audio.simple_vad_detection()
    else:
        print("无效的模式选择")
