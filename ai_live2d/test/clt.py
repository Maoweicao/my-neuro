#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置加载器测试脚本
"""

import sys
import os
import json
import tempfile
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_config_loader")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置加载器
from utils.config_loader import ConfigLoader

def test_config_loader():
    """测试配置加载器的基本功能"""
    # 创建临时配置文件
    temp_config = os.path.join(tempfile.gettempdir(), "test_config.json")
    temp_default_config = os.path.join(tempfile.gettempdir(), "default_config.json")
    
    # 创建测试配置
    test_config = {
        "test": {
            "value1": 123,
            "value2": "test",
            "nested": {
                "value3": True
            }
        },
        "empty_section": {}
    }
    
    # 创建默认配置
    default_config = {
        "default": {
            "value1": 456,
            "value2": "default"
        }
    }
    
    try:
        # 写入测试配置文件
        with open(temp_config, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, indent=2)
        
        # 写入默认配置文件
        with open(temp_default_config, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        # 创建配置加载器
        logger.info("测试加载现有配置")
        config_loader = ConfigLoader(temp_config)
        config = config_loader.load()
        
        # 验证配置内容
        assert config["test"]["value1"] == 123, "加载的配置值不匹配"
        assert config["test"]["value2"] == "test", "加载的配置值不匹配"
        assert config["test"]["nested"]["value3"] == True, "加载的嵌套配置值不匹配"
        
        # 测试get方法
        logger.info("测试get方法")
        value1 = config_loader.get("test.value1")
        value2 = config_loader.get("test.value2")
        value3 = config_loader.get("test.nested.value3")
        missing = config_loader.get("missing.key", "default_value")
        
        assert value1 == 123, "get方法返回的值不匹配"
        assert value2 == "test", "get方法返回的值不匹配"
        assert value3 == True, "get方法返回的嵌套值不匹配"
        assert missing == "default_value", "get方法的默认值不匹配"
        
        # 测试update方法
        logger.info("测试update方法")
        result = config_loader.update("test.value1", 999)
        assert result == True, "update方法应该返回True"
        
        # 重新加载配置验证更新
        config = config_loader.load()
        assert config["test"]["value1"] == 999, "更新后的配置值不匹配"
        
        # 测试创建新的嵌套配置
        logger.info("测试创建新的嵌套配置")
        result = config_loader.update("new.nested.value", "new_value")
        assert result == True, "update方法应该返回True"
        
        # 重新加载配置验证更新
        config = config_loader.load()
        assert config["new"]["nested"]["value"] == "new_value", "新创建的嵌套配置值不匹配"
        
        # 测试加载不存在的配置文件
        logger.info("测试加载不存在的配置文件")
        missing_config_path = os.path.join(tempfile.gettempdir(), "non_existent_config.json")
        
        # 删除文件如果存在
        if os.path.exists(missing_config_path):
            os.remove(missing_config_path)
        
        try:
            # 设置默认配置路径
            missing_loader = ConfigLoader(missing_config_path)
            missing_loader.default_config_path = temp_default_config
            
            # 加载不存在的配置，应该加载默认配置
            missing_config = missing_loader.load()
            
            # 验证加载的是默认配置
            assert missing_config["default"]["value1"] == 456, "未加载正确的默认配置"
            assert os.path.exists(missing_config_path), "默认配置未被保存到指定路径"
        except Exception as e:
            logger.error(f"加载不存在配置失败: {e}")
            raise
        finally:
            # 清理生成的文件
            if os.path.exists(missing_config_path):
                os.remove(missing_config_path)
        
        logger.info("配置加载器测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # 清理临时文件
        for file_path in [temp_config, temp_default_config]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")

if __name__ == "__main__":
    try:
        result = test_config_loader()
        logger.info(f"测试结果: {'通过' if result else '失败'}")
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())