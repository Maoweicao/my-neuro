"""
核心模块 - 提供应用程序的核心功能和模块间通信
"""

from .app_manager import AppManager
from .event_bus import EventBus

__all__ = ['AppManager', 'EventBus']