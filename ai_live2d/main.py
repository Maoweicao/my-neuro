#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI桌面宠物核心服务 - 集成Qt事件循环和asyncio
"""
import sys
import os
# === 添加强制UTF-8编码设置 ===
if sys.platform.startswith("win"):
    # Windows系统需要特别处理
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') # type: ignore
    sys.stderr.reconfigure(encoding='utf-8', errors='replace') # type: ignore
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"
else:
    # 非Windows系统
    sys.stdout.reconfigure(encoding='utf-8') # type: ignore
    sys.stderr.reconfigure(encoding='utf-8') # type: ignore

import asyncio
import logging
import signal
import sys
import os
import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

# Qt相关导入
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QSurfaceFormat

# 导入核心管理器
from core.app_manager import AppManager
from utils.logger import setup_logger

# 导入qasync
import qasync

class PetService:
    """AI桌面宠物服务类 - 支持Qt和asyncio集成"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.app_manager: AppManager|None = None
        self.qt_app: QApplication|None = None
        self.logger: Any = None
        self._running: bool = False
        self._shutdown_event = asyncio.Event()
        
        # 进程间通信相关
        self.interrupt_socket = None
        self.interrupt_thread = None
        self.interrupt_signal_file = Path("interrupt_signal.tmp")
        self.interrupt_port = 8889  # 固定的中断通信端口
        self.event_loop = None  # 保存事件循环引用
        
    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 设置日志
            self.logger = setup_logger(
                level=logging.INFO,
                log_file="pet_system.log"
            )
            self.logger.info(">>> 初始化AI桌宠系统... [ 进行中 ]")
            
            # 记录主进程PID
            import os
            main_pid = os.getpid()
            try:
                with open('main_pid.txt', 'w', encoding='utf-8') as f:
                    f.write(str(main_pid))
                self.logger.info(f">>> 主进程PID已记录: {main_pid}")
            except Exception as e:
                self.logger.warning(f">>> 记录主进程PID失败: {e}")
            
            # 检查配置文件
            if not self.config_path.exists():
                raise FileNotFoundError(f">>> 配置文件不存在: {self.config_path}")
            
            # 创建应用管理器
            self.app_manager = AppManager(str(self.config_path))
            
            # 初始化应用管理器
            await self.app_manager.initialize()
            
            # 启动中断监听器
            self.start_interrupt_listener()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 系统初始化失败: {e}")
            raise
    
    async def start(self) -> None:
        """启动服务"""
        try:
            self._running = True
            
            # 保存当前事件循环引用，用于线程间通信
            self.event_loop = asyncio.get_running_loop()
            
            # 启动应用管理器
            assert self.app_manager is not None
            await self.app_manager.start()
            self.logger.info(">>> 初始化AI桌宠系统... [ 完成 ]")
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f">>> 服务运行错误: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """关闭服务"""
        if not self._running:
            return
            
        self._running = False
        
        try:
            if self.logger:
                self.logger.info(">>> 关闭AI桌宠系统... [ 进行中 ]")
            
            # 关闭应用管理器
            if self.app_manager:
                await self.app_manager.shutdown()
                if self.logger:
                    self.logger.info(">>> 应用管理器... [ 已关闭 ]")
            
            # 停止中断监听器
            self.stop_interrupt_listener()
            
            # 清理事件循环引用
            self.event_loop = None
            
            # 清理PID文件
            import os
            pid_files = ['main_pid.txt', 'tts_pid.txt', 'asr_pid.txt', 'audio_pid.txt']
            for pid_file in pid_files:
                try:
                    if os.path.exists(pid_file):
                        os.remove(pid_file)
                        if self.logger:
                            self.logger.info(f">>> 清理PID文件: {pid_file}")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 清理PID文件失败 {pid_file}: {e}")
            
            if self.logger:
                self.logger.info(">>> AI桌宠系统... [ 已关闭 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 关闭服务时出错: {e}")
    
    def request_shutdown(self):
        """请求关闭服务"""
        if self._running:
            self._shutdown_event.set()

    def start_interrupt_listener(self):
        """启动中断监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 启动中断监听器... [ 进行中 ]")
            
            # 启动socket监听线程
            self.interrupt_thread = threading.Thread(
                target=self._interrupt_listener_thread,
                daemon=True
            )
            self.interrupt_thread.start()
            
            if self.logger:
                self.logger.info(">>> 中断监听器... [ 已启动 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 启动中断监听器失败: {e}")

    def stop_interrupt_listener(self):
        """停止中断监听器"""
        try:
            if self.logger:
                self.logger.info(">>> 停止中断监听器... [ 进行中 ]")
            
            # 关闭socket
            if self.interrupt_socket:
                self.interrupt_socket.close()
                self.interrupt_socket = None
            
            # 等待线程结束
            if self.interrupt_thread and self.interrupt_thread.is_alive():
                self.interrupt_thread.join(timeout=2.0)
            
            if self.logger:
                self.logger.info(">>> 中断监听器... [ 已停止 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 停止中断监听器失败: {e}")

    def _interrupt_listener_thread(self):
        """中断监听器线程"""
        try:
            # 创建socket服务器
            self.interrupt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.interrupt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.interrupt_socket.bind(('127.0.0.1', self.interrupt_port))
            self.interrupt_socket.listen(1)
            self.interrupt_socket.settimeout(1.0)  # 1秒超时，用于定期检查
            
            if self.logger:
                self.logger.info(f">>> 中断监听器绑定到端口: {self.interrupt_port}")
            
            while self._running:
                try:
                    # 同时监听socket连接和文件信号
                    self._check_interrupt_signal()
                    
                    # 尝试接受socket连接
                    try:
                        client_socket, addr = self.interrupt_socket.accept()
                        self._handle_interrupt_connection(client_socket, addr)
                    except socket.timeout:
                        continue  # 超时，继续循环
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f">>> 中断监听器循环出错: {e}")
                    time.sleep(0.1)  # 短暂延迟
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 中断监听器线程异常: {e}")
        finally:
            if self.interrupt_socket:
                self.interrupt_socket.close()

    def _check_interrupt_signal(self):
        """检查中断信号文件"""
        try:
            if self.interrupt_signal_file.exists():
                # 读取信号文件
                with open(self.interrupt_signal_file, 'r', encoding='utf-8') as f:
                    signal_data = json.load(f)
                
                if self.logger:
                    self.logger.info(">>> 收到中断信号文件")
                
                # 处理中断信号
                self._process_interrupt_signal(signal_data)
                
                # 删除信号文件
                self.interrupt_signal_file.unlink()
                
        except FileNotFoundError:
            pass  # 文件不存在，正常情况
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 处理中断信号文件出错: {e}")

    def _handle_interrupt_connection(self, client_socket, addr):
        """处理中断连接"""
        try:
            if self.logger:
                self.logger.info(f">>> 收到中断连接: {addr}")
            
            # 接收数据
            data = client_socket.recv(1024)
            if data:
                signal_data = json.loads(data.decode('utf-8'))
                self._process_interrupt_signal(signal_data)
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f">>> 处理中断连接出错: {e}")
        finally:
            client_socket.close()

    def _process_interrupt_signal(self, signal_data):
        """处理中断信号"""
        try:
            if self.logger:
                self.logger.info(f">>> 处理中断信号: {signal_data}")
            
            signal_type = signal_data.get('type', 'interrupt')
            
            if signal_type == 'interrupt':
                # 安全地在主事件循环中运行异步中断操作
                if self.event_loop and self.event_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self._perform_interrupt(), 
                        self.event_loop
                    )
                    # 可选：等待完成或设置回调
                    # future.add_done_callback(lambda f: print("中断操作完成"))
                else:
                    if self.logger:
                        self.logger.warning(">>> 事件循环不可用，无法执行异步中断操作")
            elif signal_type == 'shutdown':
                # 请求关闭服务
                self.request_shutdown()
            else:
                if self.logger:
                    self.logger.warning(f">>> 未知的信号类型: {signal_type}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 处理中断信号时出错: {e}")
                import traceback
                self.logger.error(f">>> 错误详情: {traceback.format_exc()}")

    async def _perform_interrupt(self):
        """执行中断操作"""
        try:
            if self.logger:
                self.logger.info(">>> 执行中断操作... [ 进行中 ]")
            
            # 中断LLM输出
            if self.app_manager and hasattr(self.app_manager, 'llm_client') and self.app_manager.llm_client:
                if hasattr(self.app_manager.llm_client, 'interrupt'):
                    self.app_manager.llm_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> LLM输出已中断")
            
            # 中断TTS播放
            if self.app_manager and hasattr(self.app_manager, 'tts_client') and self.app_manager.tts_client:
                if hasattr(self.app_manager.tts_client, 'interrupt'):
                    self.app_manager.tts_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> TTS播放已中断")
                elif hasattr(self.app_manager.tts_client, 'stop'):
                    await self.app_manager.tts_client.stop()
                    if self.logger:
                        self.logger.info(">>> TTS播放已中断")
            
            # 中断ASR
            if self.app_manager and hasattr(self.app_manager, 'asr_client') and self.app_manager.asr_client:
                if hasattr(self.app_manager.asr_client, 'interrupt'):
                    self.app_manager.asr_client.interrupt()
                    if self.logger:
                        self.logger.info(">>> ASR已中断")
                elif hasattr(self.app_manager.asr_client, 'stop'):
                    await self.app_manager.asr_client.stop()
                    if self.logger:
                        self.logger.info(">>> ASR已中断")
            
            # 中断字幕显示
            if self.app_manager and hasattr(self.app_manager, 'subtitle_manager') and self.app_manager.subtitle_manager:
                self.app_manager.subtitle_manager.clear_text()
                if self.logger:
                    self.logger.info(">>> 字幕已中断")
            
            # 停止Live2D动作
            if self.app_manager and hasattr(self.app_manager, 'live2d_model') and self.app_manager.live2d_model:
                # 这里可以调用Live2D的停止方法
                if self.logger:
                    self.logger.info(">>> Live2D动作已停止")
            
            if self.logger:
                self.logger.info(">>> 中断操作... [ 完成 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 执行中断操作时出错: {e}")


