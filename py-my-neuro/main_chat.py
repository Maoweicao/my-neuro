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


class MyNeuro:

    def __init__(self):
        # 初始化
        init_live2d()
        self.app = QApplication(sys.argv)
        live_model = Live2DModel()
        live_model.show()

        self.config = load_config()
        self.bert = Bert_panduan()

        API_KEY = self.config['api']['api_key']
        API_URL = self.config['api']['api_url']
        self.model = self.config['api']['model']

        self.client = OpenAI(api_key=API_KEY, base_url=API_URL)

        self.messages = [{
            'role': 'system', 'content': self.config['api']['system_prompt']
        }]

        self.cut_text_tts = self.config['features']['cut_text_tts']

        # 时间限制
        self.interval = self.config['inputs']['auto_chat']['interval']
        self.audo_chat = self.config['inputs']['auto_chat']['enabled']

        # 新增：获取ASR监听模式配置
        self.asr_real_time = self.config['inputs']['asr'].get('real_time', True)

        # 新增：麦克风状态控制
        self.mic_enabled = True

        # AI回复状态标志
        self.ai_is_responding = False

        # 判断ASR是否
        self.vad_input = AudioSystem(parent_neuro=self)
        self.asr_vad = self.config['inputs']['asr']['enabled']

        # 根据config配置文件布尔值判断是否开启live2d的皮套显示
        live_2d = self.config['features']['live2d']

        # 🎯 唯一的修改：初始化情绪处理器
        self.emotion_handler = EmotionHandler(config_path="emotion_mod/emotion_actions.json", live_model=live_model)

        # 🎯 唯一的修改：传入emotion_handler
        self.audio_player = AudioPlayer(live_model=live_model,
                                        emotion_handler=self.emotion_handler) if live_2d else AudioPlayer(
            emotion_handler=self.emotion_handler)


        self.stop_flag = False
        keyboard.add_hotkey('ctrl+i', self.stop_key)

        self.singing_system = SingingSystem(
            live_model=live_model if live_2d else None,
            audio_dir="KTV/output"
        )


        # 根据配置决定是否启用 function calling
        self.function_calling_enabled = self.config['features']['function_calling']
        if self.function_calling_enabled:
            self.fc_tool = MyNuroTools(self)
        else:
            self.fc_tool = None

        # 哔哩哔哩的直播
        self.listener = BilibiliDanmuListener()

    def set_mic_enabled(self, enabled):
        """控制麦克风开关"""
        self.mic_enabled = enabled
        if hasattr(self, 'vad_input'):
            self.vad_input.set_mic_enabled(enabled)

    def wait_for_audio_finish(self):
        """等待所有音频播放完成"""
        import pygame
        while pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            time.sleep(0.1)
        # 额外等待一点时间确保完全结束
        time.sleep(0.2)

    def stop_key(self):
        self.stop_flag = True
        self.ai_is_responding = False
        print('打断！')
        # 重置情绪处理器的缓冲区
        self.emotion_handler.reset_buffer()

    def add_message(self, role, content):
        self.messages.append({
            'role': role,
            'content': content
        })

        if len(self.messages) > 31:
            self.messages.pop(1)

    def get_requests(self):
        # 如果启用了function calling，就用fc_tool的方法
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
        """
        截图并把通过base64将图片解析成二进制图片数据
        """
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

    def accept_chat(self, response):
        # 非实时模式：AI开始回复时关闭麦克风
        if not self.asr_real_time:
            self.set_mic_enabled(False)
            print("🔇 麦克风已关闭，AI回复中...")

        # 设置AI正在回复状态
        self.ai_is_responding = True

        # 如果启用了function calling，就用fc_tool的方法
        if self.function_calling_enabled and self.fc_tool:
            result = self.fc_tool.accept_chat(response)

            if self.cut_text_tts and not self.stop_flag:
                self.audio_player.finish_current_text()

            self.ai_is_responding = False

            # AI回复完成后，如果是非实时模式，重新开启麦克风
            if not self.asr_real_time:
                # 等待所有音频播放完成
                self.wait_for_audio_finish()
                self.set_mic_enabled(True)
                print("🎤 麦克风已开启，可以说话了")

            print("🔥🔥🔥 AI回复结束！🔥🔥🔥")
            return result
        else:
            full_assistant = ''
            print('AI:', end='')

            for chunk in response:
                if self.stop_flag:
                    print("🔥 收到打断信号，停止AI回复")
                    break
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    ai_response = chunk.choices[0].delta.content
                    print(ai_response, end='', flush=True)

                    # 🎯 删除旧的立即触发，现在AudioPlayer会自动处理情绪同步
                    # self.emotion_handler.process_text_chunk(ai_response)  # 已删除

                    # 根据config配置文件布尔值判断是否开启tts语音播放
                    if self.cut_text_tts:
                        self.audio_player.cut_text(ai_response)

                    full_assistant += ai_response

                    # 测试用：稍微延迟一下，方便测试打断
                    time.sleep(0.05)

            # for循环完全结束后，并且只有在没有被打断的情况下才处理
            if self.cut_text_tts and not self.stop_flag:
                self.audio_player.finish_current_text()

            print()

            # 重置AI回复状态
            self.ai_is_responding = False
            self.stop_flag = False

            # AI回复完成后，如果是非实时模式，重新开启麦克风
            if not self.asr_real_time:
                # 等待所有音频播放完成
                self.wait_for_audio_finish()
                self.set_mic_enabled(True)
                print("🎤 麦克风已开启，可以说话了")

            print("🔥🔥🔥 AI回复结束！🔥🔥🔥")

            # 对话结束后重置情绪处理器缓冲区
            self.emotion_handler.reset_buffer()

            return full_assistant

    def asr_vad_chat(self):
        if self.asr_vad:
            while True:
                print('启动ASR')
                user = self.vad_input.vad_asr()
                self.stop_flag = False

                # 调用start_chat而不是直接add_message
                self.start_chat(user)

    def start_chat(self, user):
        self.stop_flag = False
        data = self.bert.vl_bert(user)
        if data == '是':
            image_data = self.get_image_base64()
            self.add_vl_message(user, image_data)
        else:
            self.add_message('user', user)

        response = self.get_requests()
        ai_response = self.accept_chat(response)

        if ai_response:
            self.add_message('assistant', ai_response)

    def main(self):
        sys.exit(start_gui_with_ai(self.start_chat))

    def start_main(self):
        print('开始对话')

        # 启动弹幕监听
        self.listener.start_listening()

        while True:
            # 获取弹幕
            chat = self.listener.get_chat()
            if chat:
                user_message = f"弹幕消息：{chat['nickname']}: {chat['text']}"
                nickname = chat['nickname']

                print(f"收到弹幕: {nickname}: {user_message}")

                # 添加用户消息
                self.add_message('user', user_message)

                # 获取AI回复
                response = self.get_requests()
                ai_content = self.accept_chat(response)

                # 添加AI回复到对话历史
                self.add_message('assistant', ai_content)

            time.sleep(1)  # 每秒检查一次新弹幕

    def auto_chat(self):
        if self.audo_chat:
            while True:
                jiange = self.interval
                time.sleep(jiange)

                user = self.config['api']['auto_content_chat']
                self.add_message('user', user)
                response = self.get_requests()
                ai_response = self.accept_chat(response)

                if ai_response:
                    self.add_message('assistant', ai_response)

    def start_vl_chat(self):
        user = input('你：')
        image_data = self.get_image_base64()
        self.add_vl_message(user, image_data)
        response = self.get_requests()
        ai_response = self.accept_chat(response)
        if ai_response:
            self.add_message('assistant', ai_response)

    def main_chat(self):
        threading.Thread(target=self.auto_chat, daemon=True).start()
        threading.Thread(target=self.start_main, daemon=True).start()
        threading.Thread(target=self.asr_vad_chat, daemon=True).start()
        # 主线程
        if self.config['inputs']['keyboard']['enabled']:
            self.main()
        else:
            while True:
                user = input('你：')
                self.start_chat(user)


if __name__ == '__main__':
    my_neuro = MyNeuro()
    my_neuro.main_chat()
