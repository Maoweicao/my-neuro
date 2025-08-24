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
        
    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 设置日志
            self.logger = setup_logger(
                level=logging.INFO,
                log_file="pet_system.log"
            )
            self.logger.info(">>> 初始化AI桌宠系统... [ 进行中 ]")
            
            # 检查配置文件
            if not self.config_path.exists():
                raise FileNotFoundError(f">>> 配置文件不存在: {self.config_path}")
            
            # 创建应用管理器
            self.app_manager = AppManager(str(self.config_path))
            
            # 初始化应用管理器
            await self.app_manager.initialize()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 系统初始化失败: {e}")
            raise
    
    async def start(self) -> None:
        """启动服务"""
        try:
            self._running = True
            
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
            
            if self.logger:
                self.logger.info(">>> AI桌宠系统... [ 已关闭 ]")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f">>> 关闭服务时出错: {e}")
    
    def request_shutdown(self):
        """请求关闭服务"""
        if self._running:
            self._shutdown_event.set()

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