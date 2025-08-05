# -*- coding: utf-8 -*-
import json
import base64
import io
import pyautogui
from openai import OpenAI
from PIL import ImageGrab, Image, ImageDraw
from config_mod.load_config import load_config


class Pc_Agent:

    def __init__(self):
        config = load_config()
        api_key = config['jietu_api']['api_key']
        api_url = config['jietu_api']['api_url']
        self.model = config['jietu_api']['model']
        self.client = OpenAI(api_key=api_key, base_url=api_url)

    def get_image_base64(self):
        print("分析图片...")
        scr = ImageGrab.grab()
        buffer = io.BytesIO()
        scr.save(buffer, format='JPEG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_data, scr

    def jieshou(self, response):
        full_assistant_response = ''
        print('AI:', end='')
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                ai_chunk = chunk.choices[0].delta.content
                print(ai_chunk, end='', flush=True)
                full_assistant_response += ai_chunk
        print()
        return full_assistant_response

    def draw_bbox(self, img, bbox):
        draw = ImageDraw.Draw(img)
        draw.rectangle(bbox, outline='red', width=3)
        # img.show() # 取消注释可以在执行后显示带红框的截图

    def shubiao(self, rect):
        center_x = (rect[0] + rect[2]) // 2
        center_y = (rect[1] + rect[3]) // 2
        pyautogui.moveTo(center_x, center_y, duration=0.25)
        pyautogui.doubleClick()

    def click_element(self, content):
        image_data, img = self.get_image_base64()

        messages = [
            {
                'role': 'system',
                'content': '你是一个PC屏幕视觉分析助手。你的任务是根据用户的文字描述，在提供的截图中定位目标元素，并以JSON格式返回该元素的2D边界框（bounding box）。JSON格式必须为 `{"bbox_2d": [x1, y1, x2, y2]}`。不要输出任何其他文字或代码标记。'
            },
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_data}'}},
                    {'type': 'text', 'text': content}
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )

        ai_response_str = self.jieshou(response)

        # 直接解析JSON，如果格式错误程序会在这里报错
        bbox_data = json.loads(ai_response_str)
        image_bbox = bbox_data['bbox_2d']
        self.draw_bbox(img, image_bbox)
        self.shubiao(image_bbox)

        return f"已点击 {content}"


if __name__ == '__main__':
    pc_agent = Pc_Agent()
    while True:
        user_input = input("你:")
        pc_agent.click_element(user_input)
