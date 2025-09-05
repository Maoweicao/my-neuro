"""
测试字幕位置显示功能
"""

import json
import time
import requests

def test_subtitle_display():
    """测试字幕显示功能"""
    
    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    subtitle_config = config.get('subtitle', {})
    print("当前字幕配置:")
    print(f"  显示器: {subtitle_config.get('display_monitor', 0)}")
    print(f"  位置: {subtitle_config.get('display_position', 'bottom')}")
    print(f"  X坐标: {subtitle_config.get('position_x', 0)}")
    print(f"  Y坐标: {subtitle_config.get('position_y', 0)}")
    print(f"  X偏移: {subtitle_config.get('display_offset_x', 0)}")
    print(f"  Y偏移: {subtitle_config.get('display_offset_y', 0)}")
    
    # 测试字幕显示
    test_messages = [
        "测试字幕显示功能 - 第一条消息",
        "这是第二条测试消息，用于验证位置是否正确",
        "最后一条测试消息，检查字幕是否在指定位置显示"
    ]
    
    try:
        # 通过WebAPI发送测试消息
        url = "http://127.0.0.1:5000/subtitle"
        
        for i, message in enumerate(test_messages):
            print(f"\n发送第 {i+1} 条测试消息: {message}")
            
            data = {
                "text": message,
                "duration": 3000  # 显示3秒
            }
            
            try:
                response = requests.post(url, json=data, timeout=5)
                if response.status_code == 200:
                    print(f"  ✓ 消息发送成功")
                else:
                    print(f"  ✗ 消息发送失败: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"  ✗ 网络请求失败: {e}")
            
            # 等待一段时间再发送下一条
            time.sleep(4)
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    print("=== 字幕位置显示测试 ===")
    test_subtitle_display()
    print("\n=== 测试完成 ===")
