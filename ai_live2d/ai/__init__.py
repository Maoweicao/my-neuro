"""
AI能力模块 - 提供大语言模型交互、记忆管理、上下文管理和自动聊天功能
"""

from .llm_client import LLMClient
from .memory_manager import MemoryManager
from .context_processor import ContextProcessor
from .prompt_integrator import PromptIntegrator
from .mcp_client import MCPClient
from .auto_chat import AutoChatModule

__all__ = ['LLMClient', 'MemoryManager', 'ContextProcessor', 'PromptIntegrator', 'MCPClient', 'AutoChatModule']