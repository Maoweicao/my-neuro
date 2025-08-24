#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户输入窗口手动测试脚本 (使用qasync) - 修复版
运行后会出现输入窗口，您可以：
1. 输入文本并按回车发送
2. 按 Alt 键切换穿透模式（鼠标穿透，窗口半透明）
3. 按 Ctrl 键进入拖动模式（临时隐藏输入框）
4. 在拖动模式下移动窗口位置
5. 再次按 Ctrl 键退出拖动模式（恢复输入框）
"""

import sys
import os
import logging
import asyncio
import qasync
from PyQt5.QtWidgets import QApplication

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("test_user_input")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入模块
from interface.user_input import UserInputWindow
from core.event_bus import EventBus

async def handle_user_input(data):
    """处理用户输入事件"""
    text = data.get("text", "")
    logger.info(f"📤 收到用户输入: {text}")
    print(f"\n{'='*50}")
    print(f"测试结果: 成功收到用户输入!")
    print(f"输入内容: '{text}'")
    print(f"事件类型: user_text_input")
    print(f"{'='*50}\n")

def main():
    """主函数 - 使用qasync正确初始化"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 设置qasync事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 创建事件总线
    event_bus = EventBus()
    
    # 创建配置
    config = {
        "user_input": {
            "width": 500,
            "height": 100,
            "font_family": "Microsoft YaHei",
            "font_size": 16,
            "bg_color_r": 40,
            "bg_color_g": 44,
            "bg_color_b": 52,
            "bg_color_a": 220,
            "text_color_r": 220,
            "text_color_g": 220,
            "text_color_b": 220,
            "border_color_r": 86,
            "border_color_g": 182,
            "border_color_b": 194,
            "border_radius": 10,
            "status_bg_color_r": 60,
            "status_bg_color_g": 60,
            "status_bg_color_b": 70,
            "status_bg_color_a": 220
        }
    }
    
    # 创建用户输入窗口
    user_input = UserInputWindow(config=config, event_bus=event_bus)
    user_input.show()
    
    # 正确订阅事件
    async def subscribe_events():
        await event_bus.subscribe("user_text_input", handle_user_input)
    
    # 在事件循环中运行订阅
    loop.create_task(subscribe_events())
    
    # 打印使用说明
    print("\n" + "="*60)
    print("用户输入窗口手动测试 (使用qasync)")
    print("="*60)
    print("1. 在输入框中输入文本并按回车发送")
    print("2. 按 Alt 键可以切换穿透模式（鼠标穿透，窗口半透明）")
    print("3. 按 Ctrl 键进入拖动模式（输入框隐藏）")
    print("4. 在拖动模式下移动窗口位置")
    print("5. 再次按 Ctrl 键退出拖动模式（输入框显示）")
    print("6. 所有输入将显示在控制台")
    print("="*60 + "\n")
    
    # 运行应用
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    try:
        main()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("⏹️ 用户中断测试")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 测试程序出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)