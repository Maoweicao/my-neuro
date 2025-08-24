"""
视觉功能模块 - 负责截图和图像处理
"""

import os
import base64
import logging
import aiohttp
import io
from PIL import ImageGrab
from typing import Dict, List, Any, Optional

logger = logging.getLogger("vision_client")

class VisionClient:
    """视觉功能客户端类"""
    
    def __init__(self, config, event_bus=None):
        """初始化视觉功能客户端"""
        self.config = config
        self.event_bus = event_bus
        
        # 从配置中获取视觉相关配置
        vision_config = config.get("vision", {})
        self.check_url = vision_config.get("check_url", "http://127.0.0.1:6006/check")
        
        # 创建持久化HTTP连接池
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit_per_host=4),
            timeout=aiohttp.ClientTimeout(total=10)  # 短超时避免阻塞
        )
        
        logger.info("初始化视觉功能模块... [ 完成 ]")
    
    async def close(self):
        """关闭资源"""
        if not self.session.closed:
            await self.session.close()
    
    async def check_vision_needed(self, text: str) -> bool:
        """高效判断是否需要截图"""
        try:
            # 构建请求URL
            url = f"{self.check_url}?text={text}"
            # 使用连接池发送请求
            async with self.session.post(
                url,
                json={"text": text},  # 使用JSON体更安全
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    logger.warning(f"视觉检查API状态码: {response.status}")
                    return False
                
                # 快速解析响应
                response_data = await response.json()
                logger.debug(f"视觉检查结果: {response_data}")
                
                # 判断是否需要截图
                need_vision = response_data.get("需要视觉") == "是"
                return need_vision
        
        except aiohttp.ClientError as e:
            logger.warning(f"视觉检查网络错误: {e}")
            return False
        except Exception as e:
            logger.error(f"视觉检查处理错误: {e}")
            return False
    
    async def take_screenshot(self):
        """截图并通过base64转成二进制图片数据"""
        try:
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG')
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return image_data
        
        except Exception as e:
            logger.error(f"截图错误: {e}")
            return None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文管理器退出"""
        await self.close()