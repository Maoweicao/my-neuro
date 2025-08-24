"""
配置加载器模块 - 负责读取和验证config.json配置文件
"""

import json
from typing import Dict, Any
import logging

logger = logging.getLogger("config_loader")

class ConfigLoader:
    """配置加载器类，处理配置文件的读取、验证和保存"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path: str = config_path
        self.config: Dict = {}
        
        logger.info(f"初始化配置加载器，配置文件路径: {config_path}... [ 进行中 ]")
    
    def load(self) -> Dict[str, Any]:
        """加载配置文件
        
        Returns:
            加载的配置对象
        
        Raises:
            Exception: 配置文件加载或解析错误
        """
        try:
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = file.read()
            
            try:
                # 解析JSON
                self.config = json.loads(config_data)
                logger.info("加载配置文件... [ 完成 ]")
                
                return self.config
            except json.JSONDecodeError as e:
                logger.error(f"JSON格式错误: {e}")
                raise Exception(f"配置文件JSON格式错误: {e}")
        
        except FileNotFoundError:
            logger.warning(f"配置文件 {self.config_path} 不存在，请检测配置文件是否合格")
            raise
            
        except Exception as e:
            logger.error(f"配置文件读取失败: {e}")
            raise