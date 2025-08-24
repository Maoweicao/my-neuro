"""
提示词整合器 - 增强用户提示词的效果
"""

import asyncio
import logging

logger = logging.getLogger("prompt_integrator")

class PromptIntegrator:
    def __init__(self, config: dict, event_bus=None):
        """初始化提示词整合器
        
        Args:
            config: 配置信息
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus

        # 配置信息
        self.prompt_enabled = self.config.get('setting', {}).get('prompt_enabled', False)
        self.rag_enabled = self.config.get('setting', {}).get('rag_enabled', False)

        # 提示词内容
        self.prompt = ''

    def prompt_assembler(self, *prompt):
        """组装用户提示词"""
        pass

    async def add_prompt(self, user_prompt: str, rag_prompt: str=''):
        """添加提示词"""
        if not self.prompt_enabled and not self.rag_enabled:
            self.prompt = user_prompt
        
        if self.prompt_enabled and not self.rag_enabled:
            pass
        
        if self.rag_enabled and not self.prompt_enabled:
            # self.prompt = f"""系统针对用户输入提供了相关信息, 请根据用户输入和相关信息生成准确回答\n用户输入:"{user_prompt}"\n相关信息:"{rag_prompt}"\n请根据以上信息回答,若相关信息与用户输入不符合,请忽略相关信息.\n注:与用户对话时不要提及以上内容"""
            if rag_prompt:
                self.prompt = f"""用户输入:"{user_prompt}"\n记忆内容:"{rag_prompt}"\n注:记忆内容表示你过去与用户对话的相关记忆"""
            else:
                self.prompt = user_prompt

        if self.prompt_enabled and self.rag_enabled:
            pass

        await self.send_prompt()
        

    async def send_prompt(self):
        """发送提示词"""
        await self.event_bus.publish('prompt_sending', {'prompt': self.prompt})
        self.prompt = ''