class QtAsyncManager:
    """Qt和asyncio集成管理器"""
    
    def __init__(self):
        self.qt_app = None
        self.event_loop = None
        self.service = None
        self.logger = logging.getLogger("qt_async")
        
    def setup_qt_application(self) -> 'QApplication|Any':
        """设置Qt应用程序"""
        try:
            # 检查是否已经有QApplication实例
            if QApplication.instance() is None:
                # 设置OpenGL格式（针对Live2D）
                format = QSurfaceFormat.defaultFormat()
                format.setSwapInterval(0)  # 禁用垂直同步
                QSurfaceFormat.setDefaultFormat(format)
                
                # 创建QApplication
                self.qt_app = QApplication(sys.argv)
                self.qt_app.setQuitOnLastWindowClosed(False)  # 防止窗口关闭时退出
                self.logger.info(">>> Qt应用程序... [ 已创建 ]")
            else:
                self.qt_app = QApplication.instance()
                self.logger.info(">>> 使用现有的Qt应用程序实例")
            
            return self.qt_app
            
        except Exception as e:
            self.logger.error(f">>> 设置Qt应用程序失败: {e}")
            raise
    
    def setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        def signal_handler(sig, frame):
            self.logger.info(f">>> 收到信号 {sig}")
            if self.service:
                self.service.request_shutdown()
            if self.qt_app:
                self.qt_app.quit()
        
        # 设置优雅关闭信号
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
        
        # Windows特殊处理
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, signal_handler)
    
    async def run_with_qasync(self, config_path: str) -> None|int:
        """使用qasync运行"""
        try:
            # 创建Qt应用
            qt_app = self.setup_qt_application()
            
            # 设置qasync事件循环
            self.event_loop = qasync.QEventLoop(qt_app)
            asyncio.set_event_loop(self.event_loop)
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            # 创建服务
            self.service = PetService(config_path)
            
            # 使用事件循环运行服务
            async def main_task():
                try:
                    assert self.service is not None
                    await self.service.initialize()
                    await self.service.start()
                    return 0
                except KeyboardInterrupt:
                    self.logger.info(">>> 用户中断服务")
                    return 0
                except Exception as e:
                    self.logger.error(f">>> 服务运行失败: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return 1
            
            # 运行主任务
            with self.event_loop:
                exit_code = self.event_loop.run_until_complete(main_task())
            
            return exit_code
            
        except Exception as e:
            self.logger.error(f">>> qasync运行失败: {e}")
            return 1

def main() -> int|None:
    """主函数"""
    # 获取配置文件路径
    config_path = os.getenv("PET_CONFIG", "config.json")
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # 创建Qt异步管理器
    qt_manager = QtAsyncManager()
    
    try:
        # 使用qasync
        exit_code = asyncio.run(qt_manager.run_with_qasync(config_path))
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n>>> 用户中断启动")
        return 0
    except Exception as e:
        print(f">>> 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f">>> 程序异常退出: {e}")
        sys.exit(1)