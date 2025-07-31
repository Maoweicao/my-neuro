from bilibili_stream import BilibiliDanmuListener
import time
from openai import OpenAI

# 创建监听器实例
listener = BilibiliDanmuListener()

API_KEY = 'sk-rQQgCdCztnxo5KBU6ZPy9RQdSmH0tzQsIRWQzgsvDtMl3JEd'
API_URL = 'http://154.9.254.9:3000/v1'
messages = [{
    'role': 'system', 'content': '你是一个傲娇的AI'
}]

client = OpenAI(api_key=API_KEY, base_url=API_URL)


def add_message(role, content):  # 去掉了self参数
    messages.append({
        'role': role,
        'content': content
    })

    if len(messages) > 31:
        messages.pop(1)


def get_requests():
    response = client.chat.completions.create(
        model='gemini-2.0-flash',
        messages=messages,
        stream=True
    )
    return response


def accept_chat(response):
    full_assistant = ''
    print('AI: ', end='')

    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            ai_response = chunk.choices[0].delta.content
            print(ai_response, end='', flush=True)
            full_assistant += ai_response

    print()
    return full_assistant


def start_main():
    print('开始对话')

    # 启动弹幕监听
    listener.start_listening()

    while True:
        # 获取弹幕
        chat = listener.get_chat()
        if chat:
            user_message = f"弹幕消息：{chat['nickname']}: {chat['text']}"
            nickname = chat['nickname']

            print(f"收到弹幕: {nickname}: {user_message}")

            # 添加用户消息
            add_message('user', user_message)

            # 获取AI回复
            response = get_requests()
            ai_content = accept_chat(response)

            # 添加AI回复到对话历史
            add_message('assistant', ai_content)

        time.sleep(1)  # 每秒检查一次新弹幕


if __name__ == '__main__':
    start_main()