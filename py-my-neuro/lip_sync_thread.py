"""
嘴型同步线程 - 用于处理Live2D模型的嘴型同步
"""

import os
import time
import logging
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal

# 需要从live2d包导入WavHandler
from live2d.utils.lipsync import WavHandler

logger = logging.getLogger("lip_sync_thread")

class LipSyncThread(QThread):
    """嘴型同步线程，用于处理WavHandler的更新"""
    
    # 定义信号
    update_signal = pyqtSignal(float)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, audio_path, event_bus=None, intensity=3.0):
        super().__init__()
        self.audio_path = audio_path
        self.event_bus = event_bus
        self.is_running = False
        self.wav_handler = None
        self.intensity = intensity
        logger.info(f"LipSyncThread初始化: {audio_path}")
    
    def run(self):
        try:
            # 添加文件存在性检查
            if not os.path.exists(self.audio_path):
                logger.error(f"音频文件不存在: {self.audio_path}")
                self.error_signal.emit(f"音频文件不存在: {self.audio_path}")
                return
            
            logger.info(f"嘴型同步线程开始运行: {self.audio_path}")
            
            # 初始化WavHandler
            self.wav_handler = WavHandler()
            
            # Start方法不返回值，直接调用
            logger.info(f"启动WavHandler: {self.audio_path}")
            self.wav_handler.Start(self.audio_path)
            
            # 验证初始化是否成功
            try:
                rms = self.wav_handler.GetRms()
                logger.info(f"初始RMS值: {rms}")
            except Exception as e:
                logger.error(f"获取RMS值失败: {e}")
                self.error_signal.emit(f"嘴型同步初始化失败: {e}")
                return
                
            self.is_running = True
            logger.info(f"嘴型同步初始化成功: {self.audio_path}")

            # 通知事件总线嘴型同步已开始
            if self.event_bus:
                asyncio.run_coroutine_threadsafe(
                    self.event_bus.publish("lip_sync_started", {
                        "audio_path": self.audio_path
                    }),
                    asyncio.get_event_loop()
                )
            
            # 处理循环
            while self.is_running:
                if self.wav_handler:
                    if self.wav_handler.Update():
                        # 获取RMS值并计算嘴部开合值
                        rms = self.wav_handler.GetRms()
                        mouth_value = rms * self.intensity
                        
                        # 限制值范围
                        mouth_value = max(0.0, min(2.0, mouth_value))
                        
                        # 发送更新信号
                        self.update_signal.emit(mouth_value)
                        
                        # 短暂休眠，避免CPU占用过高
                        time.sleep(1/60)  # 约60fps
                    else:
                        # 播放完成
                        logger.info("嘴型同步播放完成")
                        self.is_running = False
                        break
                else:
                    # WavHandler不存在，退出循环
                    logger.error("WavHandler不存在，退出循环")
                    self.is_running = False
                    break
                    
            # 发送完成信号
            self.finished_signal.emit()
            
        except Exception as e:
            logger.error(f"嘴型同步线程错误: {e}")
            self.error_signal.emit(str(e))
            import traceback
            logger.error(traceback.format_exc())
            # 通知事件总线错误
            if self.event_bus:
                self.event_bus.publish_sync("lip_sync_started", {
                    "audio_path": self.audio_path
                })
                    
        finally:
            # 确保资源释放
            self.is_running = False
            # 显式清空WavHandler引用
            if hasattr(self, 'wav_handler') and self.wav_handler:
                logger.info("清理WavHandler资源")
                self.wav_handler = None
            logger.info("嘴型同步线程已退出")
    
    def stop(self):
        """停止嘴型同步"""
        logger.info("正在停止嘴型同步线程...")
        self.is_running = False
        
        # 等待线程结束，但不阻塞太久
        if self.isRunning():
            self.wait(500)  # 最多等待0.5秒
            
            # 如果还在运行，强制终止
            if self.isRunning():
                logger.warning("嘴型同步线程等待超时，强制终止")
                self.terminate()
        
        # 显式清空WavHandler引用
        if hasattr(self, 'wav_handler') and self.wav_handler:
            logger.info("清理WavHandler资源")
            self.wav_handler = None