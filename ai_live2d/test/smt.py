#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
字幕管理器测试脚本 - 异步适配版本
支持与异步系统的集成测试
"""

import sys
import os
import asyncio
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt, QThread

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_subtitle_manager")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入模块
from interface.subtitle_manager import SubtitleManager
from core.event_bus import EventBus

# 尝试导入qasync（如果可用）
try:
    import qasync
    HAS_QASYNC = True
    logger.info("检测到qasync，将使用完整异步支持")
except ImportError:
    HAS_QASYNC = False
    logger.warning("未安装qasync，将使用兼容模式")
    logger.warning("建议安装: pip install qasync")

class AsyncTestRunner:
    """异步测试运行器"""
    
    def __init__(self):
        self.app = None
        self.subtitle_manager = None
        self.event_bus = None
        
    async def setup(self):
        """设置测试环境"""
        # 创建事件总线
        self.event_bus = EventBus()
        
        # 创建配置
        config = {
            "subtitle": {
                "font_family": "Microsoft YaHei",
                "font_size": 24,
                "font_bold": True,
                "box_height": 500,
                "box_width": 1200,
                "text_color_r": 255,
                "text_color_g": 255,
                "text_color_b": 255,
                "text_color_a": 255,
                "outline_color_r": 0,
                "outline_color_g": 0,
                "outline_color_b": 0,
                "outline_color_a": 200,
                "bg_color_r": 0,
                "bg_color_g": 0,
                "bg_color_b": 0,
                "bg_color_a": 128,
                "padding": 20,
                "enable_limit_range": True,
                "border_radius": 15,
                "fade_duration": 300,
                "auto_hide_delay": 2000,  # 自动隐藏延迟时间
            }
        }
        
        # 创建字幕管理器
        self.subtitle_manager = SubtitleManager(parent=None, config=config, event_bus=self.event_bus)
        
    
    async def test_text_sequence(self):
        """测试文本序列显示功能"""
        logger.info("🧪 测试1: 文本序列显示")
        
        # 测试文本序列
        sequences = [
            "你",
            "你好",
            "你好呀",
            "你好呀！",
            "你好呀！这是一个",
            "你好呀！这是一个测试",
            "你好呀！这是一个测试序列."
        ]
        
        for text in sequences:
            # 使用新的更新方法
            self.subtitle_manager.add_text(text)
            await asyncio.sleep(0.5)  # 每个文本显示0.5秒
            
        # 显示最终文本
        self.subtitle_manager.add_text("文本序列测试完成 ✅")
        await asyncio.sleep(1)
        
        logger.info("✅ 文本序列测试完成")
    
    async def test_basic_subtitle(self):
        """测试基本字幕功能"""
        logger.info("🧪 测试2: 基本字幕显示")
        
        # 测试短文本
        self.subtitle_manager.clear_text()
        await asyncio.sleep(1)
        self.subtitle_manager.add_text("你好，这是一个测试字幕！")
        await asyncio.sleep(2)
        
        # 测试长文本
        long_text = "这是一个较长的测试字幕，用于验证字幕管理器处理长文本的能力。"
        self.subtitle_manager.add_text(long_text)
        await asyncio.sleep(3)
        
        logger.info("✅ 基本字幕测试完成")
    
    async def test_multiline_subtitle(self):
        """测试多行字幕"""
        logger.info("🧪 测试3: 多行字幕显示")
        
        multiline_text = """这是第一行字幕
这是第二行字幕
这是第三行字幕
测试多行显示效果"""
        
        self.subtitle_manager.add_text(multiline_text)
        await asyncio.sleep(3)
        
        logger.info("✅ 多行字幕测试完成")
    
    async def test_event_integration(self):
        """测试事件总线集成"""
        logger.info("🧪 测试4: 事件总线集成（模拟TTS同步）")
        
        # 模拟TTS开始
        await self.event_bus.publish("tts_start", {})
        await asyncio.sleep(0.5)
        
        # 模拟LLM完成事件（非TTS模式）
        await self.event_bus.publish("llm_complete", {
            "text": "这是LLM完成事件的测试文本，会直接显示并自动隐藏。"
        })
        
        await asyncio.sleep(2)  # 观察自动隐藏
        
        # 模拟TTS结束
        await self.event_bus.publish("tts_end", {})
        await asyncio.sleep(1)
        
        logger.info("✅ 事件总线集成测试完成")
    
    async def test_clear_function(self):
        """测试清空功能"""
        logger.info("🧪 测试5: 清空功能")
        
        # 显示文本
        self.subtitle_manager.add_text("这段文本会被清空")
        await asyncio.sleep(1.5)  # 等待显示+一点观察时间
        
        # 清空文本
        self.subtitle_manager.clear_text()
        await asyncio.sleep(1.5)  # 观察清空效果
        
        logger.info("✅ 清空功能测试完成")
    
    async def test_long_text_handling(self):
        """测试长文本处理"""
        logger.info("🧪 测试6: 长文本处理")
        
        very_long_text = """这是一个非常长的文本，用来测试字幕管理器处理长文本的能力。
