# BLBL.py
import requests
import time
import threading
from queue import Queue
from config_mod.load_config import load_config


class BilibiliDanmuListener:
    def __init__(self):
        config = load_config()

        self.room_id = config['inputs']['danmu']['room_id']
        self.url = f"http://api.live.bilibili.com/ajax/msg?roomid={self.room_id}"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        self.message_queue = Queue()
        self.is_listening = False
        self.last_timeline = ""

    def start_listening(self):
        """启动后台监听线程"""
        if self.is_listening:
            return

        self.is_listening = True
        thread = threading.Thread(target=self._listen_danmu, daemon=True)
        thread.start()

    def _listen_danmu(self):
        """后台监听弹幕"""
        print("正在初始化...")

        try:
            data = requests.get(self.url, headers=self.headers).json()
            messages = data['data']['room']
            if messages:
                self.last_timeline = max(msg.get('timeline', '') for msg in messages)
                print(f"从 {self.last_timeline} 开始监听新弹幕...")
        except:
            pass

        print("开始监听...")

        while self.is_listening:
            try:
                data = requests.get(self.url, headers=self.headers).json()
                messages = data['data']['room']

                for msg in messages:
                    timeline = msg.get('timeline', '')
                    if timeline > self.last_timeline:
                        nickname = msg.get('nickname', '未知')
                        text = msg.get('text', '')
                        if text.strip():
                            self.message_queue.put({
                                'text': text,
                                'nickname': nickname,
                                'timeline': timeline
                            })
                            self.last_timeline = timeline

                time.sleep(2)
            except Exception as e:
                print(f"监听出错: {e}")
                time.sleep(3)

    def get_chat(self):
        """获取最新的弹幕消息"""
        if not self.message_queue.empty():
            return self.message_queue.get()
        return None

    def get_all_chat(self):
        """获取所有待处理的弹幕"""
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages

    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        print("停止监听...")

    def main_start(self):
        self.start_listening()
        while True:
            chat = self.get_chat()
            if chat:
                print(f"收到弹幕: {chat['nickname']}: {chat['text']}")
            time.sleep(1)


# 使用示例
if __name__ == "__main__":
    # 创建监听器实例
    listener = BilibiliDanmuListener()

    # 启动监听
    listener.main_start()