#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Live2D模型测试脚本
"""

import sys
import os
import time
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_live2d_model")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Live2D模型和事件总线
from models.live2d_model import Live2DModel, init_live2d, dispose_live2d
from core.event_bus import EventBus

def test_live2d_model():
    """测试Live2D模型的基本功能"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 初始化Live2D引擎
    if not init_live2d():
        logger.error("Live2D引擎初始化失败")
        return False
    
    # 创建配置和事件总线
    config = {
        "ui": {
            "model_scale": 1.0
        },
        "model_path": "models/2D/Hiyori.model3-2025.json"
    }
    event_bus = EventBus()
    
    try:
        # 创建模型实例
        model = Live2DModel(config, event_bus)
        
        # 设置大小和位置
        model.resize(500, 500)
        model.move(100, 100)
        
        # 显示模型
        model.show()
        
        # 测试模型操作
        def test_model_functions():
            logger.info("测试模型功能...")
            
            # 测试说话状态
            logger.info("测试说话状态")
            model.set_talking(True)
            QTimer.singleShot(2000, lambda: model.set_talking(False))
            
            # 测试聆听状态
            logger.info("测试聆听状态")
            QTimer.singleShot(3000, lambda: model.set_listening(True))
            QTimer.singleShot(5000, lambda: model.set_listening(False))
            
            # 测试表情
            logger.info("测试表情")
            QTimer.singleShot(6000, lambda: model.set_random_expression())
            
            # 测试嘴部动作
            logger.info("测试嘴部动作")
            def animate_mouth():
                for i in range(10):
                    value = (i % 10) / 10.0
                    model.on_mouth_movement(value)
                    time.sleep(0.2)
            
            QTimer.singleShot(8000, animate_mouth)
            
            # 测试完成后退出
            QTimer.singleShot(15000, app.quit)
        
        # 启动测试定时器
        QTimer.singleShot(1000, test_model_functions)
        
        # 运行应用
        app.exec_()
        
        logger.info("Live2D模型测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # 清理Live2D引擎
        dispose_live2d()

if __name__ == "__main__":
    try:
        result = test_live2d_model()
        logger.info(f"测试结果: {'通过' if result else '失败'}")
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())