它包含了多行内容，并且每行都有相当多的字符。
这样可以测试文本分行、尺寸限制等功能。
字幕管理器应该能够智能地处理这些内容，确保用户能够清晰地看到所有信息。"""
        
        self.subtitle_manager.add_text(very_long_text)
        await asyncio.sleep(3)
        
        logger.info("✅ 长文本处理测试完成")
    
    async def run_all_tests(self):
        """运行所有测试"""
        try:
            await self.setup()
            
            logger.info("🎬 开始字幕管理器异步测试")
            print("\n" + "="*60)
            print("🎬 字幕管理器异步测试")
            print("="*60)
            
            # 运行各项测试
            await self.test_text_sequence()
            await asyncio.sleep(1)
            
            await self.test_basic_subtitle()
            await asyncio.sleep(1)
            
            await self.test_multiline_subtitle()
            await asyncio.sleep(1)
            
            await self.test_event_integration()
            await asyncio.sleep(1)
            
            await self.test_clear_function()
            await asyncio.sleep(1)
            
            await self.test_long_text_handling()
            await asyncio.sleep(1)
            
            print("\n" + "="*60)
            print("📊 测试结果: 🎉 全部测试完成")
            print("="*60)
            
            logger.info("✅ 所有测试完成")
            return True
            
        except Exception as e:
            logger.error(f"💥 测试过程出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        finally:
            # 清理资源
            if self.subtitle_manager:
                await self.subtitle_manager.cleanup()
            if self.event_bus:
                await self.event_bus.shutdown()

def test_with_qasync():
    """使用qasync运行完整异步测试"""
    app = QApplication(sys.argv)
    
    # 设置异步事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    async def main():
        test_runner = AsyncTestRunner()
        test_runner.app = app
        
        # 运行测试
        result = await test_runner.run_all_tests()
        
        # 等待一会儿让用户看到结果
        await asyncio.sleep(1)
        
        # 退出应用
        app.quit()
        
        return result
    
    try:
        with loop:
            result = loop.run_until_complete(main())
        return result
    except Exception as e:
        logger.error(f"qasync测试失败: {e}")
        return False

def test_compatibility_mode():
    """兼容模式测试（不使用qasync）"""
    app = QApplication(sys.argv)
    
    # 创建配置
    config = {
        "subtitle": {
            "font_family": "Microsoft YaHei",
            "font_size": 24,
            "font_bold": True,
            "box_height": 500,
            "box_width": 1200,
            "text_color_r": 255,
            "text_color_g": 255,
            "text_color_b": 255,
            "text_color_a": 255,
            "outline_color_r": 0,
            "outline_color_g": 0,
            "outline_color_b": 0,
            "outline_color_a": 200,
            "bg_color_r": 0,
            "bg_color_g": 0,
            "bg_color_b": 0,
            "bg_color_a": 128,
            "padding": 20,
            "enable_limit_range": False,
            "border_radius": 15,
            "fade_duration": 300,
            "auto_hide_delay": 2000,
        }
    }
    
    try:
        # 创建字幕管理器（无事件总线）
        subtitle_manager = SubtitleManager(parent=None, config=config, event_bus=None)
        
        def run_tests():
            logger.info("🧪 兼容模式测试")
            
            # 测试1: 文本序列
            logger.info("测试文本序列")
            sequences = [
                "你",
                "你好",
                "你好呀",
                "你好呀！"
            ]
            
            for i, text in enumerate(sequences):
                QTimer.singleShot(1500 * (i+1), lambda t=text: [
                    subtitle_manager.set_text_async(t, stream=False)
                ])
            
            # 测试2: 基本显示
            QTimer.singleShot(7500, lambda: [
                logger.info("测试基本显示"),
                subtitle_manager.set_text_async("兼容模式测试 - 基本显示", stream=False)
            ])
            
            # 测试3: 多行文本
            QTimer.singleShot(10000, lambda: [
                logger.info("测试多行文本"),
                subtitle_manager.set_text_async("第一行文本\n第二行文本\n第三行文本\n兼容模式测试", stream=False)
            ])
            
            # 测试4: 清空
            QTimer.singleShot(13000, lambda: [
                logger.info("测试清空功能"),
                subtitle_manager.clear_text_async()
            ])
            
            # 结束测试
            QTimer.singleShot(15000, lambda: [
                logger.info("✅ 兼容模式测试完成"),
                app.quit()
            ])
        
        # 启动测试
        QTimer.singleShot(1000, run_tests)
        
        # 运行应用
        app.exec_()
        
        logger.info("兼容模式测试完成")
        return True
        
    except Exception as e:
        logger.error(f"兼容模式测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("🎬 开始字幕管理器测试")
    
    if HAS_QASYNC:
        # 使用完整异步模式
        logger.info("使用qasync完整异步模式")
        result = test_with_qasync()
    else:
        # 使用兼容模式
        logger.info("使用兼容模式")
        result = test_compatibility_mode()
    
    logger.info(f"📊 测试结果: {'🎉 通过' if result else '❌ 失败'}")
    return result

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 测试程序出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)