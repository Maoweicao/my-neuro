#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Live2D嘴型同步测试脚本 - 专门测试嘴型同步功能
"""

import os
import sys
import time
import logging
import traceback
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QSurfaceFormat

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lipsync_test")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Live2D模型相关模块
from models.live2d_model import Live2DModel, init_live2d, dispose_live2d
from live2d.utils.lipsync import WavHandler
from live2d.v3 import StandardParams

class WavHandlerWatcher(QThread):
    """用于监视WavHandler的后台线程"""
    
    update_signal = pyqtSignal(float)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, wav_file_path):
        super().__init__()
        self.wav_file_path = wav_file_path
        self.is_running = False
        self.wav_handler = None
        self.lip_sync_intensity = 3.0
        
    def run(self):
        """运行线程"""
        try:
            logger.info(f"启动WavHandler监视线程: {self.wav_file_path}")
            
            # 检查文件
            if not os.path.exists(self.wav_file_path):
                raise FileNotFoundError(f"音频文件不存在: {self.wav_file_path}")
            
            # 文件信息
            logger.info(f"音频文件大小: {os.path.getsize(self.wav_file_path)} 字节")
            
            # 使用wave库检查文件
            import wave
            with wave.open(self.wav_file_path, 'rb') as wav_file:
                channels, sampwidth, framerate, nframes, _, _ = wav_file.getparams()
                logger.info(f"音频文件参数: 通道数={channels}, 采样宽度={sampwidth}, 帧率={framerate}, 总帧数={nframes}")
            
            # 初始化WavHandler
            self.wav_handler = WavHandler()
            logger.info("WavHandler实例已创建")
            
            # 从成功示例看，Start方法不会返回值，所以直接调用不检查返回值
            logger.info(f"启动WavHandler: {self.wav_file_path}")
            self.wav_handler.Start(self.wav_file_path)
            
            # 验证是否可以获取RMS值作为初始化成功的标志
            try:
                rms = self.wav_handler.GetRms()
                logger.info(f"初始RMS值: {rms}")
                # 成功获取RMS值，表示初始化成功
            except Exception as rms_err:
                logger.error(f"获取RMS值失败，初始化可能失败: {rms_err}")
                import traceback
                logger.error(traceback.format_exc())
                raise RuntimeError(f"WavHandler可能初始化失败: {self.wav_file_path}")
            
            self.is_running = True
            logger.info("WavHandler初始化成功，开始处理")
            
            # 循环更新
            while self.is_running:
                if self.wav_handler.Update():
                    # 获取RMS值
                    rms = self.wav_handler.GetRms()
                    mouth_open_value = rms * self.lip_sync_intensity
                    
                    # 限制值范围
                    mouth_open_value = max(0.0, min(2.0, mouth_open_value))
                    
                    # 发出更新信号
                    self.update_signal.emit(mouth_open_value)
                    
                    # 短暂休眠
                    time.sleep(1/60)  # 约60fps
                else:
                    # 处理完毕
                    logger.info("WavHandler处理完毕")
                    self.is_running = False
                    break
            
            # 发送完成信号
            self.finished_signal.emit()
            
        except Exception as e:
            logger.error(f"WavHandler线程错误: {e}")
            self.error_signal.emit(str(e))
            traceback.print_exc()
            self.is_running = False
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        self.wait()  # 等待线程结束
        # 清理资源
        if self.wav_handler:
            self.wav_handler = None

def test_lip_sync():
    """测试嘴型同步功能"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 配置OpenGL格式
    format = QSurfaceFormat.defaultFormat()
    format.setSwapInterval(0)  # 禁用垂直同步
    QSurfaceFormat.setDefaultFormat(format)
    
    # 初始化Live2D引擎
    if not init_live2d():
        logger.error("Live2D引擎初始化失败")
        return False
    
    # 配置信息
    config = {
        "ui": {
            "model_scale": 1.0
        },
        "model_path": "models/2D/Hiyori.model3-2025.json"  # 替换为你的模型路径
    }
    
    try:
        # 创建模型实例
        model = Live2DModel(config)
        
        # 设置窗口位置和大小
        model.resize(500, 500)
        model.move(100, 100)
        
        # 在第一次显示模型之前
        logger.info("模型初始化中...")
        
        # 创建调试窗口
        from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton, QSlider
        debug_window = QWidget()
        debug_window.setWindowTitle("嘴型同步测试")
        debug_layout = QVBoxLayout(debug_window)
        
        status_label = QLabel("状态: 准备中")
        debug_layout.addWidget(status_label)
        
        mouth_value_label = QLabel("嘴部值: 0.0")
        debug_layout.addWidget(mouth_value_label)
        
        # 添加播放按钮
        play_button = QPushButton("播放 (1.wav)")
        debug_layout.addWidget(play_button)
        
        # 添加停止按钮
        stop_button = QPushButton("停止")
        debug_layout.addWidget(stop_button)
        
        # 添加强度滑块
        intensity_label = QLabel("嘴型强度: 3.0")
        debug_layout.addWidget(intensity_label)
        
        intensity_slider = QSlider(1)  # 水平滑块
        intensity_slider.setMinimum(0)
        intensity_slider.setMaximum(100)
        intensity_slider.setValue(30)  # 默认值3.0
        debug_layout.addWidget(intensity_slider)
        
        # 设置大小并显示
        debug_window.resize(300, 200)
        debug_window.move(650, 100)
        debug_window.show()
        
        # 创建WavHandler监视器
        wav_watcher = None
        
        # 更新嘴型函数
        def update_mouth_value(value):
            try:
                # 更新Label显示
                mouth_value_label.setText(f"嘴部值: {value:.2f}")
                
                # 设置模型嘴部参数
                if model.model:
                    try:
                        # 直接设置参数值
                        model.model.SetParameterValue(StandardParams.ParamMouthOpenY, value)
                    except Exception as e:
                        logger.error(f"设置嘴部参数失败: {e}")
                        # 尝试使用字符串参数名
                        model.model.SetParameterValue("ParamMouthOpenY", value)
            except Exception as e:
                logger.error(f"更新嘴部值错误: {e}")
                status_label.setText(f"状态: 错误 - {e}")
        
        # 播放按钮点击事件
        def on_play_clicked():
            nonlocal wav_watcher
            try:
                # 获取音频文件路径
                audio_path = os.path.abspath("1.wav")
                if not os.path.exists(audio_path):
                    status_label.setText(f"状态: 错误 - 文件不存在: {audio_path}")
                    return
                
                # 停止之前的监视器
                if wav_watcher and wav_watcher.isRunning():
                    wav_watcher.stop()
                
                # 播放音频 (重要：先播放音频)
                status_label.setText("状态: 播放音频...")
                try:
                    if sys.platform == "win32":
                        import winsound
                        winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception as e:
                    logger.error(f"播放音频失败: {e}")
                    status_label.setText(f"状态: 音频播放失败 - {e}")
                    return
                
                # 创建新的监视器
                status_label.setText(f"状态: 初始化WavHandler...")
                wav_watcher = WavHandlerWatcher(audio_path)
                
                # 设置强度
                intensity = intensity_slider.value() / 15.0
                wav_watcher.lip_sync_intensity = intensity
                intensity_label.setText(f"嘴型强度: {intensity:.1f}")
                
                # 连接信号
                wav_watcher.update_signal.connect(update_mouth_value)
                wav_watcher.finished_signal.connect(lambda: status_label.setText("状态: 播放完成"))
                wav_watcher.error_signal.connect(lambda err: status_label.setText(f"状态: 错误 - {err}"))
                
                # 启动监视器
                wav_watcher.start()
                status_label.setText("状态: 播放中...")
                
            except Exception as e:
                logger.error(f"播放出错: {e}")
                status_label.setText(f"状态: 错误 - {e}")
                traceback.print_exc()
        
        # 停止按钮点击事件
        def on_stop_clicked():
            nonlocal wav_watcher
            if wav_watcher and wav_watcher.isRunning():
                wav_watcher.stop()
                status_label.setText("状态: 已停止")
            
            # 重置嘴部参数
            update_mouth_value(0.0)
        
        # 强度滑块值变化事件
        def on_intensity_changed(value):
            intensity = value / 10.0
            intensity_label.setText(f"嘴型强度: {intensity:.1f}")
            if wav_watcher:
                wav_watcher.lip_sync_intensity = intensity
        
        # 连接信号和槽
        play_button.clicked.connect(on_play_clicked)
        stop_button.clicked.connect(on_stop_clicked)
        intensity_slider.valueChanged.connect(on_intensity_changed)
        
        # 显示模型
        model.show()
        
        # 设置退出处理
        app.aboutToQuit.connect(lambda: cleanup(wav_watcher))
        
        # 运行应用
        logger.info("进入事件循环...")
        return app.exec_()
    
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        traceback.print_exc()
        return False
    
    finally:
        # 清理Live2D引擎
        dispose_live2d()

def cleanup(wav_watcher):
    """清理资源"""
    if wav_watcher and wav_watcher.isRunning():
        logger.info("停止WavHandler监视线程...")
        wav_watcher.stop()
    logger.info("清理资源完成")

if __name__ == "__main__":
    try:
        exit_code = test_lip_sync()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"测试失败: {e}")
        traceback.print_exc()
        sys.exit(1)