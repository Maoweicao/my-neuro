"""
截图工具 - 提供截图功能
"""

import os
import logging
import tempfile
from typing import Optional

logger = logging.getLogger("screenshot")

def take_screenshot(output_path: Optional[str] = None) -> Optional[str]:
    """截图函数
    
    Args:
        output_path: 输出文件路径，如果为None则使用临时文件
    
    Returns:
        截图文件路径，失败则返回None
    """
    try:
        # 如果没有提供输出路径，创建临时文件
        if not output_path:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "screenshot.png")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        return _take_screenshot(output_path)
    
    except Exception as e:
        logger.error(f"截图错误: {e}")
        return None

def _take_screenshot(output_path: str) -> Optional[str]:
    """进行截图
    
    Args:
        output_path: 输出文件路径
    
    Returns:
        截图文件路径，失败则返回None
    """
    try:
        # 首先尝试使用pyautogui
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(output_path)
            return output_path
        except ImportError:
            pass
        
        # 尝试使用PIL
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(output_path)
            return output_path
        except ImportError:
            pass
    
    except Exception as e:
        logger.error(f"Windows截图错误: {e}")
        return None