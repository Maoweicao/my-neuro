# backend/tts_service.py
from flask import Flask, request, send_file
import requests
import pygame
import os

app = Flask(__name__)


def generate_audio(text):
    data = {'text': text, 'text_language': 'zh'}
    url = 'https://u456499-8a2f-422084c5.westb.seetacloud.com:8443/v3/'

    response = requests.post(url, json=data)

    # 保存音频文件
    audio_path = 'temp_audio.wav'
    with open(audio_path, 'wb') as f:
        f.write(response.content)

    return audio_path


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    text = request.json.get('text')
    audio_path = generate_audio(text)
    return send_file(audio_path, mimetype='audio/wav')


if __name__ == '__main__':
    app.run(port=5000)