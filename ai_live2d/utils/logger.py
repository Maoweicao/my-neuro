"""
日志工具 - 提供统一的日志设置，支持终端颜色输出
"""

import os
import logging
from logging.handlers import RotatingFileHandler

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


def setup_logger(level=logging.INFO, log_file="pet_system.log"):
    """设置全局日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
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
    
    # 创建控制台处理器 (带颜色)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器 (不带颜色)
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