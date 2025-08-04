# main_chat.py - 事件驱动重构版本
from ai_singing_feature import SingingSystem
from openai import OpenAI
from PIL import ImageGrab
import io
import base64
from audio_mod.audio_proucess import AudioPlayer
from audio_mod.asr_module import AudioSystem
import keyboard
import inspect
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from UI.live2d_model import Live2DModel, init_live2d, dispose_live2d
import sys
import json

from config_mod.load_config import load_config
import threading
import time

import pyperclip
import pyautogui

from stream_mod.bilibili_stream import BilibiliDanmuListener

# 导入情绪处理器
from emotion_mod.emotion_handler import EmotionHandler
from agent_mod.fc_tools import MyNuroTools

from UI.typing_box import start_gui_with_ai

from bert_mod import Bert_panduan

# 导入事件总线
try:
    from UI.simple_event_bus import event_bus, Events

    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False
    print("未找到事件总线，使用传统模式")


class MyNeuro:

    def __init__(self):
        # 初始化配置
        self.config = load_config()
        self.bert = Bert_panduan()

        # API配置
        API_KEY = self.config['api']['api_key']
        API_URL = self.config['api']['api_url']
        self.model = self.config['api']['model']
        self.client = OpenAI(api_key=API_KEY, base_url=API_URL)

        self.messages = [{
            'role': 'system', 'content': self.config['api']['system_prompt']
        }]

        # 各种配置
        self.cut_text_tts = self.config['features']['cut_text_tts']
        self.interval = self.config['inputs']['auto_chat']['interval']
        self.audo_chat = self.config['inputs']['auto_chat']['enabled']
        self.asr_real_time = self.config['inputs']['asr'].get('real_time', True)

        # 状态控制
        self.mic_enabled = True
        self.ai_is_responding = False
        self.stop_flag = False

        # 初始化Live2D
        init_live2d()
        self.app = QApplication(sys.argv)
        live_model = Live2DModel()
        live_model.show()

        # 初始化各个组件
        self.vad_input = AudioSystem(parent_neuro=self)
        self.asr_vad = self.config['inputs']['asr']['enabled']

        # 情绪处理器
        self.emotion_handler = EmotionHandler(config_path="emotion_mod/emotion_actions.json", live_model=live_model)

        # 音频播放器
        live_2d = self.config['features']['live2d']
        self.audio_player = AudioPlayer(live_model=live_model if live_2d else None,
                                        emotion_handler=self.emotion_handler)

        # 唱歌系统
        self.singing_system = SingingSystem(
            live_model=live_model if live_2d else None,
            audio_dir="KTV/output"
        )

        # Function calling
        self.function_calling_enabled = self.config['features']['function_calling']
        if self.function_calling_enabled:
            self.fc_tool = MyNuroTools(self)
        else:
            self.fc_tool = None

        # 哔哩哔哩直播
        self.listener = BilibiliDanmuListener()

        # 快捷键
        keyboard.add_hotkey('ctrl+i', self.stop_key)

        # 🔥 新增：事件驱动集成
        if HAS_EVENT_BUS:
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """设置事件处理器 - 新增"""
        # 订阅用户输入事件
        event_bus.subscribe(Events.USER_INPUT, self._handle_user_input_event)

        # 订阅音频控制事件
        event_bus.subscribe(Events.AUDIO_INTERRUPT, self._handle_audio_interrupt_event)
        event_bus.subscribe(Events.MIC_TOGGLE, self._handle_mic_toggle_event)

        # 订阅AI响应事件
        event_bus.subscribe("ai_response_start", self._handle_ai_response_start)
        event_bus.subscribe("ai_response_end", self._handle_ai_response_end)

    def _handle_user_input_event(self, data):
        """处理用户输入事件 - 新增"""
        user_text = data.get('text', '')
        source = data.get('source', 'unknown')

        print(f"[事件] 收到用户输入: {user_text} (来源: {source})")
        self.start_chat(user_text)

    def _handle_audio_interrupt_event(self, data=None):
        """处理音频打断事件 - 新增"""
        print("[事件] 收到音频打断信号")
        self.stop_key()

    def _handle_mic_toggle_event(self, data):
        """处理麦克风开关事件 - 新增"""
        enabled = data.get('enabled', True)
        self.set_mic_enabled(enabled)

    def _handle_ai_response_start(self, data=None):
        """处理AI开始响应事件 - 新增"""
        if not self.asr_real_time:
            self.set_mic_enabled(False)
            print("🔇 [事件] 麦克风已关闭，AI回复中...")

    def _handle_ai_response_end(self, data=None):
        """处理AI响应结束事件 - 新增"""
        if not self.asr_real_time:
            self.wait_for_audio_finish()
            self.set_mic_enabled(True)
            print("🎤 [事件] 麦克风已开启，可以说话了")

    # 新增：事件发布方法
    def publish_event(self, event_name, data=None):
        """发布事件"""
        if HAS_EVENT_BUS:
            event_bus.publish(event_name, data)

    # 🔥 修改原有方法，集成事件发布
    def start_chat(self, user):
        """开始聊天 - 修改为支持事件"""
        self.stop_flag = False

        # 发布开始处理用户输入事件
        self.publish_event("user_input_processing", {"text": user})

        # 原有逻辑
        data = self.bert.vl_bert(user)
        if data == '是':
            image_data = self.get_image_base64()
            self.add_vl_message(user, image_data)
        else:
            self.add_message('user', user)

        # 发布AI开始响应事件
        self.publish_event("ai_response_start")

        response = self.get_requests()
        ai_response = self.accept_chat(response)

        if ai_response:
            self.add_message('assistant', ai_response)

        # 发布AI响应结束事件
        self.publish_event("ai_response_end")

    def accept_chat(self, response):
        """接收聊天 - 修改为支持事件"""
        # 原有的AI回复逻辑...
        if self.function_calling_enabled and self.fc_tool:
            result = self.fc_tool.accept_chat(response)
            if self.cut_text_tts and not self.stop_flag:
                self.audio_player.finish_current_text()
            self.ai_is_responding = False
            print("🔥🔥🔥 AI回复结束！🔥🔥🔥")
            return result
        else:
            full_assistant = ''
            print('AI:', end='')

            for chunk in response:
                if self.stop_flag:
                    print("🔥 收到打断信号，停止AI回复")
                    # 发布打断事件
                    self.publish_event(Events.AUDIO_INTERRUPT)
                    break

                if chunk.choices and chunk.choices[0].delta.content is not None:
                    ai_response = chunk.choices[0].delta.content
                    print(ai_response, end='', flush=True)

                    # 发布AI响应块事件
                    self.publish_event(Events.AI_RESPONSE, {
                        "chunk": ai_response,
                        "full_text": full_assistant + ai_response
                    })

                    if self.cut_text_tts:
                        self.audio_player.cut_text(ai_response)

                    full_assistant += ai_response
                    time.sleep(0.05)

            if self.cut_text_tts and not self.stop_flag:
                self.audio_player.finish_current_text()

            print()
            self.ai_is_responding = False
            self.stop_flag = False
            self.emotion_handler.reset_buffer()
            print("🔥🔥🔥 AI回复结束！🔥🔥🔥")
            return full_assistant

    def stop_key(self):
        """停止按键 - 修改为支持事件"""
        self.stop_flag = True
        self.ai_is_responding = False
        print('打断！')

        # 发布系统打断事件
        self.publish_event(Events.AUDIO_INTERRUPT)

        # 重置情绪处理器的缓冲区
        self.emotion_handler.reset_buffer()

    def set_mic_enabled(self, enabled):
        """控制麦克风开关 - 修改为支持事件"""
        self.mic_enabled = enabled
        if hasattr(self, 'vad_input'):
            self.vad_input.set_mic_enabled(enabled)

        # 发布麦克风状态事件
        self.publish_event(Events.MIC_TOGGLE, {"enabled": enabled})

    # 🔥 新增：外部输入接口（支持事件驱动）
    def handle_keyboard_input(self, text):
        """处理键盘输入"""
        self.publish_event(Events.USER_INPUT, {
            "text": text,
            "source": "keyboard"
        })

    def handle_voice_input(self, text):
        """处理语音输入"""
        self.publish_event(Events.USER_INPUT, {
            "text": text,
            "source": "voice"
        })

    def handle_danmu_input(self, text, nickname):
        """处理弹幕输入"""
        self.publish_event(Events.USER_INPUT, {
            "text": f"弹幕消息：{nickname}: {text}",
            "source": "danmu",
            "nickname": nickname
        })

    # 保持原有方法不变
    def wait_for_audio_finish(self):
        """等待所有音频播放完成"""
        import pygame
        while pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            time.sleep(0.1)
        time.sleep(0.2)

    def add_message(self, role, content):
        self.messages.append({
            'role': role,
            'content': content
        })
        if len(self.messages) > 31:
            self.messages.pop(1)

    def get_requests(self):
        if self.function_calling_enabled and self.fc_tool:
            return self.fc_tool.get_requests()
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True
            )
            return response

    def get_image_base64(self):
        """截图并把通过base64将图片解析成二进制图片数据"""
        screenshot = ImageGrab.grab()
        buffer = io.BytesIO()
        screenshot.save(buffer, format='JPEG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        print('截图')
        return image_data

    def add_vl_message(self, content, image_data):
        self.messages.append({
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_data}'}},
                {'type': 'text', 'text': content}
            ]
        })
        if len(self.messages) > 31:
            self.messages.pop(1)

    # 🔥 修改输入处理方法，使用事件驱动
    def asr_vad_chat(self):
        """ASR语音输入 - 修改为事件驱动"""
        if self.asr_vad:
            while True:
                print('启动ASR')
                user = self.vad_input.vad_asr()
                if user.strip():  # 只有非空输入才处理
                    # 使用事件驱动方式
                    self.handle_voice_input(user)

    def main(self):
        """GUI输入处理 - 修改为事件驱动"""

        def process_keyboard_input(text):
            self.handle_keyboard_input(text)

        sys.exit(start_gui_with_ai(process_keyboard_input))

    def start_main(self):
        """弹幕监听 - 修改为事件驱动"""
        print('开始对话')
        self.listener.start_listening()

        while True:
            chat = self.listener.get_chat()
            if chat:
                # 使用事件驱动方式
                user_message = chat['text']
                nickname = chat['nickname']
                print(f"收到弹幕: {nickname}: {user_message}")

                self.handle_danmu_input(user_message, nickname)

            time.sleep(1)

    def auto_chat(self):
        """自动聊天 - 修改为事件驱动"""
        if self.audo_chat:
            while True:
                jiange = self.interval
                time.sleep(jiange)

                user = self.config['api']['auto_content_chat']
                # 使用事件驱动方式
                self.publish_event(Events.USER_INPUT, {
                    "text": user,
                    "source": "auto_chat"
                })

    def main_chat(self):
        """主聊天循环 - 保持不变"""
        threading.Thread(target=self.auto_chat, daemon=True).start()
        threading.Thread(target=self.start_main, daemon=True).start()
        threading.Thread(target=self.asr_vad_chat, daemon=True).start()

        # 主线程
        if self.config['inputs']['keyboard']['enabled']:
            self.main()
        else:
            while True:
                user = input('你：')
                self.handle_keyboard_input(user)


if __name__ == '__main__':
    print("🚀 启动事件驱动版本的MyNeuro")
    my_neuro = MyNeuro()
    my_neuro.main_chat()
