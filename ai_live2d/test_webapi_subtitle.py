"""
通过WebAPI测试字幕显示
"""

import requests
import time

def test_subtitle_webapi():
    """通过WebAPI测试字幕显示"""
    
    print("=== 通过WebAPI测试字幕显示 ===")
    
    # WebAPI字幕端点
    url = "http://127.0.0.1:5000/subtitle"
    
    # 测试字幕
    test_messages = [
        "🔴 这是通过WebAPI发送的测试字幕",
        "🟢 如果您看到这条消息，说明字幕系统工作正常",
        "🔵 现在字幕应该在屏幕中央显示，使用红色背景"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n发送第 {i} 条测试字幕: {message}")
        
        data = {
            "text": message,
            "duration": 4000  # 显示4秒
        }
        
        try:
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ 字幕发送成功")
                result = response.json()
                print(f"  响应: {result}")
            else:
                print(f"  ✗ 字幕发送失败: HTTP {response.status_code}")
                print(f"  响应内容: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"  ✗ 网络请求失败: {e}")
        
        # 等待一段时间再发送下一条
        if i < len(test_messages):
            print("  等待5秒...")
            time.sleep(5)
    
    print(f"\n所有测试字幕已发送完成！")
    print("请检查您的屏幕中央是否有红色背景的字幕显示。")

if __name__ == "__main__":
    test_subtitle_webapi()
