"""
上下文处理器 - 处理LLM输入以及上下文内容
"""

import logging

logger = logging.getLogger("context_processor")

class ContextProcessor:
    """上下文处理器类(LLM的附属模块)，处理LLM输入以及上下文内容"""
    
    def __init__(self, config, event_bus=None):
        """初始化上下文处理器
        
        Args:
            config: 配置信息，包含上下文相关配置
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus

        # LLM输出文本相关
        self.text = ''
        self.full_text = ''
        self.buffer = ''
        self.is_final = False

        logger.info("初始化上下文处理器... [ 成功 ]")

    async def handle_llm_output(self, text: str, full_text: str, is_final: bool):
        """处理LLM的输入
        
        Args:
            text: LLM流式输出的token
            full_text: LLM已输出的内容
            is_final: 流式输出是否完成
        """
        try:
            self.text = text
            self.full_text += text
            self.is_final = is_final

            # 普通文本流式输出路径（保持你的逻辑）
            if not is_final:
                self.buffer += text
                if any(punct in text for punct in '.。！!？?，,;；~'):
                    await self.event_bus.publish('llm_streaming', {
                                "text": self.buffer,
                                "full_text": self.full_text,
                                "is_final": is_final
                            })
                    self.buffer = ''

            if is_final:
                await self.event_bus.publish('llm_streaming', {
                            "text": self.buffer,
                            "full_text": self.full_text,
                            "is_final": is_final
                            })
                await self.event_bus.publish("llm_complete", {"text": self.full_text})
                self.buffer = ''
                self.full_text = ''
        
        except Exception as e:
            logger.error(f"上下文处理器处理失败: {e}")

    async def __aenter__(self):
        """异步上下文处理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """异步上下文处理器退出"""
        await self.close()

    async def close(self):
        """预留的清理方法，避免 __aexit__ 报错"""
        return