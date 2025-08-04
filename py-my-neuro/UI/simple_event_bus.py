# simple_event_bus.py - 直接可用的事件总线
"""
简单的事件总线实现，可以直接集成到现有项目中
"""


class SimpleEventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_name, callback):
        """订阅事件"""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name, callback):
        """取消订阅"""
        if event_name in self._subscribers:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name, data=None):
        """发布事件"""
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    if data is not None:
                        callback(data)
                    else:
                        callback()
                except Exception as e:
                    print(f"事件处理错误 {event_name}: {e}")


# 全局事件总线实例
event_bus = SimpleEventBus()


# 常用事件名称
class Events:
    AUDIO_START = "audio_start"
    AUDIO_STOP = "audio_stop"
    AUDIO_INTERRUPT = "audio_interrupt"
    LIP_SYNC_START = "lip_sync_start"
    LIP_SYNC_UPDATE = "lip_sync_update"
    LIP_SYNC_STOP = "lip_sync_stop"
    USER_INPUT = "user_input"
    AI_RESPONSE = "ai_response"
    MIC_TOGGLE = "mic_toggle"


if __name__ == "__main__":
    # 测试事件总线
    def test_handler(data):
        print(f"收到事件数据: {data}")


    # 订阅事件
    event_bus.subscribe("test_event", test_handler)

    # 发布事件
    event_bus.publish("test_event", {"message": "Hello World"})

    print("事件总线测试成功！")