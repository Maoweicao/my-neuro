"""
对各模块进行连接，增强模块的独立性及易修改性
"""

import asyncio
import logging
from typing import Dict, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from core.event_bus import EventBus

# 导入配置加载器
from utils.config_loader import ConfigLoader

# 导入模型相关模块
from models.live2d_model import Live2DModel, init_live2d

# 导入界面相关模块
from interface.subtitle_manager import SubtitleManager
from interface.user_input import UserInputWindow

# 导入AI能力相关模块
from ai.llm_client import LLMClient
from ai.memory_manager import MemoryManager
from ai.context_processor import ContextProcessor
from ai.prompt_integrator import PromptIntegrator
from ai.mcp_client import MCPClient
from ai.auto_chat import AutoChatModule

# 导入RAG相关模块
from RAG.rag_system import RagSystem

# 导入语音相关模块
from voice.tts_client import TTSClient
from voice.asr_client import ASRClient

# 导入视觉相关模块
from vision.vision_client import VisionClient

# 导入插件相关模块
from plugins.bilibili_listener import BiliBiliListener

logger = logging.getLogger("module_connector")

class ModuleConnector:
    """
    对各模块进行连接，增强模块的独立性及易修改性
    """

    def __init__(self, event_bus: 'EventBus', config_path: str="config.json"):
        """
        初始化模块连接器
        """
        # 保存配置路径
        self.config_path: str = config_path
        self.event_bus: 'EventBus' = event_bus
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            config_loader = ConfigLoader(self.config_path)
            self.config: Dict['str', Dict[str, str]] = config_loader.load()
            self.switch_config: Dict[str, str] = self.config.get("setting", {})
            logger.info("加载配置... [ 成功 ]")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise

    async def _init_llm_module(self) -> Tuple['LLMClient','ContextProcessor','PromptIntegrator']|Tuple[None, None, None]:
        """
        初始化LLM模块
        """
        # 创建LLM客户端
        if self.switch_config.get("llm_enabled", True):
            logger.info("LLM客户端... [ 已启用 ]")
            llm_client = LLMClient(self.config, self.event_bus)
            context_processor = ContextProcessor(self.config, self.event_bus)
            prompt_integrator = PromptIntegrator(self.config, self.event_bus)
            return llm_client, context_processor, prompt_integrator
        else:
            logger.warning("LLM客户端... [ 已停用 ]")
            return None, None, None

    async def _init_asr_module(self) -> 'ASRClient|None':
        """
        初始化ASR模块
        """
        # 创建ASR客户端
        if self.switch_config.get("asr_enabled", True):
            logger.info("ASR客户端... [ 已启用 ]")
            asr_client = ASRClient(self.config, self.event_bus)
            # 启动ASR客户端
            await asr_client.start()
            return asr_client
        else:
            logger.warning("ASR客户端... [ 已停用 ]")

    async def _init_tts_module(self) -> 'TTSClient|None':
        """
        初始化TTS模块
        """
        # 创建TTS客户端
        if self.switch_config.get("tts_enabled", True):
            logger.info("TTS客户端... [ 已启用 ]")
            tts_client = TTSClient(self.config, self.event_bus)
            # 启动TTS客户端
            await tts_client.start()
            # 播放欢迎语
            intro_text = self.config.get("ui", {}).get("intro_text", "你好，我是AI桌宠。")
            logger.info(f"- TTS播放欢迎语: {intro_text}")
            await tts_client.speak(intro_text)
            # 等待TTS播放完成
            while (await tts_client.is_active())[0]:
                await asyncio.sleep(0.1)
            return tts_client
        else:
            logger.warning("TTS客户端... [ 已停用 ]")

    async def _init_live2d_module(self) -> 'Live2DModel|None':
        """
        初始化Live2d模块
        """
        if self.switch_config.get("ui_enabled", True):
            logger.info("Live2D模型控制器... [ 已启用 ]")
            # 初始化Live2D引擎
            if not init_live2d():
                logger.error("初始化Live2D引擎... [ 失败 ]")
            # 创建Live2D模型
            live2d_model = Live2DModel(self.config, self.event_bus)
            # 显示Live2D模型
            live2d_model.show()
            return live2d_model
        else:
            logger.warning("Live2D模型控制器... [ 已停用 ]")

    async def _init_subtitle_module(self) -> 'SubtitleManager|None':
        """
        初始化字幕模块
        """
        # 创建字幕管理器
        if self.switch_config.get("subtitle_enabled", True):
            logger.info("字幕管理器... [ 已启用 ]")
            subtitle_manager = SubtitleManager(
                parent=None, 
                config=self.config, 
                event_bus=self.event_bus
            )
            return subtitle_manager
        else:
            logger.warning("字幕管理器... [ 已停用 ]")

    async def _init_user_input_module(self) -> 'UserInputWindow|None':
        """
        初始化用户输入框模块
        """
        # 创建用户输入框
        if self.switch_config.get("user_input_enabled", True):
            logger.info("用户输入框... [ 已启用 ]")
            user_input = UserInputWindow(config=self.config, event_bus=self.event_bus)
            # 创建用户输入框
            user_input.show()
            return user_input
        else:
            logger.warning("用户输入框... [ 已停用 ]")

    async def _init_rag_module(self) -> 'RagSystem|None':
        """
        初始化RAG系统
        """
        if self.switch_config.get("rag_enabled", False):
            rag_system = RagSystem(self.config, self.event_bus)
            logger.info("RAG系统... [ 已启用 ]")
            await rag_system.start()
            return rag_system
        else:
            logger.warning("RAG系统... [ 已停用 ]")  

    async def _init_mcp_module(self) -> 'MCPClient|None':
        """
        初始化MCP模块
        """
        if self.switch_config.get("mcp_enabled", False):
            mcp_client = MCPClient(self.config, event_bus=self.event_bus)
            logger.info("MCP客户端... [ 已启用 ]")
            await mcp_client.start()
            return mcp_client
        else:
            logger.warning("MCP客户端... [ 已停用 ]")   

    async def _init_memory_module(self) -> 'MemoryManager|None':
        """
        初始化记忆模块
        """
        # 创建记忆管理器
        if self.switch_config.get("memory_enabled", True):
            logger.info("记忆管理器... [ 已启用 ]")
            memory_manager = MemoryManager(self.config, self.event_bus)
            return memory_manager
        else:
            logger.warning("记忆管理器... [ 已停用 ]")

    async def _init_vision_module(self) -> 'VisionClient|None':
        """
        初始化视觉模块
        """
        # 创建视觉客户端
        if self.switch_config.get("vision_enabled", True):
            logger.info("视觉功能模块... [ 已启用 ]")
            vision_client = VisionClient(self.config, self.event_bus)
            return vision_client
        else:
            logger.warning("视觉功能模块... [ 已停用 ]")

    async def _init_auto_chat_module(self) -> 'AutoChatModule|None':
        """
        初始化主动对话模块
        """
        # 创建自动聊天模块
        if self.switch_config.get("auto_chat_enabled", True):
            logger.info("自动聊天模块... [ 已启用 ]")
            auto_chat = AutoChatModule(self.config, self.event_bus)
            # 启动自动聊天模块
            await auto_chat.start()
            return auto_chat
        else:
            logger.warning("自动聊天模块... [ 已停用 ]")

    async def _init_bilibili_listener_module(self) -> 'BiliBiliListener|None':
        """
        初始化B站直播监听器模块
        """
        # 创建B站直播监听器模块
        if self.switch_config.get("bilibili_enabled", False):
            logger.info("B站直播监听器... [ 已启用 ]")
            bilibili_listener = BiliBiliListener(self.config, self.event_bus)
            # 启动B站直播监听
            await bilibili_listener.start()
            return bilibili_listener
        else:
            logger.warning("B站直播监听器... [ 已停用 ]")