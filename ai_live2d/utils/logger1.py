"""
超级无敌酷炫吊炸天的日志工具 - 提供统一的日志设置，支持终端颜色输出和流式输出
"""

import os
import logging
import sys
import asyncio
import re
import contextlib
from logging.handlers import RotatingFileHandler
from collections import deque

class AsyncTypewriterConsoleHandler(logging.Handler):
    """异步流式输出控制台处理器"""
    
    def __init__(self, char_delay=0.25, streaming=True):
        """
        Args:
            char_delay: 每个字符之间的延迟（秒）
            streaming: 是否启用流式输出
        """
        super().__init__()
        self.char_delay = char_delay
        self.streaming = streaming
        self.queue = deque()
        self.index = 0
        self.current_task = None
        self.pattern = r'^(.*?(- (?:INFO|WARNING) - ))(.*)$'
        self.loop = asyncio.get_event_loop()
        
    def emit(self, record):
        try:
            # 获取格式化后的消息（包括颜色）
            message = self.format(record)
            
            # 如果启用流式输出，加入队列异步处理
            if self.streaming:
                self.queue.append(message)
                if self.current_task is None or self.current_task.done():
                    self.current_task = self.loop.create_task(self._process_queue())
            else:
                # 非流式输出直接打印
                sys.stdout.write(message)
                sys.stdout.flush()
        except Exception:
            self.handleError(record)
    
    async def _process_queue(self):
        """异步处理消息队列，实现流式输出"""
        while self.queue:
            message = self.queue.popleft()
            match = re.match(self.pattern, message)
            sys.stdout.write(match.group(1))
            sys.stdout.flush()
            message = match.group(3) + '\n'
            if len(message) < 30 and len(self.queue) < 5:
                char_delay = self.char_delay / len(message)
            else:
                char_delay = 0.0
            try:
                self.index = 0
                # 逐字输出消息
                for char in message:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    self.index += 1
                    if self.queue and self.index >= 10:
                        sys.stdout.write(message[self.index:])
                        sys.stdout.flush()
                        break
                    await asyncio.sleep(char_delay)
            except Exception:
                pass
    
    def close(self):
        """关闭处理器"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        super().close()


class ColoredFormatter(logging.Formatter):
    """支持终端ANSI颜色的自定义格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        logging.DEBUG: "\033[0;36m",    # 青色
        logging.INFO: "\033[0;32m",     # 绿色
        logging.WARNING: "\033[1;33m",  # 黄色
        logging.ERROR: "\033[1;31m",    # 红色
        logging.CRITICAL: "\033[1;41m"  # 红底白字
    }
    RESET = "\033[0m"
    
    def format(self, record):
        message = super().format(record)
        color = self.COLORS.get(record.levelno, '')
        return f"{color}{message}{self.RESET}"


def setup_logger(level=logging.INFO, 
                 log_file="pet_system.log", 
                 streaming=True, 
                 char_delay=0.25):
    """设置全局日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        streaming: 是否启用流式输出
        char_delay: 流式输出时每个字符的延迟（秒）
    """
    # 创建日志目录
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 如果已经有处理器，则清除
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # 创建控制台处理器 (带颜色和流式输出)
    console_handler = AsyncTypewriterConsoleHandler(char_delay=char_delay, streaming=streaming)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器 (不带颜色，不流式输出)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return root_logger


# 提供临时启用/禁用流式输出的上下文管理器
@contextlib.contextmanager
def temporary_streaming(enable=True, char_delay=0.03):
    """临时修改流式输出设置
    
    Args:
        enable: 是否启用流式输出
        char_delay: 字符延迟时间
    """
    root_logger = logging.getLogger()
    original_settings = {}
    
    # 保存当前控制台处理器设置
    for handler in root_logger.handlers:
        if isinstance(handler, AsyncTypewriterConsoleHandler):
            original_settings['streaming'] = handler.streaming
            original_settings['char_delay'] = handler.char_delay
            handler.streaming = enable
            handler.char_delay = char_delay
            break
    
    try:
        yield
    finally:
        # 恢复原始设置
        for handler in root_logger.handlers:
            if isinstance(handler, AsyncTypewriterConsoleHandler) and original_settings:
                handler.streaming = original_settings['streaming']
                handler.char_delay = original_settings['char_delay']