# coding:utf-8
import json
import sys, os
import subprocess
import logging
import warnings
import asyncio
import uuid
import base64
import requests
import time
import random
import threading
import io
import wave
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from logging.handlers import RotatingFileHandler

# MCP相关导入
from mcp import ClientSession, stdio_client
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters
from contextlib import AsyncExitStack

# 消息队列导入
from utils.message_queue import send_message

# 抑制SIP相关的弃用警告，这是PyQt5版本兼容性问题
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*sipPyTypeDict.*")
from PyQt5.QtCore import Qt, QRect, QUrl, QEvent, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QIcon, QPainter, QImage, QBrush, QColor, QFont, QDesktopServices, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QStackedWidget,
    QHBoxLayout,
    QLabel,
    QSystemTrayIcon,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QWidget,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QLineEdit,
    QComboBox,
    QTabWidget,
    QSizePolicy,
    QMessageBox,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QColorDialog,
    QTextBrowser,
    QGridLayout,
    QSlider
)

from qfluentwidgets import (NavigationInterface,NavigationItemPosition, NavigationWidget, MessageBox,
                            isDarkTheme, setTheme, Theme, qrouter)
from qfluentwidgets import FluentIcon as FIF, Action, SystemTrayMenu, LineEdit, DoubleSpinBox, SpinBox, CheckBox, ScrollArea, PrimaryToolButton, ToolButton, InfoBar, InfoBarPosition, PasswordLineEdit, TextBrowser, PixmapLabel, PushButton, ColorDialog
from qframelesswindow import FramelessWindow, TitleBar

# 导入自定义界面模块
from interface.action_buttons import ActionButtonsWindow  # 已迁移到main.py


class QTextBrowserHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)  # 自定义信号

    def __init__(self, text_browser):
        super().__init__()
        QObject.__init__(self)
        self.text_browser = text_browser
        self.log_signal.connect(self.append_log)  # 连接信号到槽

    def emit(self, record):
        msg = self.format(record)
        # 根据日志级别添加HTML样式
        if record.levelno == logging.DEBUG:
            html_msg = f'<span style="color:cyan;">{msg}</span>'
        elif record.levelno == logging.INFO:
            html_msg = f'<span style="color:green;">{msg}</span>'
        elif record.levelno == logging.WARNING:
            html_msg = f'<span style="color:orange;font-weight:bold;">{msg}</span>'
        elif record.levelno >= logging.ERROR:
            html_msg = f'<span style="color:red;font-weight:bold;">{msg}</span>'
        else:
            html_msg = f'<span>{msg}</span>'
        
        self.log_signal.emit(html_msg)  # 发射信号

    def append_log(self, html):
        self.text_browser.append(html)  # 在主线程更新UI
        # 滚动到底部
        self.text_browser.verticalScrollBar().setValue(
            self.text_browser.verticalScrollBar().maximum()
        )


class WebAPIHandler(BaseHTTPRequestHandler):
    """WebAPI请求处理器"""
    
    def __init__(self, *args, ui_widget=None, **kwargs):
        self.ui_widget = ui_widget
        self._stop_singing = False  # 停止唱歌标志
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """处理POST请求"""
        import time
        start_time = time.time()
        client_ip = self.client_address[0] if hasattr(self, 'client_address') else 'unknown'
        
        # 记录请求开始
        if hasattr(self.ui_widget, 'webapi_logger'):
            self.ui_widget.webapi_logger.log_request_start('POST', self.path, client_ip)
        
        try:
            if self.path == '/api/chat':
                self._handle_chat_request()
            elif self.path == '/api/interrupt':
                self._handle_interrupt_request()
            elif self.path == '/api/dialogue':
                self._handle_dialogue_request()
            elif self.path == '/api/sing':
                self._handle_singing_request()
            elif self.path == '/api/lyrics':
                self._handle_lyrics_request()
            else:
                self._send_error_response(404, "Not Found")
        except Exception as e:
            # 记录错误
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error(self.path, "POST_ERROR", str(e))
            self._send_error_response(500, f"Internal Server Error: {str(e)}")
        finally:
            # 记录请求结束
            duration = (time.time() - start_time) * 1000  # 转换为毫秒
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_request_end('POST', self.path, 200, duration)
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/status':
            self._send_json_response({"status": "running", "message": "WebAPI服务正在运行"})
        else:
            self._send_error_response(404, "Not Found")
    
    def _handle_chat_request(self):
        """处理聊天请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Empty request body")
                return
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'message' not in data:
                self._send_error_response(400, "Missing 'message' field")
                return
            
            message = data['message'].strip()
            if not message:
                self._send_error_response(400, "Empty message")
                return
            
            # 获取可选的图片数据
            image_data = data.get('image_data', None)  # base64编码的图片数据
            
            # 验证API密钥（如果配置了）
            has_api_key = False
            if hasattr(self.ui_widget, 'config_data'):
                api_key = self.ui_widget.config_data.get('webapi', {}).get('api_key', '')
                if api_key and data.get('api_key') != api_key:
                    self._send_error_response(401, "Invalid API key")
                    return
                has_api_key = bool(data.get('api_key'))
            
            # 记录聊天请求
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_chat_request(len(message), has_api_key)
            
            # 记录请求（包含是否有图片的信息）
            if hasattr(self.ui_widget, 'log_user_input'):
                log_message = f"[WebAPI] {message}"
                if image_data:
                    log_message += " [包含图片]"
                self.ui_widget.log_user_input(log_message)
            
            # 调用LLM处理逻辑，传入图片数据
            import time
            chat_start_time = time.time()
            try:
                if hasattr(self.ui_widget, 'process_llm_request'):
                    response_text = self.ui_widget.process_llm_request(message, image_data=image_data)
                else:
                    response_text = f"收到您的消息: {message}"
            except Exception as e:
                response_text = f"处理错误: {str(e)}"
            
            chat_duration = (time.time() - chat_start_time) * 1000
            
            # 记录聊天响应
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_chat_response(len(response_text), chat_duration)
            
            # 记录响应
            if hasattr(self.ui_widget, 'log_llm_response'):
                self.ui_widget.log_llm_response(response_text)
            
            self._send_json_response({
                "response": response_text,
                "status": "success",
                "timestamp": time.time()
            })
            
        except json.JSONDecodeError:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/chat', "JSON_DECODE_ERROR", "Invalid JSON")
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/chat', "CHAT_PROCESSING_ERROR", str(e))
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _handle_interrupt_request(self):
        """处理打断请求"""
        try:
            # 验证API密钥（如果配置了）
            content_length = int(self.headers.get('Content-Length', 0))
            api_key = ""
            has_api_key = False
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                api_key = data.get('api_key', '')
                has_api_key = bool(api_key)
            
            if hasattr(self.ui_widget, 'config_data'):
                expected_api_key = self.ui_widget.config_data.get('webapi', {}).get('api_key', '')
                if expected_api_key and api_key != expected_api_key:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_error('/api/interrupt', "INVALID_API_KEY", "Invalid API key")
                    self._send_error_response(401, "Invalid API key")
                    return
            
            # 记录中断请求
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_interrupt_request(has_api_key)
                self.ui_widget.webapi_logger.log_system_event("收到中断请求")
            
            # 执行打断操作
            if hasattr(self.ui_widget, 'interrupt_current_operations'):
                # 通过消息队列发送中断请求
                interrupt_data = {
                    "action": "interrupt_all",
                    "timestamp": time.time(),
                    "source": "webapi"
                }
                
                # 发送中断消息到main.py
                interrupt_sent = self._send_message_queue_data('interrupt', interrupt_data, priority=1)
                
                # 同时执行本地中断操作
                local_success = self.ui_widget.interrupt_current_operations()
                
                # 同时停止唱歌
                self._stop_singing = True
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event("设置停止唱歌标志")
                
                success = interrupt_sent or local_success
                
                if success:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_interrupt_response(True)
                        self.ui_widget.webapi_logger.log_system_event("中断操作成功")
                    self._send_json_response({
                        "status": "success",
                        "message": "已打断当前AI输出、语音播放和唱歌",
                        "timestamp": time.time()
                    })
                else:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_interrupt_response(False)
                        self.ui_widget.webapi_logger.log_system_event("没有正在进行的操作需要打断")
                    self._send_json_response({
                        "status": "warning", 
                        "message": "没有正在进行的操作需要打断",
                        "timestamp": time.time()
                    })
            else:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/interrupt', "NOT_IMPLEMENTED", "Interrupt functionality not implemented")
                self._send_error_response(501, "Interrupt functionality not implemented")
                
        except json.JSONDecodeError:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/interrupt', "JSON_DECODE_ERROR", "Invalid JSON")
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/interrupt', "GENERAL_ERROR", str(e))
            self._send_error_response(500, f"Interrupt error: {str(e)}")
    
    def _handle_dialogue_request(self):
        """处理台词转换请求"""
        import time
        dialogue_start_time = time.time()
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/dialogue', "EMPTY_REQUEST", "Empty request body")
                self._send_error_response(400, "Empty request body")
                return
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'dialogue' not in data:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/dialogue', "MISSING_FIELD", "Missing 'dialogue' field")
                self._send_error_response(400, "Missing 'dialogue' field")
                return
            
            dialogue = data['dialogue'].strip()
            if not dialogue:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/dialogue', "EMPTY_DIALOGUE", "Empty dialogue")
                self._send_error_response(400, "Empty dialogue")
                return
            
            # 验证API密钥（如果配置了）
            has_api_key = False
            if hasattr(self.ui_widget, 'config_data'):
                api_key = self.ui_widget.config_data.get('webapi', {}).get('api_key', '')
                if api_key and data.get('api_key') != api_key:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_error('/api/dialogue', "INVALID_API_KEY", "Invalid API key")
                    self._send_error_response(401, "Invalid API key")
                    return
                has_api_key = bool(data.get('api_key'))
            
            # 记录台词转换请求
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_dialogue_request(len(dialogue), has_api_key)
                self.ui_widget.webapi_logger.log_system_event(f"开始处理台词转换: '{dialogue[:50]}...'")
            
            # 记录请求
            if hasattr(self.ui_widget, 'log_user_input'):
                self.ui_widget.log_user_input(f"[WebAPI Dialogue] {dialogue}")
            
            # 构建转换prompt
            conversion_prompt = f"""请将以下台词转换为适合AI角色表演的格式。
要求：
1. 保持原台词的核心内容
2. 添加适当的动作描述（如：*微笑地看着对方*）
3. 调整语气使其更生动自然
4. 可以添加表情或肢体语言描述
5. 格式为：动作描述 + 台词

原始台词：{dialogue}

请直接输出转换后的台词，不要添加其他解释。"""
            
            # 调用LLM处理逻辑
            dialogue_processing_start = time.time()
            try:
                if hasattr(self.ui_widget, 'process_llm_request'):
                    response_text = self.ui_widget.process_llm_request(conversion_prompt)
                else:
                    response_text = f"收到台词: {dialogue}"
            except Exception as e:
                response_text = f"处理错误: {str(e)}"
            
            dialogue_processing_duration = (time.time() - dialogue_processing_start) * 1000
            
            # 记录台词转换响应
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_dialogue_response(
                    len(dialogue), len(response_text), dialogue_processing_duration
                )
                self.ui_widget.webapi_logger.log_system_event(f"台词转换完成: '{response_text[:50]}...'")
            
            # 记录响应
            if hasattr(self.ui_widget, 'log_llm_response'):
                self.ui_widget.log_llm_response(response_text)
            
            total_duration = (time.time() - dialogue_start_time) * 1000
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"台词转换请求处理完成，总耗时: {total_duration:.2f}ms")
            
            # 检查字幕是否启用，如果启用则显示台词
            if hasattr(self.ui_widget, 'config_data'):
                subtitle_enabled = self.ui_widget.config_data.get('setting', {}).get('subtitle_enabled', False)
                if subtitle_enabled and response_text:
                    subtitle_data = {
                        "text": response_text,
                        "source": "dialogue",
                        "timestamp": time.time()
                    }
                    
                    # 使用消息队列发送函数
                    if self._send_message_queue_data('show_subtitle', subtitle_data, priority=1):
                        if hasattr(self.ui_widget, 'webapi_logger'):
                            self.ui_widget.webapi_logger.log_system_event("✓ 已发送台词字幕显示请求")
                    else:
                        if hasattr(self.ui_widget, 'webapi_logger'):
                            self.ui_widget.webapi_logger.log_system_event("⚠ 发送台词字幕显示请求失败")
            
            self._send_json_response({
                "original_dialogue": dialogue,
                "converted_dialogue": response_text,
                "status": "success",
                "timestamp": time.time()
            })
            
        except json.JSONDecodeError:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/dialogue', "JSON_DECODE_ERROR", "Invalid JSON")
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/dialogue', "GENERAL_ERROR", str(e))
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _handle_singing_request(self):
        """处理唱歌请求"""
        import time
        singing_start_time = time.time()
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/sing', "EMPTY_REQUEST", "Empty request body")
                self._send_error_response(400, "Empty request body")
                return
            
            # 记录请求开始
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("开始处理唱歌请求")
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'audio_base64' not in data:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/sing', "MISSING_FIELD", "Missing 'audio_base64' field")
                self._send_error_response(400, "Missing 'audio_base64' field")
                return
            
            audio_base64 = data['audio_base64'].strip()
            if not audio_base64:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/sing', "EMPTY_AUDIO", "Empty audio_base64")
                self._send_error_response(400, "Empty audio_base64")
                return
            
            # 验证API密钥（如果配置了）
            has_api_key = False
            if hasattr(self.ui_widget, 'config_data'):
                api_key = self.ui_widget.config_data.get('webapi', {}).get('api_key', '')
                if api_key and data.get('api_key') != api_key:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_error('/api/sing', "INVALID_API_KEY", "Invalid API key")
                    self._send_error_response(401, "Invalid API key")
                    return
                has_api_key = bool(data.get('api_key'))
            
            # 解析参数
            volume = float(data.get('volume', 1.0))
            loop = bool(data.get('loop', False))
            singing_motion = data.get('singing_motion', '唱歌')
            
            # 记录唱歌请求开始
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_singing_request_start(
                    len(audio_base64), volume, loop, singing_motion
                )
                self.ui_widget.webapi_logger.log_system_event(f"唱歌参数: 音量={volume}, 循环={loop}, 动作={singing_motion}")
            
            # 记录请求
            if hasattr(self.ui_widget, 'log_user_input'):
                self.ui_widget.log_user_input(f"[WebAPI Singing] Audio length: {len(audio_base64)} chars, Volume: {volume}, Loop: {loop}")
            
            # 启动唱歌处理
            try:
                success = self._process_singing_request(audio_base64, volume, loop, singing_motion)
                if success:
                    singing_duration = (time.time() - singing_start_time) * 1000
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_singing_request_complete(singing_duration)
                        self.ui_widget.webapi_logger.log_system_event("唱歌请求处理成功")
                    
                    self._send_json_response({
                        "status": "success",
                        "message": "唱歌请求已开始处理",
                        "volume": volume,
                        "loop": loop,
                        "singing_motion": singing_motion,
                        "timestamp": time.time()
                    })
                else:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_error('/api/sing', "PROCESSING_FAILED", "Failed to process singing request")
                    self._send_error_response(500, "Failed to process singing request")
            except Exception as e:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/sing', "PROCESSING_EXCEPTION", str(e))
                self._send_error_response(500, f"Singing processing error: {str(e)}")
                
        except json.JSONDecodeError:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/sing', "JSON_DECODE_ERROR", "Invalid JSON")
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/sing', "GENERAL_ERROR", str(e))
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _send_message_queue_data(self, message_type, data, priority=1):
        """通过消息队列发送数据到main.py
        
        Args:
            message_type: 消息类型 (interrupt, play_audio, show_subtitle等)
            data: 要发送的数据字典
            priority: 优先级 (1=高, 2=中, 3=低)
            
        Returns:
            bool: 发送是否成功
        """
        try:
            success = send_message(message_type, data, priority)
            
            if success:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event(f"✓ 消息队列发送成功: {message_type}")
            else:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event(f"⚠ 消息队列发送失败: {message_type}")
            
            return success
            
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"⚠ 消息队列发送异常: {str(e)}")
            return False

    def _process_singing_request(self, audio_base64, volume, loop, singing_motion):
        """处理唱歌请求的具体逻辑"""
        try:
            import base64
            
            # 记录开始解码音频
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("开始解码base64音频数据")
            
            # 重置停止标志
            self._stop_singing = False
            
            # 解码base64音频数据
            audio_data = base64.b64decode(audio_base64)
            
            # 记录解码成功
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_singing_audio_decode(True, len(audio_data)/44100 if len(audio_data) > 0 else 0)
                self.ui_widget.webapi_logger.log_system_event(f"音频解码成功，大小: {len(audio_data)} bytes")
            
            # 通过消息队列发送音频播放请求给main.py（音频格式转换由main.py处理）
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("通过消息队列发送音频播放请求给main.py")
            
            # 检查字幕是否启用，如果启用则获取LRC歌词
            lrc_content = ""
            if hasattr(self.ui_widget, 'config_data'):
                subtitle_enabled = self.ui_widget.config_data.get('setting', {}).get('subtitle_enabled', False)
                if subtitle_enabled:
                    # 获取LRC歌词文件内容
                    lrc_content = self._get_lrc_lyrics(audio_base64)
                    
                    # 如果没有LRC歌词，显示默认字幕
                    if not lrc_content:
                        subtitle_text = "♪ 唱歌中 ♫"
                        subtitle_data = {
                            "text": subtitle_text,
                            "source": "singing",
                            "timestamp": time.time()
                        }
                        
                        # 使用消息队列发送函数
                        if self._send_message_queue_data('show_subtitle', subtitle_data, priority=1):
                            if hasattr(self.ui_widget, 'webapi_logger'):
                                self.ui_widget.webapi_logger.log_system_event("✓ 已发送唱歌字幕显示请求")
                        else:
                            if hasattr(self.ui_widget, 'webapi_logger'):
                                self.ui_widget.webapi_logger.log_system_event("⚠ 发送唱歌字幕显示请求失败")
            
            # 通过消息队列发送音频播放请求给main.py
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("通过消息队列发送音频播放请求给main.py")
            
            # 将音频数据编码为base64
            audio_data_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            play_audio_data = {
                "audio_data": audio_data_b64,
                "volume": volume,
                "loop": loop,
                "singing_motion": singing_motion,
                "lrc_content": lrc_content,  # 添加LRC歌词内容
                "timestamp": time.time(),
                "source": "ui_singing"
            }
            
            # 使用消息队列发送函数
            if self._send_message_queue_data('play_audio', play_audio_data, priority=1):
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event("✓ 已通过消息队列发送音频播放请求")
            else:
                # 消息队列发送失败，回退到本地播放
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/sing', "MESSAGE_QUEUE_ERROR", "消息队列发送失败")
                    self.ui_widget.webapi_logger.log_system_event("⚠ 消息队列通信失败，回退到本地播放")
                
                # 回退到本地播放（如果main.py不可用）
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event("回退：创建后台线程处理唱歌")
                import threading
                singing_thread = threading.Thread(
                    target=self._play_audio_fallback,
                    args=(audio_data, volume, loop, singing_motion)
                )
                singing_thread.daemon = True
                singing_thread.start()
            
            return True
        except Exception as e:
            # 记录解码失败
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_singing_audio_decode(False)
                self.ui_widget.webapi_logger.log_error('/api/sing', "AUDIO_DECODE_ERROR", str(e))
            print(f"处理唱歌请求失败: {e}")
            return False
    
    
    def _get_lrc_lyrics(self, audio_base64):
        """获取LRC歌词文件内容
        
        Args:
            audio_base64: 音频数据的base64编码（用于生成文件名）
            
        Returns:
            str: 歌词内容，如果没有找到lrc文件则返回空字符串
        """
        try:
            import os
            import hashlib
            
            # 生成音频文件的哈希值作为文件名基础
            audio_hash = hashlib.md5(audio_base64.encode()).hexdigest()[:8]
            
            # 获取当前工作目录作为基础路径
            base_dir = os.getcwd()
            
            # 可能的lrc文件路径（使用绝对路径）
            possible_lrc_paths = [
                os.path.join(base_dir, "lyrics", f"{audio_hash}.lrc"),
                os.path.join(base_dir, "lyrics", f"audio_{audio_hash}.lrc"),
                os.path.join(base_dir, "lrc", f"{audio_hash}.lrc"),
                os.path.join(base_dir, "lrc", f"audio_{audio_hash}.lrc"),
                os.path.join(base_dir, f"{audio_hash}.lrc"),
                os.path.join(base_dir, f"audio_{audio_hash}.lrc"),
                # 也检查相对路径，以防万一
                f"lyrics/{audio_hash}.lrc",
                f"lyrics/audio_{audio_hash}.lrc",
                f"lrc/{audio_hash}.lrc",
                f"lrc/audio_{audio_hash}.lrc",
                f"{audio_hash}.lrc",
                f"audio_{audio_hash}.lrc"
            ]
            
            # 记录搜索过程
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"搜索LRC歌词文件，音频哈希: {audio_hash}")
            
            for lrc_path in possible_lrc_paths:
                try:
                    # 标准化路径
                    normalized_path = os.path.normpath(lrc_path)
                    
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_system_event(f"检查路径: {normalized_path}")
                    
                    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
                        try:
                            # 尝试使用UTF-8编码读取
                            with open(normalized_path, 'r', encoding='utf-8') as f:
                                lyrics_content = f.read().strip()
                                
                            if lyrics_content:
                                if hasattr(self.ui_widget, 'webapi_logger'):
                                    self.ui_widget.webapi_logger.log_system_event(f"✓ 找到LRC歌词文件: {normalized_path}")
                                return lyrics_content
                                
                        except UnicodeDecodeError:
                            # 如果UTF-8失败，尝试GBK编码
                            try:
                                with open(normalized_path, 'r', encoding='gbk') as f:
                                    lyrics_content = f.read().strip()
                                    
                                if lyrics_content:
                                    if hasattr(self.ui_widget, 'webapi_logger'):
                                        self.ui_widget.webapi_logger.log_system_event(f"✓ 找到LRC歌词文件(GBK编码): {normalized_path}")
                                    return lyrics_content
                            except Exception as gbk_e:
                                if hasattr(self.ui_widget, 'webapi_logger'):
                                    self.ui_widget.webapi_logger.log_system_event(f"⚠ 读取LRC文件失败(GBK编码) {normalized_path}: {gbk_e}")
                                    
                        except Exception as e:
                            if hasattr(self.ui_widget, 'webapi_logger'):
                                self.ui_widget.webapi_logger.log_system_event(f"⚠ 读取LRC文件失败 {normalized_path}: {e}")
                            continue
                            
                except Exception as path_e:
                    # 路径处理失败
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_system_event(f"⚠ 路径处理失败 {lrc_path}: {path_e}")
                    continue
            
            # 如果没有找到lrc文件，返回空字符串
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("⚠ 未找到对应的LRC歌词文件")
            return ""
            
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"⚠ 获取LRC歌词失败: {e}")
            return ""
    
    
    # 音频格式转换方法已迁移到main.py中的PetService类
    
    # 音频播放方法已迁移到main.py中的PetService类
    
    def _play_audio_fallback(self, audio_data, volume, loop, singing_motion):
        """音频播放的回退方法 - 使用专用线程避免阻塞UI"""
        try:
            # 创建音频播放线程
            self.audio_thread = AudioPlaybackThread(audio_data, volume, loop, singing_motion, self.ui_widget)
            
            # 连接信号
            self.audio_thread.finished.connect(self._on_audio_finished)
            self.audio_thread.error.connect(self._on_audio_error)
            self.audio_thread.trigger_motion.connect(self._on_trigger_motion)
            
            # 启动线程
            self.audio_thread.start()
            
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("开始音频播放回退")
                
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"音频播放回退启动失败: {e}")
            print(f"音频播放回退启动失败: {e}")
    
    def _on_trigger_motion(self, motion_index):
        """处理Live2D动作触发信号"""
        try:
            if hasattr(self.ui_widget, 'trigger_live2d_motion'):
                self.ui_widget.trigger_live2d_motion(motion_index)
        except Exception as e:
            print(f"触发Live2D动作异常: {e}")
    
    def _on_audio_finished(self):
        """音频播放完成回调"""
        if hasattr(self.ui_widget, 'webapi_logger'):
            self.ui_widget.webapi_logger.log_system_event("音频播放完成")
        
        # 清理线程引用
        if hasattr(self, 'audio_thread'):
            self.audio_thread = None
    
    def _on_audio_error(self, error_msg):
        """音频播放错误回调"""
        if hasattr(self.ui_widget, 'webapi_logger'):
            self.ui_widget.webapi_logger.log_system_event(f"音频播放错误: {error_msg}")
        print(f"音频播放错误: {error_msg}")
        
        # 清理线程引用
        if hasattr(self, 'audio_thread'):
            self.audio_thread = None
    
    def stop_audio_playback(self):
        """停止当前音频播放"""
        if hasattr(self, 'audio_thread') and self.audio_thread is not None:
            try:
                # 先设置停止标志
                self.audio_thread.stop()
                
                # 在Windows上，尝试停止音频播放
                if sys.platform == 'win32':
                    try:
                        import winsound
                        winsound.PlaySound(None, winsound.SND_PURGE)  # 停止所有音频播放
                    except:
                        pass
                
                # 等待线程结束
                self.audio_thread.wait(3000)  # 等待最多3秒
                
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event("✓ 音频播放已停止")
                    
            except Exception as e:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event(f"⚠ 停止音频播放异常: {e}")
                print(f"停止音频播放异常: {e}")
            finally:
                self.audio_thread = None
                
            # 确保Live2D动作停止
            if hasattr(self.ui_widget, 'trigger_live2d_motion'):
                self.ui_widget.trigger_live2d_motion(7)
    
    
    def _handle_lyrics_request(self):
        """处理歌词请求"""
        import time
        lyrics_start_time = time.time()
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/lyrics', "EMPTY_REQUEST", "Empty request body")
                self._send_error_response(400, "Empty request body")
                return
            
            # 记录请求开始
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event("开始处理歌词请求")
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'audio_base64' not in data:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/lyrics', "MISSING_FIELD", "Missing 'audio_base64' field")
                self._send_error_response(400, "Missing 'audio_base64' field")
                return
            
            audio_base64 = data['audio_base64'].strip()
            if not audio_base64:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/lyrics', "EMPTY_AUDIO", "Empty audio_base64")
                self._send_error_response(400, "Empty audio_base64")
                return
            
            # 验证API密钥（如果配置了）
            has_api_key = False
            if hasattr(self.ui_widget, 'config_data'):
                api_key = self.ui_widget.config_data.get('webapi', {}).get('api_key', '')
                if api_key and data.get('api_key') != api_key:
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_error('/api/lyrics', "INVALID_API_KEY", "Invalid API key")
                    self._send_error_response(401, "Invalid API key")
                    return
                has_api_key = bool(data.get('api_key'))
            
            # 获取歌词
            try:
                lrc_text = self._get_lrc_lyrics(audio_base64)
                
                lyrics_duration = (time.time() - lyrics_start_time) * 1000
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_system_event(f"歌词请求处理完成，耗时: {lyrics_duration:.2f}ms")
                
                if lrc_text:
                    # 注释掉歌词请求时的字幕显示，歌词应该只在播放时按时间同步显示
                    # # 发送歌词字幕显示请求
                    # if hasattr(self.ui_widget, 'config_data'):
                    #     subtitle_enabled = self.ui_widget.config_data.get('setting', {}).get('subtitle_enabled', False)
                    #     if subtitle_enabled:
                    #         subtitle_data = {
                    #             "text": lrc_text,
                    #             "source": "lyrics",
                    #             "timestamp": time.time()
                    #         }
                    #         
                    #         # 使用消息队列发送函数
                    #         if self._send_message_queue_data('show_subtitle', subtitle_data, priority=1):
                    #             if hasattr(self.ui_widget, 'webapi_logger'):
                    #                 self.ui_widget.webapi_logger.log_system_event("✓ 已发送歌词字幕显示请求")
                    #         else:
                    #             if hasattr(self.ui_widget, 'webapi_logger'):
                    #                 self.ui_widget.webapi_logger.log_system_event("⚠ 发送歌词字幕显示请求失败")
                    
                    if hasattr(self.ui_widget, 'webapi_logger'):
                        self.ui_widget.webapi_logger.log_system_event("✓ 歌词内容已准备，将在播放时按时间同步显示")
                    
                    self._send_json_response({
                        "lyrics": lrc_text,
                        "status": "success",
                        "found": True,
                        "timestamp": time.time()
                    })
                else:
                    self._send_json_response({
                        "lyrics": "",
                        "status": "success",
                        "found": False,
                        "message": "未找到对应的LRC歌词文件",
                        "timestamp": time.time()
                    })
                    
            except Exception as e:
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('/api/lyrics', "LYRICS_PROCESSING_ERROR", str(e))
                self._send_error_response(500, f"歌词处理错误: {str(e)}")
                
        except json.JSONDecodeError:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/lyrics', "JSON_DECODE_ERROR", "Invalid JSON")
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('/api/lyrics', "GENERAL_ERROR", str(e))
            self._send_error_response(500, f"Server error: {str(e)}")

    # 动作索引获取方法已迁移到main.py中的PetService类
    
    def _send_json_response(self, data):
        """发送JSON响应"""
        response_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_error_response(self, code, message):
        """发送错误响应"""
        error_data = {
            "error": message,
            "status": "error",
            "code": code
        }
        response_data = json.dumps(error_data, ensure_ascii=False, indent=2)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """重写日志方法，避免控制台输出"""
        pass


class WebAPIServer(QThread):
    """WebAPI服务器线程"""
    
    status_changed = pyqtSignal(bool, str)  # 状态变化信号 (is_running, message)
    
    def __init__(self, host='127.0.0.1', port=8888, ui_widget=None):
        super().__init__()
        self.host = host
        self.port = port
        self.ui_widget = ui_widget
        self.server = None
        self.is_running = False
    
    def run(self):
        """启动服务器"""
        try:
            # 创建处理器类，传入UI widget引用
            handler_class = lambda *args, **kwargs: WebAPIHandler(*args, ui_widget=self.ui_widget, **kwargs)
            
            self.server = HTTPServer((self.host, self.port), handler_class)
            self.is_running = True
            self.status_changed.emit(True, f"WebAPI服务已启动 - {self.host}:{self.port}")
            
            # 记录服务器启动
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_system_event(f"WebAPI服务器启动成功: {self.host}:{self.port}")
            
            # 启动服务器
            self.server.serve_forever()
            
        except OSError as e:
            if "Address already in use" in str(e):
                self.status_changed.emit(False, f"端口 {self.port} 已被占用")
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('WebAPIServer', "PORT_IN_USE", f"端口 {self.port} 已被占用")
            else:
                self.status_changed.emit(False, f"启动失败: {str(e)}")
                if hasattr(self.ui_widget, 'webapi_logger'):
                    self.ui_widget.webapi_logger.log_error('WebAPIServer', "STARTUP_ERROR", str(e))
        except Exception as e:
            self.status_changed.emit(False, f"服务器错误: {str(e)}")
            if hasattr(self.ui_widget, 'webapi_logger'):
                self.ui_widget.webapi_logger.log_error('WebAPIServer', "SERVER_ERROR", str(e))
        finally:
            self.is_running = False
    
    def stop_server(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        
        self.is_running = False
        self.status_changed.emit(False, "WebAPI服务已停止")
        
        # 记录服务器停止
        if hasattr(self.ui_widget, 'webapi_logger'):
            self.ui_widget.webapi_logger.log_system_event("WebAPI服务器已停止")
        
        self.quit()
        self.wait()


class LLMInteractionLogger:
    """LLM交互日志记录器"""
    
    def __init__(self, log_path="logs/llm_interactions.log", enabled=True):
        self.log_path = log_path
        self.enabled = enabled
        self.logger = None
        self.setup_logger()
    
    def setup_logger(self):
        """设置日志记录器"""
        if not self.enabled:
            return
            
        # 确保日志目录存在
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建专用的LLM交互日志记录器
        self.logger = logging.getLogger('llm_interactions')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器，支持日志轮转
            file_handler = RotatingFileHandler(
                self.log_path, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_user_input(self, user_input):
        """记录用户输入"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"USER: {user_input}")
    
    def log_llm_response(self, response, model="", api_type=""):
        """记录LLM响应"""
        if not self.enabled or not self.logger:
            return
        model_info = f"[{api_type}:{model}]" if model and api_type else ""
        self.logger.info(f"LLM{model_info}: {response}")
    
    def log_api_request(self, api_url, model, prompt_tokens=0):
        """记录API请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"API_REQUEST: URL={api_url}, Model={model}, Tokens={prompt_tokens}")
    
    def log_api_response(self, status_code, response_tokens=0, error=None):
        """记录API响应"""
        if not self.enabled or not self.logger:
            return
        if error:
            self.logger.error(f"API_ERROR: Status={status_code}, Error={error}")
        else:
            self.logger.info(f"API_RESPONSE: Status={status_code}, Tokens={response_tokens}")
    
    def log_system_event(self, event):
        """记录系统事件"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SYSTEM: {event}")
    
    def update_config(self, log_path=None, enabled=None):
        """更新日志配置"""
        if log_path is not None:
            self.log_path = log_path
        if enabled is not None:
            self.enabled = enabled
        
        # 重新设置日志记录器
        if self.logger:
            # 清除现有处理器
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            self.logger = None
        
        self.setup_logger()


class ASRInteractionLogger:
    """ASR交互日志记录器"""
    
    def __init__(self, log_path="logs/asr_interactions.log", enabled=True):
        self.log_path = log_path
        self.enabled = enabled
        self.logger = None
        self.setup_logger()
    
    def setup_logger(self):
        """设置日志记录器"""
        if not self.enabled:
            return
            
        # 确保日志目录存在
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建专用的ASR交互日志记录器
        self.logger = logging.getLogger('asr_interactions')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器，支持日志轮转
            file_handler = RotatingFileHandler(
                self.log_path, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_audio_input(self, audio_info):
        """记录音频输入"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"AUDIO_INPUT: {audio_info}")
    
    def log_recognition_result(self, result, confidence=0, asr_type=""):
        """记录识别结果"""
        if not self.enabled or not self.logger:
            return
        type_info = f"[{asr_type}]" if asr_type else ""
        confidence_info = f"(置信度:{confidence:.2f})" if confidence > 0 else ""
        self.logger.info(f"ASR_RESULT{type_info}: {result} {confidence_info}")
    
    def log_websocket_connection(self, url, status):
        """记录WebSocket连接状态"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"WEBSOCKET_CONNECTION: URL={url}, Status={status}")
    
    def log_doubao_request(self, mode, packet_size, connect_id):
        """记录豆包ASR请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"DOUBAO_REQUEST: Mode={mode}, PacketSize={packet_size}ms, ConnectId={connect_id}")
    
    def log_doubao_response(self, logid, result, is_final=False):
        """记录豆包ASR响应"""
        if not self.enabled or not self.logger:
            return
        final_flag = "[FINAL]" if is_final else "[PARTIAL]"
        self.logger.info(f"DOUBAO_RESPONSE{final_flag}: LogId={logid}, Result={result}")
    
    def log_error(self, error_type, error_message):
        """记录错误信息"""
        if not self.enabled or not self.logger:
            return
        self.logger.error(f"ASR_ERROR: Type={error_type}, Message={error_message}")
    
    def log_system_event(self, event):
        """记录系统事件"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SYSTEM: {event}")
    
    def update_config(self, log_path=None, enabled=None):
        """更新日志配置"""
        if log_path is not None:
            self.log_path = log_path
        if enabled is not None:
            self.enabled = enabled
        
        # 重新设置日志记录器
        if self.logger:
            # 清除现有处理器
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            self.logger = None
        
        self.setup_logger()


class ColorPickerWidget(QWidget):
    """颜色选择器组件，使用qfluentwidgets的ColorDialog"""
    
    def __init__(self, parent=None, label="颜色", has_alpha=True):
        super().__init__(parent)
        self.has_alpha = has_alpha
        self.r = 0
        self.g = 0
        self.b = 0
        self.a = 255
        self.setup_ui(label)
    
    def setup_ui(self, label):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用qfluentwidgets的PushButton作为颜色选择按钮
        self.color_btn = PushButton("选择颜色", self)
        self.color_btn.setFixedSize(100, 32)
        self.color_btn.clicked.connect(self.select_color)
        self.update_color_display()
        
        # 数值显示和输入
        self.r_spin = SpinBox()
        self.g_spin = SpinBox()
        self.b_spin = SpinBox()
        
        for spin in [self.r_spin, self.g_spin, self.b_spin]:
            spin.setRange(0, 255)
            spin.setFixedWidth(60)
            spin.valueChanged.connect(self.on_spin_changed)
        
        if self.has_alpha:
            self.a_spin = SpinBox()
            self.a_spin.setRange(0, 255)
            self.a_spin.setFixedWidth(60)
            self.a_spin.valueChanged.connect(self.on_spin_changed)
        
        # 布局
        layout.addWidget(self.color_btn)
        layout.addWidget(QLabel("R:"))
        layout.addWidget(self.r_spin)
        layout.addWidget(QLabel("G:"))
        layout.addWidget(self.g_spin)
        layout.addWidget(QLabel("B:"))
        layout.addWidget(self.b_spin)
        
        if self.has_alpha:
            layout.addWidget(QLabel("A:"))
            layout.addWidget(self.a_spin)
        
        layout.addStretch()
    
    def select_color(self):
        """使用qfluentwidgets的ColorDialog选择颜色"""
        try:
            current_color = QColor(self.r, self.g, self.b, self.a if self.has_alpha else 255)
            
            # 获取顶级窗口作为父控件，避免对话框被限制在小控件内
            parent_window = self.window()  # 获取顶级窗口
            
            # 创建ColorDialog
            color_dialog = ColorDialog(
                current_color, 
                "选择颜色", 
                parent_window,  # 使用顶级窗口作为父控件
                enableAlpha=self.has_alpha
            )
            
            # 连接颜色改变信号（实时预览）
            def on_color_changed(color):
                # 实时更新颜色预览
                self.set_color(color.red(), color.green(), color.blue(), 
                              color.alpha() if self.has_alpha else self.a)
            
            color_dialog.colorChanged.connect(on_color_changed)
            
            # 显示对话框
            result = color_dialog.exec_()
            if result:
                # 用户确认了颜色选择
                final_color = color_dialog.color
                self.set_color(final_color.red(), final_color.green(), final_color.blue(),
                              final_color.alpha() if self.has_alpha else self.a)
            else:
                # 用户取消，恢复原来的颜色
                self.set_color(current_color.red(), current_color.green(), current_color.blue(),
                              current_color.alpha() if self.has_alpha else current_color.alpha())
                
        except Exception as e:
            print(f"ColorDialog错误: {e}")
            # 如果ColorDialog失败，回退到标准QColorDialog
            from PyQt5.QtWidgets import QColorDialog as QtColorDialog
            color = QtColorDialog.getColor(current_color, self.window(), "选择颜色")
            if color.isValid():
                self.set_color(color.red(), color.green(), color.blue(), 
                              color.alpha() if self.has_alpha else self.a)
    
    def set_color(self, r, g, b, a=255):
        """设置颜色值"""
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        
        # 更新SpinBox（阻止信号避免循环）
        self.r_spin.blockSignals(True)
        self.g_spin.blockSignals(True)
        self.b_spin.blockSignals(True)
        
        self.r_spin.setValue(r)
        self.g_spin.setValue(g)
        self.b_spin.setValue(b)
        
        if self.has_alpha:
            self.a_spin.blockSignals(True)
            self.a_spin.setValue(a)
            self.a_spin.blockSignals(False)
        
        self.r_spin.blockSignals(False)
        self.g_spin.blockSignals(False)
        self.b_spin.blockSignals(False)
        
        self.update_color_display()
    
    def on_spin_changed(self):
        """SpinBox值改变时更新颜色"""
        self.r = self.r_spin.value()
        self.g = self.g_spin.value()
        self.b = self.b_spin.value()
        
        if self.has_alpha:
            self.a = self.a_spin.value()
        
        self.update_color_display()
    
    def update_color_display(self):
        """更新颜色按钮的显示"""
        # 使用qfluentwidgets的PushButton样式，但添加背景颜色
        if self.has_alpha:
            # 对于有透明度的颜色，显示RGBA值
            self.color_btn.setStyleSheet(f"""
                PushButton {{
                    background-color: rgba({self.r}, {self.g}, {self.b}, {self.a / 255.0});
                    border: 2px solid rgba(136, 136, 136, 0.5);
                    border-radius: 6px;
                    color: {"white" if (self.r + self.g + self.b) < 384 else "black"};
                    font-weight: bold;
                }}
                PushButton:hover {{
                    border: 2px solid rgb(0, 120, 215);
                }}
                PushButton:pressed {{
                    background-color: rgba({max(0, self.r-20)}, {max(0, self.g-20)}, {max(0, self.b-20)}, {self.a / 255.0});
                }}
            """)
            self.color_btn.setText(f"RGBA({self.r},{self.g},{self.b},{self.a})")
        else:
            self.color_btn.setStyleSheet(f"""
                PushButton {{
                    background-color: rgb({self.r}, {self.g}, {self.b});
                    border: 2px solid rgba(136, 136, 136, 0.5);
                    border-radius: 6px;
                    color: {"white" if (self.r + self.g + self.b) < 384 else "black"};
                    font-weight: bold;
                }}
                PushButton:hover {{
                    border: 2px solid rgb(0, 120, 215);
                }}
                PushButton:pressed {{
                    background-color: rgb({max(0, self.r-20)}, {max(0, self.g-20)}, {max(0, self.b-20)});
                }}
            """)
            self.color_btn.setText(f"RGB({self.r},{self.g},{self.b})")
    
    def get_rgba(self):
        """获取RGBA值"""
        return self.r, self.g, self.b, self.a
    
    def get_rgb(self):
        """获取RGB值"""
        return self.r, self.g, self.b


class TTSInteractionLogger:
    """TTS交互日志记录器"""
    
    def __init__(self, log_path="logs/tts_interactions.log", enabled=True):
        self.log_path = log_path
        self.enabled = enabled
        self.logger = None
        self.setup_logger()
    
    def setup_logger(self):
        """设置日志记录器"""
        if not self.enabled:
            return
            
        # 确保日志目录存在
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建专用的TTS交互日志记录器
        self.logger = logging.getLogger('tts_interactions')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器，支持日志轮转
            file_handler = RotatingFileHandler(
                self.log_path, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_text_input(self, text, tts_type=""):
        """记录文本输入"""
        if not self.enabled or not self.logger:
            return
        type_info = f"[{tts_type}]" if tts_type else ""
        self.logger.info(f"TEXT_INPUT{type_info}: {text}")
    
    def log_synthesis_request(self, text, voice_type="", parameters=None):
        """记录合成请求"""
        if not self.enabled or not self.logger:
            return
        voice_info = f"Voice={voice_type}" if voice_type else ""
        param_info = f"Params={parameters}" if parameters else ""
        info_parts = [part for part in [voice_info, param_info] if part]
        info_str = f"({', '.join(info_parts)})" if info_parts else ""
        self.logger.info(f"SYNTHESIS_REQUEST: Text='{text}' {info_str}")
    
    def log_synthesis_result(self, status, audio_length=0, tts_type=""):
        """记录合成结果"""
        if not self.enabled or not self.logger:
            return
        type_info = f"[{tts_type}]" if tts_type else ""
        length_info = f"AudioLength={audio_length}bytes" if audio_length > 0 else ""
        self.logger.info(f"SYNTHESIS_RESULT{type_info}: Status={status} {length_info}")
    
    def log_websocket_connection(self, url, status):
        """记录WebSocket连接状态"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"WEBSOCKET_CONNECTION: URL={url}, Status={status}")
    
    def log_doubao_request(self, appid, voice_type, encoding, text):
        """记录豆包TTS请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"DOUBAO_REQUEST: AppId={appid}, Voice={voice_type}, Encoding={encoding}, Text='{text}'")
    
    def log_doubao_response(self, logid, audio_size, is_final=False):
        """记录豆包TTS响应"""
        if not self.enabled or not self.logger:
            return
        final_flag = "[FINAL]" if is_final else "[CHUNK]"
        self.logger.info(f"DOUBAO_RESPONSE{final_flag}: LogId={logid}, AudioSize={audio_size}bytes")
    
    def log_fish_audio_request(self, reference_id, text, backend="", temperature=0, top_p=0):
        """记录Fish Audio TTS请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"FISH_AUDIO_REQUEST: ReferenceId={reference_id}, Text='{text}', Backend={backend}, Temperature={temperature}, TopP={top_p}")
    
    def log_fish_audio_response(self, status, audio_size):
        """记录Fish Audio TTS响应"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"FISH_AUDIO_RESPONSE: Status={status}, AudioSize={audio_size}bytes")
    
    def log_local_tts_request(self, text, voice_model=""):
        """记录本地TTS请求"""
        if not self.enabled or not self.logger:
            return
        model_info = f"Model={voice_model}" if voice_model else ""
        self.logger.info(f"LOCAL_TTS_REQUEST: Text='{text}' {model_info}")
    
    def log_local_tts_response(self, status, audio_file=""):
        """记录本地TTS响应"""
        if not self.enabled or not self.logger:
            return
        file_info = f"OutputFile={audio_file}" if audio_file else ""
        self.logger.info(f"LOCAL_TTS_RESPONSE: Status={status} {file_info}")
    
    def log_error(self, error_type, error_message):
        """记录错误信息"""
        if not self.enabled or not self.logger:
            return
        self.logger.error(f"TTS_ERROR: Type={error_type}, Message={error_message}")
    
    def log_system_event(self, event):
        """记录系统事件"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SYSTEM: {event}")
    
    def update_config(self, log_path=None, enabled=None):
        """更新日志配置"""
        if log_path is not None:
            self.log_path = log_path
        if enabled is not None:
            self.enabled = enabled
        
        # 重新设置日志记录器
        if self.logger:
            # 清除现有处理器
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            self.logger = None
        
        self.setup_logger()


class WebAPIInteractionLogger:
    """WebAPI交互日志记录器"""

    def __init__(self, log_path="logs/webapi_interactions.log", enabled=True):
        self.log_path = log_path
        self.enabled = enabled
        self.logger = None
        self.setup_logger()

    def setup_logger(self):
        """设置日志记录器"""
        if not self.enabled:
            return

        # 确保日志目录存在
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 创建专用的WebAPI交互日志记录器
        self.logger = logging.getLogger('webapi_interactions')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器，支持日志轮转
            file_handler = RotatingFileHandler(
                self.log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )

            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_request_start(self, method, path, client_ip):
        """记录请求开始"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"REQUEST_START: {method} {path} from {client_ip}")

    def log_request_end(self, method, path, status_code, duration):
        """记录请求结束"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"REQUEST_END: {method} {path} -> {status_code} ({duration:.2f}ms)")

    def log_chat_request(self, message_length, has_api_key):
        """记录聊天请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"CHAT_REQUEST: MessageLength={message_length}, HasApiKey={has_api_key}")

    def log_chat_response(self, response_length, duration):
        """记录聊天响应"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"CHAT_RESPONSE: ResponseLength={response_length}, Duration={duration:.2f}ms")

    def log_singing_request_start(self, audio_size, volume, loop, motion):
        """记录唱歌请求开始"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SINGING_REQUEST_START: AudioSize={audio_size}bytes, Volume={volume}, Loop={loop}, Motion={motion}")

    def log_singing_audio_decode(self, success, audio_length=None):
        """记录音频解码"""
        if not self.enabled or not self.logger:
            return
        status = "SUCCESS" if success else "FAILED"
        length_info = f", AudioLength={audio_length}s" if audio_length else ""
        self.logger.info(f"SINGING_AUDIO_DECODE: {status}{length_info}")

    def log_singing_motion_trigger(self, motion_index):
        """记录Live2D动作触发"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SINGING_MOTION_TRIGGER: MotionIndex={motion_index}")

    def log_singing_audio_playback_start(self, loop_mode):
        """记录音频播放开始"""
        if not self.enabled or not self.logger:
            return
        mode = "LOOP" if loop_mode else "SINGLE"
        self.logger.info(f"SINGING_AUDIO_PLAYBACK_START: Mode={mode}")

    def log_singing_audio_playback_end(self):
        """记录音频播放结束"""
        if not self.enabled or not self.logger:
            return
        self.logger.info("SINGING_AUDIO_PLAYBACK_END")

    def log_singing_motion_stop(self, motion_index):
        """记录Live2D动作停止"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SINGING_MOTION_STOP: MotionIndex={motion_index}")

    def log_singing_request_complete(self, duration):
        """记录唱歌请求完成"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SINGING_REQUEST_COMPLETE: TotalDuration={duration:.2f}ms")

    def log_interrupt_request(self, has_api_key):
        """记录中断请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"INTERRUPT_REQUEST: HasApiKey={has_api_key}")

    def log_interrupt_response(self, success):
        """记录中断响应"""
        if not self.enabled or not self.logger:
            return
        status = "SUCCESS" if success else "NO_ACTIVE_OPERATIONS"
        self.logger.info(f"INTERRUPT_RESPONSE: Status={status}")

    def log_dialogue_request(self, dialogue_length, has_api_key):
        """记录台词转换请求"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"DIALOGUE_REQUEST: DialogueLength={dialogue_length}, HasApiKey={has_api_key}")

    def log_dialogue_response(self, original_length, converted_length, duration):
        """记录台词转换响应"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"DIALOGUE_RESPONSE: OriginalLength={original_length}, ConvertedLength={converted_length}, Duration={duration:.2f}ms")

    def log_error(self, endpoint, error_type, error_message):
        """记录错误"""
        if not self.enabled or not self.logger:
            return
        self.logger.error(f"WEBAPI_ERROR: Endpoint={endpoint}, Type={error_type}, Message={error_message}")

    def log_system_event(self, event):
        """记录系统事件"""
        if not self.enabled or not self.logger:
            return
        self.logger.info(f"SYSTEM: {event}")

    def update_config(self, log_path=None, enabled=None):
        """更新日志配置"""
        if log_path is not None:
            self.log_path = log_path
        if enabled is not None:
            self.enabled = enabled

        # 重新设置日志记录器
        if self.logger:
            # 清除现有处理器
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            self.logger = None

        self.setup_logger()


class MCPToolManager(QWidget):
    """MCP工具管理器 - 支持标准MCP协议格式"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.mcp_servers = {}  # 标准MCP服务器配置
        self.setup_ui()
        self.load_mcp_config()
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # 左侧：服务器列表和操作按钮
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 服务器列表
        self.server_list = QListWidget()
        self.server_list.itemClicked.connect(self.on_server_selected)
        left_layout.addWidget(QLabel("MCP服务器列表:"))
        left_layout.addWidget(self.server_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = PushButton("添加", self)
        self.edit_btn = PushButton("编辑", self)
        self.delete_btn = PushButton("删除", self)
        self.test_btn = PushButton("测试连接", self)
        self.import_btn = PushButton("导入JSON", self)
        
        self.add_btn.clicked.connect(self.add_server)
        self.edit_btn.clicked.connect(self.edit_server)
        self.delete_btn.clicked.connect(self.delete_server)
        self.test_btn.clicked.connect(self.test_server)
        self.import_btn.clicked.connect(self.import_json)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.import_btn)
        left_layout.addLayout(btn_layout)
        
        # 资源加载按钮
        resource_btn_layout = QHBoxLayout()
        self.load_tools_btn = PushButton("加载工具", self)
        self.load_prompts_btn = PushButton("加载提示", self)
        self.load_resources_btn = PushButton("加载资源", self)
        
        self.load_tools_btn.clicked.connect(self.load_tools)
        self.load_prompts_btn.clicked.connect(self.load_prompts)
        self.load_resources_btn.clicked.connect(self.load_resources)
        
        resource_btn_layout.addWidget(self.load_tools_btn)
        resource_btn_layout.addWidget(self.load_prompts_btn)
        resource_btn_layout.addWidget(self.load_resources_btn)
        left_layout.addLayout(resource_btn_layout)
        
        # 右侧：详细配置
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 配置表单
        form_group = QGroupBox("MCP服务器配置")
        form_layout = QFormLayout(form_group)
        
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("服务器名称")
        form_layout.addRow("名称:", self.name_edit)
        
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["stdio", "sse", "streamablehttp", "python"])
        self.transport_combo.currentTextChanged.connect(self.on_transport_changed)
        form_layout.addRow("传输方式:", self.transport_combo)
        
        # 动态控件容器
        self.dynamic_container = QWidget()
        self.dynamic_layout = QVBoxLayout(self.dynamic_container)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        
        # stdio控件
        self.stdio_group = QWidget()
        stdio_layout = QFormLayout(self.stdio_group)
        self.command_edit = LineEdit()
        self.command_edit.setPlaceholderText("命令 (如: npx)")
        stdio_layout.addRow("命令:", self.command_edit)
        self.args_edit = LineEdit()
        self.args_edit.setPlaceholderText("参数 (如: bing-cn-mcp)")
        stdio_layout.addRow("参数:", self.args_edit)
        self.env_edit = QTextEdit()
        self.env_edit.setPlaceholderText('{"VAR": "value"}')
        self.env_edit.setMaximumHeight(60)
        stdio_layout.addRow("环境变量(JSON):", self.env_edit)
        
        # sse/streamablehttp控件
        self.http_group = QWidget()
        http_layout = QFormLayout(self.http_group)
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("http://localhost:3000/mcp 或 https://api.example.com")
        http_layout.addRow("URL:", self.url_edit)
        self.headers_edit = QTextEdit()
        self.headers_edit.setPlaceholderText('{"Authorization": "Bearer token"}')
        self.headers_edit.setMaximumHeight(60)
        http_layout.addRow("请求头(JSON):", self.headers_edit)
        
        # python控件
        self.python_group = QWidget()
        python_layout = QFormLayout(self.python_group)
        self.module_edit = LineEdit()
        self.module_edit.setPlaceholderText("模块名或文件路径")
        python_layout.addRow("模块/文件:", self.module_edit)
        self.python_args_edit = QTextEdit()
        self.python_args_edit.setPlaceholderText('["arg1", "arg2"]')
        self.python_args_edit.setMaximumHeight(60)
        python_layout.addRow("参数(JSON):", self.python_args_edit)
        
        self.dynamic_layout.addWidget(self.stdio_group)
        self.dynamic_layout.addWidget(self.http_group)
        self.dynamic_layout.addWidget(self.python_group)
        
        form_layout.addRow(self.dynamic_container)
        
        self.enabled_check = CheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("启用:", self.enabled_check)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("服务器描述...")
        self.description_edit.setMaximumHeight(60)
        form_layout.addRow("描述:", self.description_edit)
        
        right_layout.addWidget(form_group)
        
        # 保存按钮
        save_btn = PrimaryToolButton(FIF.SAVE)
        save_btn.setText("保存配置")
        save_btn.clicked.connect(self.save_current_server)
        right_layout.addWidget(save_btn)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # 初始状态
        self.clear_form()
        self.update_buttons()
        self.on_transport_changed("stdio")  # 默认显示stdio
    
    def on_transport_changed(self, transport):
        """传输方式改变时更新界面"""
        self.stdio_group.setVisible(transport == "stdio")
        self.http_group.setVisible(transport in ["sse", "streamablehttp"])
        self.python_group.setVisible(transport == "python")
    
    def load_mcp_config(self):
        """从父组件的配置中加载MCP服务器配置，兼容传统格式"""
        if hasattr(self.parent_widget, 'config_data'):
            mcp_config = self.parent_widget.config_data.get('mcp', {})
            
            # 新格式：直接使用mcpServers
            if 'mcpServers' in mcp_config:
                self.mcp_servers = mcp_config.get('mcpServers', {})
            elif 'servers' in mcp_config:
                self.mcp_servers = mcp_config.get('servers', {})
            # 兼容旧的 tools 列表格式（来自早期实现或测试）
            elif 'tools' in mcp_config:
                # 将tools列表转换为mcp_servers dict
                tools = mcp_config.get('tools', [])
                self.mcp_servers = {}
                for t in tools:
                    name = t.get('name') or f"tool_{len(self.mcp_servers)+1}"
                    cfg = {}
                    # 尝试映射旧字段到新格式
                    cfg['enabled'] = t.get('enabled', True)
                    cfg['description'] = t.get('description', '')
                    # url/path/args
                    if t.get('url'):
                        cfg['transport'] = 'sse'
                        cfg['url'] = t.get('url')
                        cfg['headers'] = {}
                    elif t.get('path'):
                        # 如果看起来是python文件或 .py 后缀，归为 python，否则stdio
                        path = t.get('path')
                        if isinstance(path, str) and path.endswith('.py'):
                            cfg['transport'] = 'python'
                            cfg['module'] = path
                            cfg['args'] = t.get('args', []) if isinstance(t.get('args', []), list) else []
                        else:
                            cfg['transport'] = 'stdio'
                            cfg['command'] = path
                            # 尝试把 args dict 转为 list if necessary
                            args = t.get('args', {})
                            if isinstance(args, dict):
                                # keep as empty list for stdio compatibility
                                cfg['args'] = []
                            elif isinstance(args, list):
                                cfg['args'] = args
                            else:
                                cfg['args'] = []
                            cfg['env'] = {}
                    else:
                        # 作为stdio占位
                        cfg['transport'] = 'stdio'
                        cfg['command'] = ''
                        cfg['args'] = []
                        cfg['env'] = {}
                    self.mcp_servers[name] = cfg
            else:
                # 传统格式转换
                self.mcp_servers = {}
                
                # 处理URLs (sse/streamablehttp)
                urls = mcp_config.get('urls', [])
                if isinstance(urls, str):
                    urls = [url.strip() for url in urls.split(',') if url.strip()]
                elif not isinstance(urls, list):
                    urls = []
                
                for i, url in enumerate(urls):
                    if url.strip():
                        server_name = f'url_server_{i+1}'
                        self.mcp_servers[server_name] = {
                            'transport': 'sse' if url.startswith('http') else 'streamablehttp',
                            'url': url.strip(),
                            'headers': {},
                            'enabled': True,
                            'description': f'从传统URL导入: {url.strip()}'
                        }
                
                # 处理Paths (stdio/python)
                paths = mcp_config.get('paths', [])
                if isinstance(paths, str):
                    paths = [path.strip() for path in paths.split(',') if path.strip()]
                elif not isinstance(paths, list):
                    paths = []
                
                for i, path in enumerate(paths):
                    if path.strip():
                        server_name = f'path_server_{i+1}'
                        # 简单判断是命令还是Python文件
                        if path.endswith('.py') or not os.path.exists(path):
                            transport = 'python'
                            config = {
                                'transport': transport,
                                'module': path.strip(),
                                'args': [],
                                'enabled': True,
                                'description': f'从传统路径导入: {path.strip()}'
                            }
                        else:
                            transport = 'stdio'
                            config = {
                                'transport': transport,
                                'command': path.strip(),
                                'args': [],
                                'env': {},
                                'enabled': True,
                                'description': f'从传统路径导入: {path.strip()}'
                            }
                        self.mcp_servers[server_name] = config
                
                # 自动保存转换后的格式
                if self.mcp_servers:
                    self.save_to_parent_config()
        
        self.refresh_server_list()

    
    def refresh_server_list(self):
        """刷新服务器列表显示"""
        self.server_list.clear()
        for name, config in self.mcp_servers.items():
            enabled = config.get('enabled', True)
            transport = config.get('transport', 'stdio')
            item_text = f"{name} ({transport}) ({'✓' if enabled else '✗'})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.server_list.addItem(item)
    
    def on_server_selected(self, item):
        """服务器选中事件"""
        name = item.data(Qt.UserRole)
        if name in self.mcp_servers:
            server_config = self.mcp_servers[name]
            self.load_server_to_form(name, server_config)
        self.update_buttons()
    
    def load_server_to_form(self, name, config):
        """将服务器配置加载到表单"""
        self.name_edit.setText(name)
        
        transport = config.get('transport', 'stdio')
        index = self.transport_combo.findText(transport)
        if index >= 0:
            self.transport_combo.setCurrentIndex(index)
        
        # 根据传输方式加载不同字段
        if transport == 'stdio':
            self.command_edit.setText(config.get('command', ''))
            args = config.get('args', [])
            if isinstance(args, list):
                self.args_edit.setText(' '.join(str(arg) for arg in args))
            else:
                self.args_edit.setText(str(args))
            env = config.get('env', {})
            self.env_edit.setPlainText(json.dumps(env, indent=2, ensure_ascii=False) if env else '')
            
        elif transport in ['sse', 'streamablehttp']:
            self.url_edit.setText(config.get('url', ''))
            headers = config.get('headers', {})
            self.headers_edit.setPlainText(json.dumps(headers, indent=2, ensure_ascii=False) if headers else '')
            
        elif transport == 'python':
            self.module_edit.setText(config.get('module', ''))
            args = config.get('args', [])
            self.python_args_edit.setPlainText(json.dumps(args, indent=2, ensure_ascii=False) if args else '')
        
        self.enabled_check.setChecked(config.get('enabled', True))
        self.description_edit.setPlainText(config.get('description', ''))
    
    def clear_form(self):
        """清空表单"""
        self.name_edit.clear()
        self.transport_combo.setCurrentIndex(0)
        self.command_edit.clear()
        self.args_edit.clear()
        self.env_edit.clear()
        self.url_edit.clear()
        self.headers_edit.clear()
        self.module_edit.clear()
        self.python_args_edit.clear()
        self.enabled_check.setChecked(True)
        self.description_edit.clear()
    
    def get_form_data(self):
        """从表单获取数据"""
        name = self.name_edit.text().strip()
        transport = self.transport_combo.currentText()
        
        config = {
            'transport': transport,
            'enabled': self.enabled_check.isChecked(),
            'description': self.description_edit.toPlainText().strip()
        }
        
        try:
            if transport == 'stdio':
                args_text = self.args_edit.text().strip()
                args = args_text.split() if args_text else []
                env_text = self.env_edit.toPlainText().strip()
                env = json.loads(env_text) if env_text else {}
                config.update({
                    'command': self.command_edit.text().strip(),
                    'args': args,
                    'env': env
                })
                
            elif transport in ['sse', 'streamablehttp']:
                headers_text = self.headers_edit.toPlainText().strip()
                headers = json.loads(headers_text) if headers_text else {}
                config.update({
                    'url': self.url_edit.text().strip(),
                    'headers': headers
                })
                
            elif transport == 'python':
                args_text = self.python_args_edit.toPlainText().strip()
                args = json.loads(args_text) if args_text else []
                config.update({
                    'module': self.module_edit.text().strip(),
                    'args': args
                })
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
        
        return name, config
    
    def add_server(self):
        """添加新服务器"""
        self.clear_form()
        self.name_edit.setFocus()
        self.update_buttons()
    
    def edit_server(self):
        """编辑当前选中的服务器"""
        current_item = self.server_list.currentItem()
        if current_item:
            name = current_item.data(Qt.UserRole)
            if name in self.mcp_servers:
                self.load_server_to_form(name, self.mcp_servers[name])
    
    def delete_server(self):
        """删除当前选中的服务器"""
        current_item = self.server_list.currentItem()
        if not current_item:
            return
        
        name = current_item.data(Qt.UserRole)
        if name in self.mcp_servers:
            reply = QMessageBox.question(
                self, '确认删除', 
                f'确定要删除服务器 "{name}" 吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.mcp_servers[name]
                self.refresh_server_list()
                self.clear_form()
                self.update_buttons()
                self.save_to_parent_config()
    
    def save_current_server(self):
        """保存当前表单中的服务器配置"""
        try:
            name, config = self.get_form_data()
            
            if not name:
                InfoBar.warning(
                    title='保存失败',
                    content="请输入服务器名称",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 检查名称是否已存在（编辑模式下允许同名）
            current_item = self.server_list.currentItem()
            if current_item:
                old_name = current_item.data(Qt.UserRole)
                if old_name != name and name in self.mcp_servers:
                    InfoBar.warning(
                        title='保存失败',
                        content=f"服务器名称 '{name}' 已存在",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
                # 如果名称改变，删除旧的
                if old_name != name:
                    del self.mcp_servers[old_name]
            
            self.mcp_servers[name] = config
            self.refresh_server_list()
            self.save_to_parent_config()
            
            InfoBar.success(
                title='保存成功',
                content=f"服务器 '{name}' 已保存",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except ValueError as e:
            InfoBar.error(
                title='保存失败',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def test_server(self):
        """测试服务器连接"""
        current_item = self.server_list.currentItem()
        if not current_item:
            InfoBar.warning(
                title='测试失败',
                content="请先选择一个服务器",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        name = current_item.data(Qt.UserRole)
        if name in self.mcp_servers:
            config = self.mcp_servers[name]
            transport = config.get('transport', 'stdio')
            
            try:
                if transport == 'stdio':
                    # 测试命令是否存在
                    command = config.get('command', '')
                    args = config.get('args', [])
                    
                    if command:
                        try:
                            if command == 'npx' and args:
                                # 特殊处理npx命令，测试包是否存在
                                package_name = args[0] if args else ''
                                if package_name:
                                    # 使用完整路径的npx命令
                                    npx_path = r'C:\nvm4w\nodejs\npx.cmd'
                                    result = subprocess.run([npx_path, '--package', package_name, '--yes', 'echo', 'test'], 
                                                          capture_output=True, text=True, timeout=15, 
                                                          env=self._get_conda_env())
                                    if result.returncode == 0:
                                        InfoBar.success(
                                            title='测试成功',
                                            content=f"npx包 '{package_name}' 可用",
                                            orient=Qt.Horizontal,
                                            isClosable=True,
                                            position=InfoBarPosition.TOP,
                                            duration=2000,
                                            parent=self
                                        )
                                    else:
                                        InfoBar.warning(
                                            title='测试结果',
                                            content=f"npx包 '{package_name}' 可能不存在或无法访问: {result.stderr[:100]}",
                                            orient=Qt.Horizontal,
                                            isClosable=True,
                                            position=InfoBarPosition.TOP,
                                            duration=3000,
                                            parent=self
                                        )
                                else:
                                    InfoBar.warning(
                                        title='无法测试',
                                        content="npx命令缺少包名参数",
                                        orient=Qt.Horizontal,
                                        isClosable=True,
                                        position=InfoBarPosition.TOP,
                                        duration=2000,
                                        parent=self
                                    )
                            else:
                                # 普通命令测试
                                result = subprocess.run([command] + (['--help'] if '--help' not in str(args) else []), 
                                                      capture_output=True, text=True, timeout=10,
                                                      env=self._get_conda_env())
                                if result.returncode == 0:
                                    InfoBar.success(
                                        title='测试成功',
                                        content=f"命令 '{command}' 可执行",
                                        orient=Qt.Horizontal,
                                        isClosable=True,
                                        position=InfoBarPosition.TOP,
                                        duration=2000,
                                        parent=self
                                    )
                                else:
                                    InfoBar.warning(
                                        title='测试结果',
                                        content=f"命令返回错误: {result.stderr[:100]}",
                                        orient=Qt.Horizontal,
                                        isClosable=True,
                                        position=InfoBarPosition.TOP,
                                        duration=2000,
                                        parent=self
                                    )
                        except subprocess.TimeoutExpired:
                            InfoBar.warning(
                                title='测试超时',
                                content=f"命令 '{command}' 测试超时",
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=2000,
                                parent=self
                            )
                        except FileNotFoundError:
                            InfoBar.error(
                                title='命令未找到',
                                content=f"命令 '{command}' 未找到，请检查PATH环境变量",
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=3000,
                                parent=self
                            )
                        except Exception as e:
                            InfoBar.error(
                                title='测试失败',
                                content=f"测试命令时出错: {str(e)}",
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=3000,
                                parent=self
                            )
                    else:
                        InfoBar.warning(
                            title='无法测试',
                            content="未配置命令",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                        
                elif transport in ['sse', 'streamablehttp']:
                    # 测试HTTP连接
                    import requests
                    url = config.get('url', '')
                    headers = config.get('headers', {})
                    if url:
                        response = requests.get(url, headers=headers, timeout=10)
                        InfoBar.success(
                            title='连接成功',
                            content=f"URL {url} 响应状态: {response.status_code}",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=3000,
                            parent=self
                        )
                    else:
                        InfoBar.warning(
                            title='无法测试',
                            content="未配置URL",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                        
                elif transport == 'python':
                    # 测试Python模块
                    module = config.get('module', '')
                    if module:
                        if module.endswith('.py'):
                            if os.path.exists(module):
                                InfoBar.success(
                                    title='文件存在',
                                    content=f"Python文件 {module} 存在",
                                    orient=Qt.Horizontal,
                                    isClosable=True,
                                    position=InfoBarPosition.TOP,
                                    duration=2000,
                                    parent=self
                                )
                            else:
                                InfoBar.error(
                                    title='文件不存在',
                                    content=f"Python文件 {module} 不存在",
                                    orient=Qt.Horizontal,
                                    isClosable=True,
                                    position=InfoBarPosition.TOP,
                                    duration=2000,
                                    parent=self
                                )
                        else:
                            # 测试模块导入
                            try:
                                __import__(module)
                                InfoBar.success(
                                    title='模块可用',
                                    content=f"Python模块 {module} 可导入",
                                    orient=Qt.Horizontal,
                                    isClosable=True,
                                    position=InfoBarPosition.TOP,
                                    duration=2000,
                                    parent=self
                                )
                            except ImportError:
                                InfoBar.warning(
                                    title='模块不可用',
                                    content=f"无法导入Python模块 {module}",
                                    orient=Qt.Horizontal,
                                    isClosable=True,
                                    position=InfoBarPosition.TOP,
                                    duration=2000,
                                    parent=self
                                )
                    else:
                        InfoBar.warning(
                            title='无法测试',
                            content="未配置模块",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                        
            except Exception as e:
                InfoBar.error(
                    title='测试失败',
                    content=f"测试过程中出错: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
    
    def update_buttons(self):
        """更新按钮状态"""
        has_selection = self.server_list.currentItem() is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.test_btn.setEnabled(has_selection)
        self.load_tools_btn.setEnabled(has_selection)
        self.load_prompts_btn.setEnabled(has_selection)
        self.load_resources_btn.setEnabled(has_selection)
    
    def import_json(self):
        """从JSON字符串导入服务器配置"""
        dialog = QDialog(self)
        dialog.setWindowTitle("导入MCP服务器配置")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # 说明文本
        info_label = QLabel("粘贴包含 mcpServers 的JSON配置：")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # JSON输入框
        json_edit = QTextEdit()
        json_edit.setPlaceholderText('''例如：
{
  "mcpServers": {
    "bingcn": {
      "command": "npx",
      "args": ["bing-cn-mcp"]
    },
    "filesystem": {
      "transport": "sse",
      "url": "http://localhost:3000/mcp"
    }
  }
}''')
        layout.addWidget(json_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        import_btn = PushButton("导入")
        cancel_btn = PushButton("取消")
        
        import_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.resize(500, 400)
        
        if dialog.exec_() == QDialog.Accepted:
            json_text = json_edit.toPlainText().strip()
            if json_text:
                try:
                    data = json.loads(json_text)
                    
                    # 支持多种格式
                    servers = {}
                    if 'mcpServers' in data:
                        servers = data['mcpServers']
                    elif 'servers' in data:
                        servers = data['servers']
                    elif isinstance(data, dict):
                        # 直接是服务器配置
                        servers = data
                    
                    # 验证和导入
                    imported_count = 0
                    for name, config in servers.items():
                        if isinstance(config, dict):
                            # 标准化配置
                            normalized_config = self.normalize_server_config(config)
                            if normalized_config:
                                self.mcp_servers[name] = normalized_config
                                imported_count += 1
                    
                    if imported_count > 0:
                        self.refresh_server_list()
                        self.save_to_parent_config()
                        InfoBar.success(
                            title='导入成功',
                            content=f"成功导入 {imported_count} 个服务器配置",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                    else:
                        InfoBar.warning(
                            title='导入结果',
                            content="未找到有效的服务器配置",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                        
                except json.JSONDecodeError as e:
                    InfoBar.error(
                        title='导入失败',
                        content=f"JSON格式错误: {str(e)}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                except Exception as e:
                    InfoBar.error(
                        title='导入失败',
                        content=f"导入过程中出错: {str(e)}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
    
    def normalize_server_config(self, config):
        """标准化服务器配置"""
        if not isinstance(config, dict):
            return None
        
        # 检测传输方式
        transport = config.get('transport', 'stdio')
        
        # 如果没有明确指定transport，尝试推断
        if 'transport' not in config:
            if 'command' in config or 'args' in config:
                transport = 'stdio'
            elif 'url' in config:
                transport = 'sse'  # 默认HTTP传输
            elif 'module' in config:
                transport = 'python'
        
        normalized = {
            'transport': transport,
            'enabled': config.get('enabled', True),
            'description': config.get('description', '')
        }
        
        if transport == 'stdio':
            normalized.update({
                'command': config.get('command', ''),
                'args': config.get('args', []),
                'env': config.get('env', {})
            })
        elif transport in ['sse', 'streamablehttp']:
            normalized.update({
                'url': config.get('url', ''),
                'headers': config.get('headers', {})
            })
        elif transport == 'python':
            normalized.update({
                'module': config.get('module', ''),
                'args': config.get('args', [])
            })
        
        return normalized
    
    def _get_conda_env(self):
        """获取包含conda环境的PATH的环境变量"""
        import os
        server_env = os.environ.copy()
        
        # 确保包含conda环境的PATH（如果存在的话）
        # 默认使用my-neuro-tts环境，如果没有设置CONDA_DEFAULT_ENV的话
        conda_env_path = os.environ.get('CONDA_DEFAULT_ENV', 'my-neuro')
        if conda_env_path:
            conda_bin_path = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Scripts' if os.name == 'nt' else 'bin')
            current_path = server_env.get('PATH', '')
            if conda_bin_path not in current_path:
                server_env['PATH'] = conda_bin_path + os.pathsep + current_path
        
        # 强制重新排列PATH，确保Node.js路径在前面
        nodejs_path = r'C:\nvm4w\nodejs'
        if nodejs_path in current_path:
            # 如果Node.js路径已在PATH中，将其移到前面
            paths = current_path.split(os.pathsep)
            paths.remove(nodejs_path)
            paths.insert(0, nodejs_path)
            server_env['PATH'] = os.pathsep.join(paths)
        else:
            # 如果不在PATH中，添加到前面
            server_env['PATH'] = nodejs_path + os.pathsep + current_path
        
        return server_env
    
    def save_to_parent_config(self):
        """保存到父组件的配置中"""
        if hasattr(self.parent_widget, 'config_data'):
            if 'mcp' not in self.parent_widget.config_data:
                self.parent_widget.config_data['mcp'] = {}
            self.parent_widget.config_data['mcp']['mcpServers'] = self.mcp_servers
    
    def get_servers_config(self):
        """获取服务器配置，供外部调用"""
        return {
            'mcpServers': self.mcp_servers
        }

    # 兼容旧接口：返回 tools/urls/paths 以满足旧代码调用 get_tools_config
    def get_tools_config(self):
        """兼容函数：返回旧的 tools/urls/paths 格式以及新的 mcpServers"""
        tools_list = []
        urls = []
        paths = []
        for name, cfg in self.mcp_servers.items():
            if not cfg.get('enabled', True):
                continue
            tool = {
                'name': name,
                'enabled': cfg.get('enabled', True),
                'description': cfg.get('description', '')
            }
            transport = cfg.get('transport', 'stdio')
            if transport in ['sse', 'streamablehttp']:
                tool['type'] = 'server'
                tool['url'] = cfg.get('url', '')
                urls.append(cfg.get('url', ''))
            elif transport == 'python':
                tool['type'] = 'server'
                tool['path'] = cfg.get('module', '')
                paths.append(cfg.get('module', ''))
                tool['args'] = cfg.get('args', [])
            else:
                tool['type'] = 'server'
                tool['path'] = cfg.get('command', '')
                tool['args'] = cfg.get('args', [])
                paths.append(cfg.get('command', ''))

            tools_list.append(tool)

        return {
            'tools': tools_list,
            'urls': [u for u in urls if u],
            'paths': [p for p in paths if p],
            'mcpServers': self.mcp_servers
        }

    def load_tools(self):
        """加载并显示选中服务器的工具列表"""
        current_item = self.server_list.currentItem()
        if not current_item:
            InfoBar.warning(
                title='请选择服务器',
                content="请先选择一个MCP服务器",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        name = current_item.data(Qt.UserRole)
        if name in self.mcp_servers:
            config = self.mcp_servers[name]
            self._load_server_resources(name, config, 'tools')

    def load_prompts(self):
        """加载并显示选中服务器的提示列表"""
        current_item = self.server_list.currentItem()
        if not current_item:
            InfoBar.warning(
                title='请选择服务器',
                content="请先选择一个MCP服务器",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        name = current_item.data(Qt.UserRole)
        if name in self.mcp_servers:
            config = self.mcp_servers[name]
            self._load_server_resources(name, config, 'prompts')

    def load_resources(self):
        """加载并显示选中服务器的资源列表"""
        current_item = self.server_list.currentItem()
        if not current_item:
            InfoBar.warning(
                title='请选择服务器',
                content="请先选择一个MCP服务器",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        name = current_item.data(Qt.UserRole)
        if name in self.mcp_servers:
            config = self.mcp_servers[name]
            self._load_server_resources(name, config, 'resources')

    def _load_server_resources(self, server_name, config, resource_type):
        """加载服务器资源（工具/提示/资源）"""
        # 创建异步任务来加载资源
        import asyncio
        from qasync import QEventLoop, asyncSlot
        
        async def load_async():
            try:
                exit_stack = AsyncExitStack()
                session = None
                
                transport = config.get('transport', 'stdio')
                
                if transport == 'stdio':
                    # 连接stdio服务器
                    command = config.get('command', '')
                    args = config.get('args', [])
                    env = config.get('env', {})
                    
                    if not command:
                        raise ValueError("未配置命令")
                    
                    server_env = self._get_conda_env()
                    if env:
                        server_env.update(env)
                    
                    server_params = StdioServerParameters(
                        command=command,
                        args=args,
                        env=server_env
                    )
                    
                    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                    stdio, write = stdio_transport
                    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
                    
                elif transport in ['sse', 'streamablehttp']:
                    # 连接SSE服务器
                    url = config.get('url', '')
                    headers = config.get('headers', {})
                    
                    if not url:
                        raise ValueError("未配置URL")
                    
                    read, write = await exit_stack.enter_async_context(sse_client(url, headers=headers))
                    session = await exit_stack.enter_async_context(ClientSession(read, write))
                    
                elif transport == 'python':
                    # 连接Python服务器
                    module = config.get('module', '')
                    args = config.get('args', [])
                    
                    if not module:
                        raise ValueError("未配置模块")
                    
                    # 构建命令
                    if module.endswith('.py'):
                        if os.path.exists(module):
                            command = sys.executable
                            args = [module] + args
                        else:
                            raise ValueError(f"Python文件不存在: {module}")
                    else:
                        command = sys.executable
                        args = ['-m', module] + args
                    
                    server_env = self._get_conda_env()
                    server_params = StdioServerParameters(
                        command=command,
                        args=args,
                        env=server_env
                    )
                    
                    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                    stdio, write = stdio_transport
                    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
                
                if session:
                    await session.initialize()
                    
                    # 根据资源类型调用相应的方法
                    if resource_type == 'tools':
                        response = await session.list_tools()
                        resources = response.tools
                        resource_name = "工具"
                    elif resource_type == 'prompts':
                        try:
                            response = await session.list_prompts()
                            resources = response.prompts
                            resource_name = "提示"
                        except AttributeError:
                            # 如果服务器不支持list_prompts
                            resources = []
                            resource_name = "提示"
                    elif resource_type == 'resources':
                        try:
                            response = await session.list_resources()
                            resources = response.resources
                            resource_name = "资源"
                        except AttributeError:
                            # 如果服务器不支持list_resources
                            resources = []
                            resource_name = "资源"
                    
                    # 显示结果
                    if resources:
                        resource_list = []
                        for resource in resources:
                            if hasattr(resource, 'name'):
                                resource_list.append(f"• {resource.name}")
                                if hasattr(resource, 'description') and resource.description:
                                    resource_list.append(f"  描述: {resource.description}")
                            else:
                                resource_list.append(f"• {str(resource)}")
                        
                        result_text = f"{server_name} 服务器的{resource_name}列表:\n\n" + "\n".join(resource_list)
                    else:
                        result_text = f"{server_name} 服务器没有提供任何{resource_name}"
                    
                    # 在主线程中显示结果
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, f"{resource_name}列表", result_text)
                    
                await exit_stack.aclose()
                
            except Exception as e:
                error_msg = f"加载{resource_type}失败: {str(e)}"
                InfoBar.error(
                    title='加载失败',
                    content=error_msg,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
        
        # 运行异步任务
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，创建新任务
                asyncio.create_task(load_async())
            else:
                loop.run_until_complete(load_async())
        except Exception as e:
            InfoBar.error(
                title='异步任务失败',
                content=f"创建异步任务失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )


class DoubaoASRClient:
    """豆包语音识别WebSocket客户端"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.websocket = None
        self.connect_id = None
        self.mode_urls = {
            "双向流式模式（优化版本）": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async",
            "双向流式模式": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
            "流式输入模式": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
        }
    
    def generate_connect_id(self):
        """生成连接ID"""
        import uuid
        self.connect_id = str(uuid.uuid4())
        return self.connect_id
    
    def get_headers(self):
        """获取WebSocket连接头"""
        self.generate_connect_id()
        headers = {
            "X-Api-App-Key": self.config.get('doubao_app_key', ''),
            "X-Api-Access-Key": self.config.get('doubao_access_key', ''),
            "X-Api-Resource-Id": self.config.get('doubao_resource_id', 'volc.bigasr.sauc.duration'),
            "X-Api-Connect-Id": self.connect_id
        }
        return headers
    
    def get_websocket_url(self):
        """获取WebSocket URL"""
        mode = self.config.get('doubao_mode', '双向流式模式（优化版本）')
        return self.mode_urls.get(mode, self.mode_urls["双向流式模式（优化版本）"])
    
    async def connect(self):
        """连接到豆包ASR服务"""
        try:
            import websockets
            import json
            
            url = self.get_websocket_url()
            headers = self.get_headers()
            
            if self.logger:
                self.logger.log_websocket_connection(url, "连接中...")
                self.logger.log_doubao_request(
                    self.config.get('doubao_mode', '双向流式模式（优化版本）'),
                    self.config.get('doubao_packet_size', 200),
                    self.connect_id
                )
            
            # 创建WebSocket连接
            self.websocket = await websockets.connect(
                url, 
                extra_headers=headers,
                timeout=self.config.get('doubao_timeout', 30)
            )
            
            if self.logger:
                self.logger.log_websocket_connection(url, "连接成功")
                # 检查响应头中的logid
                if hasattr(self.websocket, 'response_headers'):
                    logid = self.websocket.response_headers.get('X-Tt-Logid', 'unknown')
                    self.logger.log_doubao_response(logid, "WebSocket连接建立", False)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("连接失败", str(e))
            return False
    
    async def send_audio(self, audio_data, is_last=False):
        """发送音频数据"""
        if not self.websocket:
            return False
        
        try:
            import json
            import base64
            
            # 构建音频包
            audio_packet = {
                "audio": base64.b64encode(audio_data).decode('utf-8'),
                "is_end": is_last
            }
            
            await self.websocket.send(json.dumps(audio_packet))
            
            if self.logger:
                packet_info = f"音频包大小: {len(audio_data)}字节, 是否结束: {is_last}"
                self.logger.log_audio_input(packet_info)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("发送音频失败", str(e))
            return False
    
    async def receive_result(self):
        """接收识别结果"""
        if not self.websocket:
            return None
        
        try:
            import json
            
            response = await self.websocket.recv()
            result_data = json.loads(response)
            
            # 解析结果
            if 'result' in result_data:
                result_text = result_data['result']
                is_final = result_data.get('is_final', False)
                
                if self.logger:
                    logid = result_data.get('log_id', 'unknown')
                    self.logger.log_doubao_response(logid, result_text, is_final)
                
                return {
                    'text': result_text,
                    'is_final': is_final,
                    'raw_data': result_data
                }
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("接收结果失败", str(e))
            return None
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            if self.logger:
                self.logger.log_websocket_connection("", "连接已关闭")


class DoubaoTTSClient:
    """豆包语音合成WebSocket客户端"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.websocket = None
        self.request_id = None
        
    def generate_request_id(self):
        """生成请求ID"""
        import uuid
        self.request_id = str(uuid.uuid4())
        return self.request_id
    
    def get_headers(self):
        """获取WebSocket连接头"""
        headers = {
            "Authorization": f"Bearer;{self.config.get('doubao_access_token', '')}"
        }
        return headers
    
    def get_websocket_url(self):
        """获取WebSocket URL"""
        return self.config.get('doubao_url', 'wss://openspeech.bytedance.com/api/v1/tts/ws_binary')
    
    async def connect(self):
        """连接到豆包TTS服务"""
        try:
            import websockets
            url = self.get_websocket_url()
            headers = self.get_headers()
            
            if self.logger:
                self.logger.log_websocket_connection(url, "正在连接...")
            
            self.websocket = await websockets.connect(
                url, 
                additional_headers=headers,
                max_size=10 * 1024 * 1024  # 10MB
            )
            
            if self.logger:
                logid = self.websocket.response.headers.get('x-tt-logid', 'unknown')
                self.logger.log_websocket_connection(url, f"连接成功, LogID: {logid}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("连接失败", str(e))
            return False
    
    async def synthesize_text(self, text):
        """合成文本为语音"""
        if not self.websocket:
            if self.logger:
                self.logger.log_error("WebSocket未连接", "请先调用connect()方法")
            return None
        
        try:
            import json
            
            self.generate_request_id()
            
            # 构建请求数据
            request_data = {
                "app": {
                    "appid": self.config.get('doubao_app_id', ''),
                    "token": self.config.get('doubao_access_token', ''),
                    "cluster": "volcano_tts"
                },
                "user": {
                    "uid": self.request_id
                },
                "audio": {
                    "voice_type": self.config.get('doubao_voice_type', ''),
                    "encoding": self.config.get('doubao_encoding', 'wav')
                },
                "request": {
                    "reqid": self.request_id,
                    "text": text,
                    "operation": "submit",
                    "with_timestamp": "1",
                    "extra_param": json.dumps({
                        "disable_markdown_filter": False
                    })
                }
            }
            
            # 记录请求日志
            if self.logger:
                self.logger.log_doubao_request(
                    self.config.get('doubao_app_id', ''),
                    self.config.get('doubao_voice_type', ''),
                    self.config.get('doubao_encoding', 'wav'),
                    text
                )
            
            # 发送请求
            from volcengine_protocols import full_client_request
            await full_client_request(self.websocket, json.dumps(request_data).encode())
            
            # 接收音频数据
            audio_data = bytearray()
            
            from volcengine_protocols import receive_message, MsgType
            
            while True:
                msg = await receive_message(self.websocket)
                
                if msg.type == MsgType.FrontEndResultServer:
                    continue
                elif msg.type == MsgType.AudioOnlyServer:
                    audio_data.extend(msg.payload)
                    
                    # 记录响应日志
                    if self.logger:
                        logid = self.websocket.response.headers.get('x-tt-logid', 'unknown')
                        is_final = msg.sequence < 0
                        self.logger.log_doubao_response(logid, len(msg.payload), is_final)
                    
                    if msg.sequence < 0:  # 最后一个消息
                        break
                else:
                    if self.logger:
                        self.logger.log_error("TTS转换失败", str(msg))
                    return None
            
            if not audio_data:
                if self.logger:
                    self.logger.log_error("TTS转换失败", "未接收到音频数据")
                return None
            
            return bytes(audio_data)
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("语音合成失败", str(e))
            return None
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            if self.logger:
                self.logger.log_websocket_connection("", "连接已关闭")


class FishAudioTTSClient:
    """Fish Audio TTS客户端"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        
    def synthesize_text(self, text):
        """使用Fish Audio合成文本为语音"""
        try:
            # 尝试导入Fish Audio SDK
            try:
                from fish_audio_sdk import WebSocketSession, TTSRequest, ReferenceAudio
            except ImportError:
                if self.logger:
                    self.logger.log_error("Fish Audio SDK未安装", "请安装fish-audio-sdk: pip install fish-audio-sdk")
                return None
            
            api_key = self.config.get('fish_audio_api_key', '')
            if not api_key:
                if self.logger:
                    self.logger.log_error("Fish Audio配置错误", "API Key未配置")
                return None
            
            # 记录请求日志
            reference_id = self.config.get('fish_audio_reference_id', '')
            backend = self.config.get('fish_audio_backend', 'speech-1.6')
            temperature = self.config.get('fish_audio_temperature', 0.7)
            top_p = self.config.get('fish_audio_top_p', 0.7)
            
            if self.logger:
                self.logger.log_fish_audio_request(reference_id, text, backend, temperature, top_p)
            
            # 创建WebSocket会话
            sync_websocket = WebSocketSession(api_key)
            
            # 创建TTS请求
            if reference_id:
                # 使用预设的reference_id
                tts_request = TTSRequest(
                    text=text,
                    reference_id=reference_id,
                    temperature=temperature,
                    top_p=top_p
                )
            else:
                # 使用参考音频文件
                ref_audio_path = self.config.get('fish_audio_ref_audio', '')
                ref_text = self.config.get('fish_audio_ref_text', '')
                
                if not ref_audio_path or not os.path.exists(ref_audio_path):
                    if self.logger:
                        self.logger.log_error("Fish Audio配置错误", "参考音频文件不存在")
                    return None
                
                with open(ref_audio_path, 'rb') as f:
                    ref_audio_data = f.read()
                
                tts_request = TTSRequest(
                    text=text,
                    references=[
                        ReferenceAudio(
                            audio=ref_audio_data,
                            text=ref_text
                        )
                    ],
                    temperature=temperature,
                    top_p=top_p
                )
            
            # 生成语音
            audio_data = bytearray()
            
            def text_stream():
                """文本流生成器"""
                for word in text.split():
                    yield word + " "
            
            # 调用TTS API
            for chunk in sync_websocket.tts(
                tts_request,
                text_stream(),
                backend=backend
            ):
                audio_data.extend(chunk)
            
            if self.logger:
                self.logger.log_fish_audio_response("成功", len(audio_data))
            
            return bytes(audio_data)
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Fish Audio TTS失败", str(e))
            return None


class LocalTTSClient:
    """本地TTS客户端"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
    
    def synthesize_text(self, text):
        """使用本地TTS合成文本为语音"""
        try:
            if self.logger:
                voice_model = self.config.get('voice', '')
                self.logger.log_local_tts_request(text, voice_model)
            
            # 这里可以实现各种本地TTS引擎的调用
            # 例如：pyttsx3, espeak, festival 等
            
            # 示例：使用HTTP API调用本地TTS服务
            tts_url = self.config.get('local_url') or self.config.get('url', '')
            if not tts_url:
                if self.logger:
                    self.logger.log_error("本地TTS配置错误", "TTS URL未配置")
                return None
            
            # 构建请求参数
            params = {
                'text': text,
                'language': self.config.get('language', 'zh'),
                'voice': self.config.get('voice', ''),
                'speed': self.config.get('speed', 1.0),
                'volume': self.config.get('volume', 1.0)
            }
            
            # 发送TTS请求
            response = requests.post(tts_url, json=params, timeout=30)
            
            if response.status_code == 200:
                audio_data = response.content
                if self.logger:
                    self.logger.log_local_tts_response("成功", f"音频大小: {len(audio_data)}字节")
                return audio_data
            else:
                if self.logger:
                    self.logger.log_error("本地TTS请求失败", f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            if self.logger:
                self.logger.log_error("本地TTS失败", str(e))
            return None


class AudioPlaybackThread(QThread):
    """音频播放后台线程，避免阻塞UI"""
    
    finished = pyqtSignal()  # 播放完成信号
    error = pyqtSignal(str)  # 错误信号
    trigger_motion = pyqtSignal(int)  # 触发Live2D动作信号
    
    def __init__(self, audio_data, volume, loop, singing_motion, ui_widget):
        super().__init__()
        self.audio_data = audio_data
        self.volume = volume
        self.loop = loop
        self.singing_motion = singing_motion
        self.ui_widget = ui_widget
        self.temp_path = None
        self.is_running = True
        
    def run(self):
        """在后台线程中执行音频播放"""
        try:
            # 保存音频数据到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(self.audio_data)
                self.temp_path = temp_file.name
            
            # 触发Live2D动作 - 通过信号发送到主线程
            motion_map = {
                '唱歌': 5,
                '开始唱歌': 5,
                '停止唱歌': 7,
                '跳舞': 6,
                '开心': 1,
                '悲伤': 2,
                '生气': 3,
                '惊讶': 4
            }
            singing_motion_index = motion_map.get(self.singing_motion, 5)
            self.trigger_motion.emit(singing_motion_index)
            
            # 执行音频播放
            self._play_audio()
            
            # 停止Live2D动作 - 通过信号发送到主线程
            self.trigger_motion.emit(7)
                
        except Exception as e:
            self.error.emit(f"音频播放异常: {str(e)}")
        finally:
            # 清理临时文件
            if self.temp_path and os.path.exists(self.temp_path):
                try:
                    os.unlink(self.temp_path)
                except:
                    pass
            self.finished.emit()
    
    def _play_audio(self):
        """执行音频播放"""
        if sys.platform == 'win32':
            self._play_windows()
        else:
            self._play_unix()
    
    def _play_windows(self):
        """Windows平台音频播放"""
        import winsound
        import time
        
        try:
            # 获取音频时长
            duration = 0
            try:
                with wave.open(self.temp_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate) if rate > 0 else 0
            except:
                duration = 0
            
            if self.loop:
                # 循环播放
                while self.is_running:
                    try:
                        # 使用同步播放，这样可以更好地控制循环
                        winsound.PlaySound(self.temp_path, winsound.SND_FILENAME)
                        
                        # 检查是否需要停止（在播放间隔中检查）
                        if not self.is_running:
                            break
                            
                        # 短暂延迟后继续下一轮循环
                        time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"Windows循环播放异常: {e}")
                        break
            else:
                # 单次播放
                if self.is_running:  # 检查是否需要播放
                    winsound.PlaySound(self.temp_path, winsound.SND_FILENAME)
                    # 等待播放完成
                    if duration > 0:
                        time.sleep(min(duration + 0.5, 30.0))  # 额外0.5秒缓冲，最长30秒
                    else:
                        time.sleep(2.0)  # 默认等待2秒
                    
        except Exception as e:
            print(f"Windows音频播放异常: {e}")
    
    def _play_unix(self):
        """Unix/Linux/Mac平台音频播放"""
        import subprocess
        import time
        
        try:
            if self.loop:
                # 循环播放
                while self.is_running:
                    try:
                        # 检查是否需要停止
                        if not self.is_running:
                            break
                            
                        cmd = ['aplay', self.temp_path]
                        result = subprocess.run(cmd, timeout=30, capture_output=True)
                        if result.returncode != 0:
                            print(f"aplay命令执行失败: {result.stderr.decode()}")
                            break
                            
                        # 检查是否需要停止（在播放间隔中检查）
                        if not self.is_running:
                            break
                            
                        time.sleep(0.5)  # 短暂延迟后继续下一轮循环
                        
                    except subprocess.TimeoutExpired:
                        continue
                    except Exception as e:
                        print(f"Unix循环播放异常: {e}")
                        break
            else:
                # 单次播放
                if self.is_running:  # 检查是否需要播放
                    cmd = ['aplay', self.temp_path]
                    result = subprocess.run(cmd, timeout=60, capture_output=True)  # 60秒超时
                    if result.returncode != 0:
                        print(f"aplay命令执行失败: {result.stderr.decode()}")
                    
        except Exception as e:
            print(f"Unix音频播放异常: {e}")
    
    def stop(self):
        """停止播放"""
        self.is_running = False


class BatWorker(QThread):
    """
    后台线程用于执行BAT文件并捕获输出
    """
    output_signal = pyqtSignal(str)  # 输出信号
    finished_signal = pyqtSignal()    # 完成信号
    
    def __init__(self, bat_path):
        super().__init__()
        self.bat_path = bat_path
        self.process = None
        self.is_running = True

    def run(self):
        """执行BAT文件并实时捕获输出"""
        try:
            # 如果是 .bat，优先用 PowerShell 点源 Run-MyNeuro.ps1 或 .venv 激活后再执行
            if isinstance(self.bat_path, str) and self.bat_path.lower().endswith('.bat'):
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                bat_dir = os.path.dirname(os.path.abspath(self.bat_path))
                bat_abs = os.path.abspath(self.bat_path)
                # PowerShell 单引号内转义：将 ' 替换为 ''
                bat_ps = bat_abs.replace("'", "''")
                ps_cmd = (
                    "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                    f"\"Set-Location -Path '{bat_dir}'; "
                    "Write-Host '=== 环境检查 ==='; "
                    "Write-Host ('PWD: ' + (Get-Location).Path); "
                    "Write-Host ('CONDA_DEFAULT_ENV: ' + ($env:CONDA_DEFAULT_ENV)); "
                    "Write-Host ('VIRTUAL_ENV: ' + ($env:VIRTUAL_ENV)); "
                    "Write-Host '=== 启动脚本 ==='; "
                    f"& '{bat_ps}'\""
                )
                # 强制切换到 UTF-8 代码页后再执行，避免中文乱码
                wrapped = f"chcp 65001 >NUL & {ps_cmd}"
                self.process = subprocess.Popen(
                    wrapped,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    bufsize=0,
                    cwd=bat_dir
                )
            elif isinstance(self.bat_path, str) and self.bat_path.lower().endswith('.ps1'):
                # 处理PowerShell脚本
                script_dir = os.path.dirname(os.path.abspath(self.bat_path))
                script_abs = os.path.abspath(self.bat_path)
                # PowerShell 单引号内转义：将 ' 替换为 ''
                script_ps = script_abs.replace("'", "''")
                ps_cmd = (
                    "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                    f"\"Set-Location -Path '{script_dir}'; "
                    "Write-Host '=== 环境检查 ==='; "
                    "Write-Host ('PWD: ' + (Get-Location).Path); "
                    "Write-Host ('CONDA_DEFAULT_ENV: ' + ($env:CONDA_DEFAULT_ENV)); "
                    "Write-Host ('VIRTUAL_ENV: ' + ($env:VIRTUAL_ENV)); "
                    "Write-Host '=== 启动PowerShell脚本 ==='; "
                    f"& '{script_ps}'\""
                )
                # 强制切换到 UTF-8 代码页后再执行，避免中文乱码
                wrapped = f"chcp 65001 >NUL & {ps_cmd}"
                self.process = subprocess.Popen(
                    wrapped,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    bufsize=0,
                    cwd=script_dir
                )
            else:
                wrapped = f"chcp 65001 >NUL & {self.bat_path}"
                self.process = subprocess.Popen(
                    wrapped,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    bufsize=0
                )

            # 实时读取输出
            while self.is_running and self.process and self.process.stdout:
                raw = self.process.stdout.readline()
                if not raw:
                    break
                if isinstance(raw, bytes):
                    try:
                        s = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            s = raw.decode('gbk', errors='replace')
                        except Exception:
                            s = raw.decode('utf-8', errors='replace')
                else:
                    s = raw
                s = s.strip()
                # 打印带颜色的输出到控制台
                self.print_colored(s)
                # 发送原始输出到UI
                self.output_signal.emit(s)

            # 等待进程结束
            if self.process:
                self.process.wait()
        except Exception as e:
            self.output_signal.emit(f"错误: {str(e)}")
        finally:
            self.finished_signal.emit()
    def print_colored(self, text):
        """根据日志级别打印带颜色的文本"""
        if "DEBUG" in text:
            print(f"\033[0;36m{text}\033[0m")  # 青色
        elif "INFO" in text:
            print(f"\033[0;32m{text}\033[0m")  # 绿色
        elif "WARNING" in text:
            print(f"\033[1;33m{text}\033[0m")  # 黄色
        elif "ERROR" in text or "CRITICAL" in text:
            print(f"\033[1;31m{text}\033[0m")  # 红色
        else:
            print(text)
    
    def stop(self):
        """停止BAT进程"""
        self.is_running = False
        if self.process:
            os.system('taskkill /t /f /pid {}'.format(self.process.pid))


class DropArea(QGroupBox):
    """简易拖拽区域，用于接收文件路径。"""
    def __init__(self, title: str, filter_desc: str = "", parent=None):
        super().__init__(title, parent)
        self.setAcceptDrops(True)
        self.file_path = ""

        layout = QVBoxLayout(self)
        self.tip_label = QLabel(filter_desc or "将文件拖拽到此处，或点击按钮选择")
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setStyleSheet("color: #666;")
        self.select_btn = QPushButton("选择文件…")
        layout.addWidget(self.tip_label)
        layout.addWidget(self.select_btn)

        # 外观
        self.setStyleSheet(
            """
            QGroupBox { border: 1px dashed #c8c8c8; border-radius: 8px; margin-top: 8px; }
            QGroupBox::title { left: 8px; top: -6px; }
            """
        )

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            url = e.mimeData().urls()[0]
            path = url.toLocalFile()
            if path:
                self.set_file_path(path)
        e.acceptProposedAction()

    def set_file_path(self, path: str):
        self.file_path = path
        base = os.path.basename(path)
        self.tip_label.setText(f"已选择：{base}")

class ModelFetchWorker(QThread):
    """后台获取模型列表的线程，兼容 OpenAI /v1/models 及 Ollama API"""
    success = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api_url: str, api_key: str, api_type: str = "OpenAI兼容API", parent=None):
        super().__init__(parent)
        self.api_url = api_url or ''
        self.api_key = api_key or ''
        self.api_type = api_type

    def _request_models_openai(self, base_url: str):
        """请求OpenAI兼容API的模型列表"""
        try:
            import requests  # 延迟导入，避免无依赖时影响主程序
        except Exception:
            return None, '未安装 requests 库，无法请求模型列表。'
        url = base_url.rstrip('/') + '/models'
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        try:
            r = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            return None, f'网络请求失败：{e}'
        if r.status_code >= 400:
            return None, f'HTTP {r.status_code} 错误：{r.text[:200]}'
        try:
            j = r.json()
        except Exception as e:
            return None, f'解析响应失败：{e}'
        return j, None

    def _request_models_ollama(self, base_url: str):
        """请求Ollama API的模型列表"""
        try:
            import requests
        except Exception:
            return None, '未安装 requests 库，无法请求模型列表。'
        
        # Ollama API endpoint
        url = base_url.rstrip('/') + '/api/tags'
        headers = {'Content-Type': 'application/json'}
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            return None, f'Ollama API请求失败：{e}'
        
        if r.status_code >= 400:
            return None, f'Ollama API HTTP {r.status_code} 错误：{r.text[:200]}'
        
        try:
            j = r.json()
        except Exception as e:
            return None, f'Ollama API响应解析失败：{e}'
        
        return j, None

    def _extract_models(self, payload):
        models = []
        
        if self.api_type == "Ollama API":
            # Ollama API 返回格式：{"models": [{"name": "model_name", ...}, ...]}
            if isinstance(payload, dict) and 'models' in payload:
                for item in payload['models']:
                    if isinstance(item, dict) and 'name' in item:
                        models.append(item['name'])
            return list(dict.fromkeys(models))  # 去重并保持顺序
        
        # OpenAI兼容API格式
        if isinstance(payload, dict):
            data = None
            if isinstance(payload.get('data'), list):
                data = payload['data']
            elif isinstance(payload.get('models'), list):
                data = payload['models']
            if data is not None:
                for item in data:
                    if isinstance(item, str):
                        models.append(item)
                    elif isinstance(item, dict):
                        mid = item.get('id') or item.get('name') or item.get('model') or item.get('slug')
                        if isinstance(mid, str):
                            models.append(mid)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, str):
                    models.append(item)
                elif isinstance(item, dict):
                    mid = item.get('id') or item.get('name') or item.get('model') or item.get('slug')
                    if isinstance(mid, str):
                        models.append(mid)
        # 去重并保持顺序
        seen = set()
        dedup = []
        for m in models:
            if m not in seen:
                seen.add(m)
                dedup.append(m)
        return dedup

    def run(self):
        if not self.api_url:
            self.error.emit('请先填写 API URL')
            return
        
        models = []
        err = None
        
        if self.api_type == "Ollama API":
            # Ollama API 直接请求 /api/tags
            payload, err = self._request_models_ollama(self.api_url)
            if err is None and payload is not None:
                models = self._extract_models(payload)
        else:
            # OpenAI兼容API：先尝试 /models，再尝试 /v1/models
            payload, err = self._request_models_openai(self.api_url)
            if err is None and payload is not None:
                models = self._extract_models(payload)
            # 兜底：如果为空或失败，尝试 /v1/models（避免重复尝试）
            if (err is not None or not models) and '/v1' not in self.api_url:
                payload2, err2 = self._request_models_openai(self.api_url.rstrip('/') + '/v1')
                if err2 is None and payload2 is not None:
                    models = self._extract_models(payload2)
                    err = None
                else:
                    err = err or err2
        
        if models:
            self.success.emit(models)
        else:
            error_msg = err or '未获取到可用模型'
            if self.api_type == "Ollama API":
                error_msg += '\n提示：请确保Ollama服务正在运行，并且URL格式正确（如：http://localhost:11434）'
            self.error.emit(error_msg)

class Interface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        # 创建浮动按钮容器
        self.floatingContainer = QWidget(self)
        self.floatingContainer.setObjectName('floatingContainer')
        self.floatingLayout = QHBoxLayout(self.floatingContainer)
        self.floatingLayout.setContentsMargins(0, 0, 0, 0)
        
        # 创建正方形保存按钮
        self.saveButton = PrimaryToolButton(FIF.SAVE, self.floatingContainer)
        self.saveButton.setFixedSize(50, 50)  # 正方形尺寸
        self.saveButton.clicked.connect(self.save_config)

        # 创建正方形加载按钮
        self.reloadButton = ToolButton(FIF.SYNC, self.floatingContainer)
        self.reloadButton.setFixedSize(50, 50)  # 正方形尺寸
        self.reloadButton.clicked.connect(self.reload_config)

         # 创建正方形开启按钮
        self.startButton = PrimaryToolButton(FIF.PLAY, self.floatingContainer)
        self.startButton.setFixedSize(50, 50)  # 正方形尺寸
        self.startButton.clicked.connect(self.start_bat_msg)

        # 创建正方形关闭按钮
        self.closeButton = ToolButton(FIF.POWER_BUTTON, self.floatingContainer)
        self.closeButton.setFixedSize(50, 50)  # 正方形尺寸
        self.closeButton.clicked.connect(self.close_bat_msg)
        
        self.floatingLayout.addWidget(self.saveButton)
        self.floatingLayout.addWidget(self.reloadButton)
        self.floatingLayout.addWidget(self.startButton)
        self.floatingLayout.addWidget(self.closeButton)
        
        # 设置浮动容器
        self.floatingContainer.setFixedSize(120, 50)
        self.floatingContainer.setAttribute(Qt.WA_TranslucentBackground)
        self.floatingContainer.raise_()

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 45, 0, 0)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setSpacing(30)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.view.setObjectName('view')

        # 初始化工作线程
        self.bat_worker = None

        # 初始位置设置
        self.updateButtonPosition()

    def resizeEvent(self, event):
        """窗口大小改变时更新按钮位置"""
        super().resizeEvent(event)
        self.updateButtonPosition()

    def showEvent(self, event):
        """显示时更新按钮位置"""
        super().showEvent(event)
        self.updateButtonPosition()

    def updateButtonPosition(self):
        """更新按钮位置到右下角"""
        # 获取滚动区域的大小
        scroll_width = self.width()
        scroll_height = self.height()
        
        # 计算右下角位置
        button_width = self.floatingContainer.width()
        button_height = self.floatingContainer.height()
        margin = 20  # 距离边缘的边距
        
        # 右下角位置计算
        x = scroll_width - button_width - margin
        y = scroll_height - button_height - margin
        
        # 设置位置
        self.floatingContainer.move(x, y)

    def event(self, event):
        if event.type() == QEvent.LayoutRequest:
            self.updateButtonPosition()
        return super().event(event)

    # --- Default no-op handlers for subclasses that don't use floating buttons ---
    def save_config(self):
        """Default stub: subclasses can override. Keeps signal connections valid."""
        pass

    def reload_config(self):
        """Default stub: subclasses can override."""
        pass

    def start_bat_msg(self):
        """Default stub: subclasses can override."""
        pass

    def close_bat_msg(self):
        """Default stub: subclasses can override."""
        pass

class Widget(Interface):

    def __init__(self, text, num, parent=None):
        super().__init__(parent=parent)
        self.config_path = os.path.abspath("config.json")
        self.config_data = self.load_config()
        # 初始化日志处理器
        self.log_handler = None
        self.widgets = {}
        self._model_fetchers = []  # 保持线程引用，避免被GC
        self.setObjectName(text.replace(' ', '-'))

        # 初始化WebAPI服务器
        self.webapi_server = None
        self.webapi_server_thread = None

        # 检查是否需要自动启动WebAPI
        webapi_auto_start = self.config_data.get('webapi', {}).get('auto_start', False)
        webapi_enabled = self.config_data.get('webapi', {}).get('enabled', False)
        
        if webapi_auto_start and webapi_enabled:
            try:
                self.start_webapi_server()
                print("WebAPI服务已自动启动")
            except Exception as e:
                print(f"WebAPI自动启动失败: {str(e)}")

        # 初始化LLM交互日志记录器
        self.init_llm_logger()

        # 初始化Live2D模型连接
        self.init_live2d_connection()

        # 进入对应的标签页创建函数
        self.tab_chose(num)()

    def init_llm_logger(self):
        """初始化LLM交互日志记录器"""
        llm_config = self.config_data.get('llm', {})
        log_enabled = llm_config.get('log_enabled', True)
        log_path = llm_config.get('log_path', 'logs/llm_interactions.log')
        
        self.llm_logger = LLMInteractionLogger(log_path, log_enabled)
        
        if log_enabled:
            self.llm_logger.log_system_event("LLM交互日志系统已启动")
        
        # 初始化ASR交互日志记录器
        self.init_asr_logger()
        
        # 初始化TTS交互日志记录器
        self.init_tts_logger()
    
    def init_asr_logger(self):
        """初始化ASR交互日志记录器"""
        asr_config = self.config_data.get('asr', {})
        log_enabled = asr_config.get('log_enabled', True)
        log_path = asr_config.get('log_path', 'logs/asr_interactions.log')
        
        self.asr_logger = ASRInteractionLogger(log_path, log_enabled)
        
        if log_enabled:
            self.asr_logger.log_system_event("ASR交互日志系统已启动")
    
    def init_tts_logger(self):
        """初始化TTS交互日志记录器"""
        tts_config = self.config_data.get('tts', {})
        log_enabled = tts_config.get('log_enabled', True)
        log_path = tts_config.get('log_path', 'logs/tts_interactions.log')
        
        self.tts_logger = TTSInteractionLogger(log_path, log_enabled)
        
        if log_enabled:
            self.tts_logger.log_system_event("TTS交互日志系统已启动")
        
        # 初始化WebAPI交互日志记录器
        self.init_webapi_logger()
    
    def init_webapi_logger(self):
        """初始化WebAPI交互日志记录器"""
        webapi_config = self.config_data.get('webapi', {})
        log_enabled = webapi_config.get('log_enabled', True)
        log_path = webapi_config.get('log_path', 'logs/webapi_interactions.log')
        
        self.webapi_logger = WebAPIInteractionLogger(log_path, log_enabled)
        
        if log_enabled:
            self.webapi_logger.log_system_event("WebAPI交互日志系统已启动")
    
    def init_live2d_connection(self):
        """初始化Live2D模型连接"""
        try:
            # 尝试获取Live2D模型实例的引用
            self.live2d_model = None
            
            # 配置Live2D模型日志处理器
            if hasattr(self, 'log_handler') and self.log_handler:
                live2d_logger = logging.getLogger('live2d_model')
                live2d_logger.addHandler(self.log_handler)
                live2d_logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别以显示详细日志
                main_logger = logging.getLogger()
                main_logger.info("Live2D模型日志处理器已配置")
            
            # 方法1：尝试从models模块获取全局实例
            try:
                import models.live2d_model as live2d_module
                if hasattr(live2d_module, '_model') and live2d_module._model:
                    self.live2d_model = live2d_module._model
                    main_logger = logging.getLogger()
                    main_logger.info("成功获取Live2D模型实例")
                    return True
            except ImportError:
                main_logger = logging.getLogger()
                main_logger.warning("无法导入models.live2d_model模块")
            
            # 方法2：尝试从其他可能的位置获取
            try:
                # 检查是否有全局的app_manager或event_bus
                from core.app_manager import AppManager
                # 这里可以添加更多获取模型实例的方法
            except ImportError:
                pass
            
            return False
            
        except Exception as e:
            main_logger = logging.getLogger()
            main_logger.error(f"初始化Live2D连接失败: {e}")
            return False

    def tab_chose(self, num):
        """创建各个配置部分的标签页"""
        tab_list = [self.create_main_tab,
                    self.create_llm_tab,
                    self.create_asr_tab,
                    self.create_tts_tab,
                    self.create_ui_tab,
                    self.create_subtitle_tab,
                    self.create_user_input_tab,
                    self.create_animation_tab,
                    self.create_other_tab,
                    self.create_setting_tab,
                    self.create_voice_clone_tab
                    ]
        return tab_list[num]
    
    def load_config(self):
        """加载或创建配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                MessageBox.critical(self, "错误", f"加载配置文件失败:\n{str(e)}")
                return {}
        return {}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 收集所有控件的值
            self.collect_values()
            
            # 如果存在MCP管理器，保存其配置
            if hasattr(self, 'mcp_manager'):
                mcp_config = self.mcp_manager.get_tools_config()
                self.config_data.setdefault('mcp', {}).update(mcp_config)
            
            # 更新LLM日志记录器配置
            if hasattr(self, 'llm_logger'):
                llm_config = self.config_data.get('llm', {})
                self.llm_logger.update_config(
                    log_path=llm_config.get('log_path', 'logs/llm_interactions.log'),
                    enabled=llm_config.get('log_enabled', True)
                )
            
            # 更新ASR日志记录器配置
            if hasattr(self, 'asr_logger'):
                asr_config = self.config_data.get('asr', {})
                self.asr_logger.update_config(
                    log_path=asr_config.get('log_path', 'logs/asr_interactions.log'),
                    enabled=asr_config.get('log_enabled', True)
                )
            
            # 更新TTS日志记录器配置
            if hasattr(self, 'tts_logger'):
                tts_config = self.config_data.get('tts', {})
                self.tts_logger.update_config(
                    log_path=tts_config.get('log_path', 'logs/tts_interactions.log'),
                    enabled=tts_config.get('log_enabled', True)
                )
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            InfoBar.success(
                title='保存成功',
                content="已成功保存到config.json文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return True
        except Exception as e:
            InfoBar.error(
                title='保存失败',
                content=f"保存失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self
            )
            return False
    
    def collect_values(self):
        """收集所有控件的值到配置数据中"""
        for key_path, widget_info in self.widgets.items():
            widget = widget_info["widget"]
            current_value = None
            
            if isinstance(widget, LineEdit):
                current_value = widget.text()
            elif isinstance(widget, PasswordLineEdit):
                current_value = widget.text()
            elif isinstance(widget, CheckBox):
                current_value = widget.isChecked()
            elif isinstance(widget, SpinBox):
                current_value = widget.value()
            elif isinstance(widget, DoubleSpinBox):
                current_value = widget.value()
            elif isinstance(widget, QComboBox):
                data = widget.currentData()
                current_value = data if data is not None else widget.currentText()
            elif isinstance(widget, QTextEdit):
                current_value = widget.toPlainText()
            else:
                # 处理其他未知类型的widget，避免current_value为None
                print(f"Unknown widget type for {key_path}: {type(widget)}")
                continue
            
            # 更新配置数据
            keys = key_path.split('.')
            config_ptr = self.config_data
            for key in keys[:-1]:
                config_ptr = config_ptr.setdefault(key, {})
            config_ptr[keys[-1]] = current_value
        
        # 处理对话框颜色选择器的值
        if hasattr(self, 'bg_color_picker'):
            r, g, b, a = self.bg_color_picker.get_rgba()
            self.config_data.setdefault('user_input', {}).update({
                'bg_color_r': r,
                'bg_color_g': g,
                'bg_color_b': b,
                'bg_color_a': a
            })
        
        if hasattr(self, 'text_color_picker'):
            r, g, b = self.text_color_picker.get_rgb()
            self.config_data.setdefault('user_input', {}).update({
                'text_color_r': r,
                'text_color_g': g,
                'text_color_b': b
            })
        
        if hasattr(self, 'border_color_picker'):
            r, g, b = self.border_color_picker.get_rgb()
            self.config_data.setdefault('user_input', {}).update({
                'border_color_r': r,
                'border_color_g': g,
                'border_color_b': b
            })
        
        if hasattr(self, 'status_bg_color_picker'):
            r, g, b, a = self.status_bg_color_picker.get_rgba()
            self.config_data.setdefault('user_input', {}).update({
                'status_bg_color_r': r,
                'status_bg_color_g': g,
                'status_bg_color_b': b,
                'status_bg_color_a': a
            })
        
        # 处理字幕颜色选择器的值
        if hasattr(self, 'subtitle_text_color_picker'):
            r, g, b, a = self.subtitle_text_color_picker.get_rgba()
            self.config_data.setdefault('subtitle', {}).update({
                'text_color_r': r,
                'text_color_g': g,
                'text_color_b': b,
                'text_color_a': a
            })
        
        if hasattr(self, 'subtitle_outline_color_picker'):
            r, g, b, a = self.subtitle_outline_color_picker.get_rgba()
            self.config_data.setdefault('subtitle', {}).update({
                'outline_color_r': r,
                'outline_color_g': g,
                'outline_color_b': b,
                'outline_color_a': a
            })
        
        if hasattr(self, 'subtitle_bg_color_picker'):
            r, g, b, a = self.subtitle_bg_color_picker.get_rgba()
            self.config_data.setdefault('subtitle', {}).update({
                'bg_color_r': r,
                'bg_color_g': g,
                'bg_color_b': b,
                'bg_color_a': a
            })
        
        # 兼容性处理：如果有新的tts.local_url，也同步到tts.url以保持向后兼容
        if 'tts' in self.config_data and 'local_url' in self.config_data['tts']:
            local_url = self.config_data['tts']['local_url']
            if local_url:  # 只有在local_url有值时才同步
                self.config_data['tts']['url'] = local_url
        
    def reload_config(self):
        """重新加载配置文件"""
        self.config_data = self.load_config()
        self.update_widgets()
        
        # 重新初始化日志记录器
        if hasattr(self, 'llm_logger'):
            self.init_llm_logger()
        if hasattr(self, 'asr_logger'):
            self.init_asr_logger()
        if hasattr(self, 'tts_logger'):
            self.init_tts_logger()
        
        # 重新加载MCP管理器配置
        if hasattr(self, 'mcp_manager'):
            self.mcp_manager.load_mcp_config()
        
        InfoBar.success(
                title='加载成功',
                content="已重新加载配置文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        
    # LLM交互日志记录方法
    def log_user_input(self, user_input):
        """记录用户输入到LLM"""
        if hasattr(self, 'llm_logger'):
            self.llm_logger.log_user_input(user_input)
    
    def log_llm_response(self, response):
        """记录LLM响应"""
        if hasattr(self, 'llm_logger'):
            llm_config = self.config_data.get('llm', {})
            api_type = llm_config.get('api_type', 'OpenAI兼容API')
            model = llm_config.get('model', '')
            self.llm_logger.log_llm_response(response, model, api_type)
    
    def log_api_request(self, api_url, model, prompt_tokens=0):
        """记录LLM API请求"""
        if hasattr(self, 'llm_logger'):
            self.llm_logger.log_api_request(api_url, model, prompt_tokens)
    
    def log_api_response(self, status_code, response_tokens=0, error=None):
        """记录LLM API响应"""
        if hasattr(self, 'llm_logger'):
            self.llm_logger.log_api_response(status_code, response_tokens, error)
    
    def log_system_event(self, event):
        """记录系统事件"""
        if hasattr(self, 'llm_logger'):
            self.llm_logger.log_system_event(event)
    
    # ASR交互日志记录方法
    def log_audio_input(self, audio_info):
        """记录音频输入到ASR"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_audio_input(audio_info)
    
    def log_asr_result(self, result, confidence=0):
        """记录ASR识别结果"""
        if hasattr(self, 'asr_logger'):
            asr_config = self.config_data.get('asr', {})
            asr_type = asr_config.get('asr_type', '本地ASR')
            self.asr_logger.log_recognition_result(result, confidence, asr_type)
    
    def log_websocket_connection(self, url, status):
        """记录WebSocket连接状态"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_websocket_connection(url, status)
    
    def log_doubao_request(self, mode, packet_size, connect_id):
        """记录豆包ASR请求"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_doubao_request(mode, packet_size, connect_id)
    
    def log_doubao_response(self, logid, result, is_final=False):
        """记录豆包ASR响应"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_doubao_response(logid, result, is_final)
    
    def log_asr_error(self, error_type, error_message):
        """记录ASR错误"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_error(error_type, error_message)
    
    def log_asr_system_event(self, event):
        """记录ASR系统事件"""
        if hasattr(self, 'asr_logger'):
            self.asr_logger.log_system_event(event)
    
    # TTS交互日志记录方法
    def log_tts_text_input(self, text, tts_type=""):
        """记录TTS文本输入"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_text_input(text, tts_type)
    
    def log_tts_synthesis_request(self, text, voice_type="", parameters=None):
        """记录TTS合成请求"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_synthesis_request(text, voice_type, parameters)
    
    def log_tts_synthesis_result(self, status, audio_length=0, tts_type=""):
        """记录TTS合成结果"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_synthesis_result(status, audio_length, tts_type)
    
    def log_tts_websocket_connection(self, url, status):
        """记录TTS WebSocket连接状态"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_websocket_connection(url, status)
    
    def log_tts_doubao_request(self, appid, voice_type, encoding, text):
        """记录豆包TTS请求"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_doubao_request(appid, voice_type, encoding, text)
    
    def log_tts_doubao_response(self, logid, audio_size, is_final=False):
        """记录豆包TTS响应"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_doubao_response(logid, audio_size, is_final)
    
    def log_tts_fish_audio_request(self, reference_id, text, backend="", temperature=0, top_p=0):
        """记录Fish Audio TTS请求"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_fish_audio_request(reference_id, text, backend, temperature, top_p)
    
    def log_tts_fish_audio_response(self, status, audio_size):
        """记录Fish Audio TTS响应"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_fish_audio_response(status, audio_size)
    
    def log_tts_local_request(self, text, voice_model=""):
        """记录本地TTS请求"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_local_tts_request(text, voice_model)
    
    def log_tts_local_response(self, status, audio_file=""):
        """记录本地TTS响应"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_local_tts_response(status, audio_file)
    
    def log_tts_error(self, error_type, error_message):
        """记录TTS错误"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_error(error_type, error_message)
    
    def log_tts_system_event(self, event):
        """记录TTS系统事件"""
        if hasattr(self, 'tts_logger'):
            self.tts_logger.log_system_event(event)
        
    def start_bat_msg(self):
        if self.bat_worker and self.bat_worker.isRunning():
            InfoBar.warning(
                title='打开失败',
                content="你已经有了一个肥牛了哦，别太贪心",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=InfoBar.desktopView()
            )
        else:
            self.start_bat()
            InfoBar.success(
                title='启动成功',
                content="快来和肥牛聊天吧！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=InfoBar.desktopView()
            )

    def close_bat_msg(self):
        if self.bat_worker and self.bat_worker.isRunning():
            self.stop_bat()
            InfoBar.success(
                title='关闭成功',
                content="肥牛被你关掉了呜呜~",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=InfoBar.desktopView()
            )
        else:
            InfoBar.warning(
                title='关闭失败',
                content="你还没开呢",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=InfoBar.desktopView()
            )

    def start_bat(self):
        """启动BAT进程"""
        # 清除之前的输出
        self.left_browser.clear()

        # 启动BAT时显示动作按钮（如果设置中启用）
        action_buttons_enabled = self.config_data.get('setting', {}).get('action_buttons_enabled', False)
        self.append_output(f"动作按钮启用状态: {action_buttons_enabled}")
        if action_buttons_enabled:
            # 通过socket发送信号给main.py显示动作按钮
            try:
                import socket
                import json
                import time
                
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(2.0)
                client_socket.connect(('127.0.0.1', 8889))
                
                signal_data = {
                    "type": "show_action_buttons",
                    "timestamp": time.time(),
                    "source": "ui_bat_start"
                }
                
                client_socket.send(json.dumps(signal_data).encode('utf-8'))
                client_socket.close()
                
                self.append_output("✓ 已发送显示动作按钮信号给main.py")
                
            except (socket.timeout, socket.error) as e:
                self.append_output(f"⚠ 发送显示动作按钮信号失败: {e}")
        else:
            self.append_output("动作按钮已禁用")

        # 确保日志处理器已设置
        if not self.log_handler:
            self.log_handler = QTextBrowserHandler(self.left_browser)
            logger = logging.getLogger()
            logger.addHandler(self.log_handler)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.log_handler.setFormatter(formatter)
        
        # 创建并启动工作线程
        self.bat_worker = BatWorker(r"start_project.bat")  # 启动主脚本
        self.bat_worker.output_signal.connect(self.append_output)
        self.bat_worker.finished_signal.connect(self.on_bat_finished)
        self.bat_worker.start()
        
        # 更新UI
        self.append_output("BAT脚本已启动...")
        
        # 检查是否需要自动启动WebAPI
        webapi_auto_start = self.config_data.get('webapi', {}).get('auto_start', False)
        webapi_enabled = self.config_data.get('webapi', {}).get('enabled', False)
        
        if webapi_auto_start and webapi_enabled:
            self.append_output("检测到WebAPI自动启动已启用，正在启动WebAPI服务...")
            try:
                self.start_webapi_server()
                self.append_output("WebAPI服务已自动启动")
            except Exception as e:
                self.append_output(f"WebAPI自动启动失败: {str(e)}")
        else:
            if webapi_auto_start and not webapi_enabled:
                self.append_output("WebAPI自动启动已启用，但WebAPI未启用，请在设置中启用WebAPI")
            else:
                self.append_output("WebAPI自动启动已禁用")
        
     
    
    def stop_bat(self):
        """停止BAT进程"""
        if self.bat_worker and self.bat_worker.isRunning():
            self.bat_worker.stop()
            self.append_output("正在停止BAT脚本...")

        # 检查是否需要自动停止WebAPI
        webapi_auto_start = self.config_data.get('webapi', {}).get('auto_start', False)
        if webapi_auto_start and hasattr(self, 'webapi_server') and self.webapi_server:
            self.append_output("正在停止WebAPI服务...")
            try:
                self.stop_webapi_server()
                self.append_output("WebAPI服务已停止")
            except Exception as e:
                self.append_output(f"WebAPI停止失败: {str(e)}")

        # 停止TerminalRoom中的所有服务进程
        try:
            # 通过parent链访问Window实例
            window = None
            if self.parent() and self.parent().parent():
                window = self.parent().parent()
            
            if window and hasattr(window, 'TerminalInterface') and window.TerminalInterface:
                terminal_interface = window.TerminalInterface
                for key in ['tts', 'asr', 'bert', 'rag']:
                    proc = terminal_interface.processes.get(key)
                    if proc and proc.poll() is None:
                        self.append_output(f"正在停止{key.upper()}服务...")
                        # 停止对应的reader线程
                        reader = terminal_interface.readers.get(key)
                        if reader and reader.isRunning():
                            reader.stop()
                        # 强制终止进程
                        try:
                            import subprocess
                            subprocess.run(["taskkill", "/t", "/f", "/pid", str(proc.pid)],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                         creationflags=0x08000000)
                            self.append_output(f"{key.upper()}服务已停止")
                        except Exception as e:
                            self.append_output(f"停止{key.upper()}服务失败: {str(e)}")
        except Exception as e:
            self.append_output(f"停止TerminalRoom进程时出错: {str(e)}")

        # 隐藏动作按钮悬浮窗口
        # 通过socket发送信号给main.py隐藏动作按钮
        try:
            import socket
            import json
            import time
            
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2.0)
            client_socket.connect(('127.0.0.1', 8889))
            
            signal_data = {
                "type": "hide_action_buttons",
                "timestamp": time.time(),
                "source": "ui_bat_stop"
            }
            
            client_socket.send(json.dumps(signal_data).encode('utf-8'))
            client_socket.close()
            
            self.append_output("✓ 已发送隐藏动作按钮信号给main.py")
            
        except (socket.timeout, socket.error) as e:
            self.append_output(f"⚠ 发送隐藏动作按钮信号失败: {e}")

    def append_output(self, text):
        # 根据日志级别添加HTML样式
        if "DEBUG" in text:
            html_text = f'<span style="color:cyan;">{text}</span>'
        elif "INFO" in text:
            html_text = f'<span style="color:green;">{text}</span>'
        elif "WARNING" in text:
            html_text = f'<span style="color:orange;font-weight:bold;">{text}</span>'
        elif "ERROR" in text or "CRITICAL" in text:
            html_text = f'<span style="color:red;font-weight:bold;">{text}</span>'
        else:
            html_text = text
        
        self.left_browser.append(html_text)
        # 自动滚动到底部
        self.left_browser.verticalScrollBar().setValue(
            self.left_browser.verticalScrollBar().maximum()
        )
    
    def on_bat_finished(self):
        """BAT完成时的处理"""
        self.append_output("BAT脚本已停止")
        
        # 检查是否需要自动停止WebAPI
        webapi_auto_start = self.config_data.get('webapi', {}).get('auto_start', False)
        if webapi_auto_start and hasattr(self, 'webapi_server') and self.webapi_server:
            self.append_output("正在停止WebAPI服务...")
            try:
                self.stop_webapi_server()
                self.append_output("WebAPI服务已停止")
            except Exception as e:
                self.append_output(f"WebAPI停止失败: {str(e)}")
        
        # 停止TerminalRoom中的所有服务进程
        try:
            # 通过parent链访问Window实例
            window = None
            if self.parent() and self.parent().parent():
                window = self.parent().parent()
            
            if window and hasattr(window, 'TerminalInterface') and window.TerminalInterface:
                terminal_interface = window.TerminalInterface
                for key in ['tts', 'asr', 'bert', 'rag']:
                    proc = terminal_interface.processes.get(key)
                    if proc and proc.poll() is None:
                        self.append_output(f"正在停止{key.upper()}服务...")
                        # 停止对应的reader线程
                        reader = terminal_interface.readers.get(key)
                        if reader and reader.isRunning():
                            reader.stop()
                        # 强制终止进程
                        try:
                            import subprocess
                            subprocess.run(["taskkill", "/t", "/f", "/pid", str(proc.pid)],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                         creationflags=0x08000000)
                            self.append_output(f"{key.upper()}服务已停止")
                        except Exception as e:
                            self.append_output(f"停止{key.upper()}服务失败: {str(e)}")
        except Exception as e:
            self.append_output(f"停止TerminalRoom进程时出错: {str(e)}")
        
        # BAT停止时隐藏动作按钮
        # 动作按钮已迁移到main.py，由main.py管理
        self.append_output("动作按钮悬浮窗口由main.py管理")

    # WebAPI服务器相关方法
    def start_webapi_server(self):
        """启动WebAPI服务器"""
        if self.webapi_server and self.webapi_server.is_running:
            InfoBar.warning(
                title='服务已运行',
                content="WebAPI服务已在运行中",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 获取配置
        host = self.config_data.get('webapi', {}).get('host', '127.0.0.1')
        port = self.config_data.get('webapi', {}).get('port', 8888)
        
        # 创建并启动服务器
        self.webapi_server = WebAPIServer(host, port, self)
        self.webapi_server.status_changed.connect(self.on_webapi_status_changed)
        self.webapi_server.start()
    
    def stop_webapi_server(self):
        """停止WebAPI服务器"""
        if self.webapi_server:
            self.webapi_server.stop_server()
            self.webapi_server = None
        else:
            InfoBar.info(
                title='服务未运行',
                content="WebAPI服务未启动",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def on_webapi_status_changed(self, is_running, message):
        """WebAPI服务状态变化处理"""
        if hasattr(self, 'webapi_status_label'):
            status_text = "服务状态: " + ("运行中" if is_running else "已停止")
            self.webapi_status_label.setText(status_text)
            
            if is_running:
                self.webapi_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.webapi_status_label.setStyleSheet("color: #666;")
        
        # 显示状态消息
        if is_running:
            InfoBar.success(
                title='服务启动成功',
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.info(
                title='服务状态',
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def test_webapi(self):
        """测试WebAPI连接"""
        host = self.config_data.get('webapi', {}).get('host', '127.0.0.1')
        port = self.config_data.get('webapi', {}).get('port', 8888)
        api_key = self.config_data.get('webapi', {}).get('api_key', '')
        
        test_url = f"http://{host}:{port}/api/status"
        
        try:
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                InfoBar.success(
                    title='连接成功',
                    content=f"WebAPI服务响应正常: {response.json().get('message', '')}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.warning(
                    title='连接异常',
                    content=f"服务响应代码: {response.status_code}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        except requests.exceptions.ConnectionError:
            InfoBar.error(
                title='连接失败',
                content=f"无法连接到 {test_url}，请检查服务是否启动",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='测试失败',
                content=f"测试过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def process_llm_request(self, message, image_data=None):
        """处理LLM请求的核心方法 - 支持视觉识别"""
        try:
            # 获取LLM配置
            llm_config = self.config_data.get('llm', {})
            if not llm_config.get('api_url') or not llm_config.get('api_key'):
                return "错误：LLM配置不完整，请检查API URL和API Key设置"
            
            # 获取视觉配置
            vision_config = self.config_data.get('vision', {})
            vision_enabled = vision_config.get('enabled', False)
            
            # 检查是否有图片数据且需要视觉处理
            vision_result = ""
            if image_data and vision_enabled:
                # 检查主LLM是否支持视觉，或者配置为仅fallback使用
                main_model = llm_config.get('model', '')
                fallback_only = vision_config.get('fallback_only', True)
                
                # 判断主模型是否支持视觉（简单的模型名称判断）
                vision_supported_models = ['gpt-4-vision', 'gpt-4o', 'claude-3', 'gemini-pro-vision']
                main_supports_vision = any(vm in main_model.lower() for vm in vision_supported_models)
                
                # 如果主模型不支持视觉，或者不是仅fallback模式，则使用视觉模型
                if not main_supports_vision or not fallback_only:
                    vision_result = self._process_vision_request(image_data, vision_config)
                    if vision_result.startswith("错误："):
                        return vision_result
                    
                    # 如果成功获取视觉识别结果，将其作为上下文添加到消息中
                    if vision_result:
                        message = f"[图片识别结果]: {vision_result}\n\n[用户问题]: {message}"
            
            # 构建LLM请求
            api_url = llm_config['api_url'].rstrip('/') + '/chat/completions'
            api_key = llm_config['api_key']
            model = llm_config.get('model', 'gpt-3.5-turbo')
            system_prompt = llm_config.get('system_prompt', '你是一个有用的AI助手。')
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            # 如果主模型支持视觉且有图片数据，添加图片到消息中
            if image_data and not vision_result:  # 只有当没有使用独立视觉模型时才添加
                try:
                    import base64
                    # 假设image_data是base64编码的图片数据
                    if isinstance(image_data, str):
                        image_b64 = image_data
                    else:
                        image_b64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # 修改最后一条用户消息，添加图片
                    messages[-1] = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                except Exception as e:
                    print(f"处理图片数据时出错: {e}")
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # 记录API请求
            self.log_api_request(api_url, model, len(message))
            
            # 发送请求
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    llm_response = result['choices'][0]['message']['content']
                    
                    # 记录成功响应
                    response_tokens = result.get('usage', {}).get('completion_tokens', 0)
                    self.log_api_response(200, response_tokens)
                    
                    return llm_response
                else:
                    self.log_api_response(200, 0, "响应格式错误")
                    return "错误：LLM返回的响应格式不正确"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.log_api_response(response.status_code, 0, error_msg)
                return f"错误：LLM API请求失败 - {error_msg}"
                
        except requests.exceptions.Timeout:
            self.log_api_response(0, 0, "请求超时")
            return "错误：LLM API请求超时"
        except requests.exceptions.ConnectionError:
            self.log_api_response(0, 0, "连接错误")
            return "错误：无法连接到LLM API服务"
        except Exception as e:
            self.log_api_response(0, 0, str(e))
            return f"错误：处理LLM请求时发生异常 - {str(e)}"
    
    def _process_vision_request(self, image_data, vision_config):
        """处理视觉识别请求"""
        try:
            if not vision_config.get('api_url') or not vision_config.get('api_key'):
                return "错误：视觉模型配置不完整，请检查API URL和API Key设置"
            
            api_url = vision_config['api_url'].rstrip('/') + '/chat/completions'
            api_key = vision_config['api_key']
            model = vision_config.get('model', 'gpt-4-vision-preview')
            vision_prompt = vision_config.get('system_prompt', '请仔细观察这张图片，描述你看到的内容。')
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            # 处理图片数据
            import base64
            if isinstance(image_data, str):
                image_b64 = image_data
            else:
                image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # 构建视觉识别消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            # 发送视觉识别请求
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    vision_result = result['choices'][0]['message']['content']
                    print(f"✓ 视觉识别完成: {vision_result[:100]}...")
                    return vision_result
                else:
                    return "错误：视觉模型返回的响应格式不正确"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return f"错误：视觉模型API请求失败 - {error_msg}"
                
        except Exception as e:
            return f"错误：处理视觉识别请求时发生异常 - {str(e)}"
    
    def process_image_input(self):
        """处理图片输入 - 支持从剪贴板获取图片"""
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QPixmap
            import base64
            import io
            
            # 从剪贴板获取图片
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasImage():
                # 从剪贴板获取图片
                image = clipboard.image()
                if not image.isNull():
                    # 将QImage转换为base64
                    byte_array = io.BytesIO()
                    pixmap = QPixmap.fromImage(image)
                    pixmap.save(byte_array, format='JPEG', quality=85)
                    image_bytes = byte_array.getvalue()
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    print("✓ 已从剪贴板获取图片")
                    return image_b64
            
            # 如果剪贴板没有图片，可以添加文件选择对话框
            from PyQt5.QtWidgets import QFileDialog
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self, 
                "选择图片文件", 
                "", 
                "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            
            if file_path:
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                print(f"✓ 已从文件获取图片: {file_path}")
                return image_b64
            
            return None
            
        except Exception as e:
            print(f"获取图片时出错: {e}")
            return None
    
    def _test_vision_recognition(self):
        """测试视觉识别功能"""
        try:
            # 检查视觉模式是否启用
            vision_config = self.config_data.get('vision', {})
            if not vision_config.get('enabled', False):
                InfoBar.warning(
                    title='视觉模式未启用',
                    content='请先在视觉模型配置中启用视觉模式',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 检查配置完整性
            if not vision_config.get('api_url') or not vision_config.get('api_key'):
                InfoBar.warning(
                    title='视觉模型配置不完整',
                    content='请先配置视觉模型的API URL和API Key',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 获取图片数据
            image_data = self.process_image_input()
            if not image_data:
                InfoBar.warning(
                    title='未找到图片',
                    content='请先复制图片到剪贴板或准备图片文件',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 执行视觉识别
            InfoBar.info(
                title='视觉识别中...',
                content='正在进行图片识别，请稍候',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 在后台线程中执行识别
            import threading
            def run_vision_test():
                try:
                    result = self._process_vision_request(image_data, vision_config)
                    
                    # 在主线程中显示结果
                    def show_result():
                        if result.startswith("错误："):
                            InfoBar.error(
                                title='视觉识别失败',
                                content=result,
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=5000,
                                parent=self
                            )
                        else:
                            # 创建结果显示对话框
                            dialog = QDialog(self)
                            dialog.setWindowTitle("视觉识别结果")
                            dialog.setModal(True)
                            dialog.resize(600, 400)
                            
                            layout = QVBoxLayout(dialog)
                            
                            # 添加结果文本框
                            result_text = QTextEdit()
                            result_text.setPlainText(result)
                            result_text.setReadOnly(True)
                            layout.addWidget(result_text)
                            
                            # 添加关闭按钮
                            close_btn = QPushButton("关闭")
                            close_btn.clicked.connect(dialog.accept)
                            layout.addWidget(close_btn)
                            
                            dialog.exec_()
                            
                            InfoBar.success(
                                title='视觉识别成功',
                                content='已完成图片识别，结果已显示',
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=3000,
                                parent=self
                            )
                    
                    # 使用QTimer在主线程中执行
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, show_result)
                    
                except Exception as e:
                    def show_error():
                        InfoBar.error(
                            title='测试异常',
                            content=f'视觉识别测试过程中出错: {str(e)}',
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=5000,
                            parent=self
                        )
                    
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, show_error)
            
            test_thread = threading.Thread(target=run_vision_test)
            test_thread.daemon = True
            test_thread.start()
            
        except Exception as e:
            InfoBar.error(
                title='测试失败',
                content=f"测试过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def interrupt_current_operations(self):
        """打断当前AI输出和语音播放 - 只发送中断信号，由main.py处理"""
        try:
            interrupted_something = False

            # 1. 通过进程间通信发送中断信号给main.py
            try:
                import socket
                import json
                import time
                
                # 尝试通过socket发送中断信号
                socket_success = False
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(2.0)  # 2秒超时
                    client_socket.connect(('127.0.0.1', 8889))  # main.py监听的端口
                    
                    signal_data = {
                        "type": "interrupt",
                        "timestamp": time.time(),
                        "source": "ui_interrupt"
                    }
                    
                    client_socket.send(json.dumps(signal_data).encode('utf-8'))
                    client_socket.close()
                    
                    print("✓ 已通过socket发送中断信号")
                    socket_success = True
                    interrupted_something = True
                    
                except (socket.timeout, socket.error) as e:
                    print(f"⚠ Socket通信失败: {e}，将使用文件信号")
                
                # 如果socket失败，使用文件信号作为备用
                if not socket_success:
                    try:
                        with open("interrupt_signal.tmp", 'w', encoding='utf-8') as f:
                            signal_data = {
                                "type": "interrupt", 
                                "timestamp": time.time(),
                                "source": "ui_interrupt",
                                "force_stop": True
                            }
                            json.dump(signal_data, f)
                        print("✓ 已创建中断信号文件")
                        interrupted_something = True
                    except Exception as e:
                        print(f"⚠ 创建中断信号文件失败: {e}")
                
                # 等待一小段时间让main.py处理信号
                time.sleep(0.1)
                
            except Exception as e:
                print(f"⚠ 发送中断信号时出错: {e}")

            # 2. 记录打断操作
            if hasattr(self, 'log_system_event'):
                self.log_system_event("用户通过UI打断当前操作")

            return interrupted_something

        except Exception as e:
            print(f"打断操作时出错: {e}")
            return False

    def update_widgets(self):
        """更新所有控件显示的值"""
        for key_path, widget_info in self.widgets.items():
            widget = widget_info["widget"]
            keys = key_path.split('.')
            value = self.config_data
            for key in keys:
                value = value.get(key, None)
                if value is None:
                    break
            
            if value is None:
                continue
                
            if isinstance(widget, LineEdit):
                widget.setText(str(value))
            elif isinstance(widget, PasswordLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, CheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, SpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, DoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QComboBox):
                # 优先按 data(真实路径) 匹配，其次按文本匹配
                idx = -1
                for i in range(widget.count()):
                    if widget.itemData(i) == value or widget.itemText(i) == str(value):
                        idx = i
                        break
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))
            else:
                # 处理其他未知类型的widget
                print(f"Unknown widget type for {key_path}: {type(widget)} in update_widgets")

    def create_form_group(self, parent, title, fields):
        """创建表单组"""
        group = QGroupBox(title)
        form_layout = QFormLayout()
        
        for field in fields:
            label, key_path, widget_type, default = field
            widget = None
            
            # 获取当前值（如果存在）
            keys = key_path.split('.')
            value = self.config_data
            for key in keys:
                value = value.get(key, default)
            
            # 创建控件
            if widget_type == "lineedit":
                widget = LineEdit(parent)
                widget.setText(str(value))
            elif widget_type == "passwordlineedit":
                widget = PasswordLineEdit()
                widget.setText(str(value))
            elif widget_type == "checkbox":
                widget = CheckBox()
                widget.setChecked(bool(value))
            elif widget_type == "spinbox":
                widget = SpinBox()
                widget.setRange(0, 999999)
                widget.setValue(int(value))
            elif widget_type == "doublespin":
                widget = DoubleSpinBox()
                widget.setRange(0, 100)
                widget.setValue(float(value))
                widget.setSingleStep(0.1)
            
            if widget:
                form_layout.addRow(label, widget)
                self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        group.setLayout(form_layout)
        return group
    
    def create_main_tab(self):
        """创建主菜单标签页"""
        self.saveButton.hide()
        self.reloadButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 主水平布局 - 分为左右两部分
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)  # 左右部分之间的间距

        # 左侧部分 - TextBrowser (占50%宽度)
        self.left_browser = TextBrowser(self)
        self.left_browser.setObjectName('leftBrowser')
        main_layout.addWidget(self.left_browser, 1)  # 拉伸因子为1，占一半空间

        # 右侧部分 - 垂直布局 (占50%宽度)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)  # 上下两部分之间的间距
        
        # 右上部分 - 图片 (占50%高度)
        self.pic_label = PixmapLabel(self)
        self.pic_label.setScaledContents(True)  # 图片缩放填充
        pic = QPixmap("resource/fake_neuro.jpg")
        self.pic_label.setPixmap(pic.scaled(
                400,
                400,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        right_layout.addWidget(self.pic_label, 1)  # 拉伸因子为1，占一半高度
        
        # 右下部分 - 文本区域 (占50%高度)
        self.right_browser = TextBrowser(self)
        self.right_browser.setObjectName('rightBrowser')
        right_layout.addWidget(self.right_browser, 1)  # 拉伸因子为1，占一半高度
        
        main_layout.addLayout(right_layout, 1)  # 拉伸因子为1，占一半空间

        # 添加主布局到界面
        self.vBoxLayout.addLayout(main_layout)

        # 设置示例文本
        self.left_browser.setText("终端输出于此处，毕竟是测试版本，如果出现了bug也很正常吧（")
        self.right_browser.setHtml("<p>欢迎使用，点击按钮即可打开终端(*´∀ ˋ*)。<br/>什么，你想问上图作者是谁(*ﾟ∀ﾟ*)？<br/>是<b>菊花茶洋参</b>大佬哦ξ( ✿＞◡❛)<br>本体程序由<b>老汤圆</b>大佬完成(☄⊙ω⊙)☄<br>但是当前你运行的是由<b>猫尾草</b>魔改的版本~(￣0￣)/</p>")
        
        # 设置日志处理器
        if not self.log_handler:
            self.log_handler = QTextBrowserHandler(self.left_browser)
            logger = logging.getLogger()
            logger.addHandler(self.log_handler)
            
            # 设置日志格式
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.log_handler.setFormatter(formatter)

    def create_llm_tab(self):
        """创建LLM配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # API类型选择组
        api_type_group = QGroupBox("API类型配置")
        api_type_form = QFormLayout(api_type_group)
        
        # API类型下拉选择
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["OpenAI兼容API", "Ollama API"])
        current_api_type = self.config_data.get('llm', {}).get('api_type', 'OpenAI兼容API')
        index = self.api_type_combo.findText(current_api_type)
        if index >= 0:
            self.api_type_combo.setCurrentIndex(index)
        self.widgets['llm.api_type'] = {"widget": self.api_type_combo, "type": "combobox"}
        api_type_form.addRow("API类型:", self.api_type_combo)
        
        # 交互日志开关
        log_enabled_check = CheckBox()
        log_enabled_check.setChecked(bool(self.config_data.get('llm', {}).get('log_enabled', True)))
        self.widgets['llm.log_enabled'] = {"widget": log_enabled_check, "type": "checkbox"}
        api_type_form.addRow("启用交互日志:", log_enabled_check)
        
        # 日志文件路径
        log_path_edit = LineEdit()
        log_path_edit.setText(self.config_data.get('llm', {}).get('log_path', 'logs/llm_interactions.log'))
        log_path_edit.setPlaceholderText("日志文件保存路径")
        self.widgets['llm.log_path'] = {"widget": log_path_edit, "type": "lineedit"}
        api_type_form.addRow("日志文件路径:", log_path_edit)
        
        self.vBoxLayout.addWidget(api_type_group)
        
        # 基础 LLM 配置
        fields = [
            ("API Key", "llm.api_key", "passwordlineedit", ""),
            ("API URL", "llm.api_url", "lineedit", ""),
            ("启用限制", "llm.enable_limit", "checkbox", False),
            ("最大消息数", "llm.max_messages", "spinbox", 8),
            ("系统提示词", "llm.system_prompt", "lineedit", "")
        ]
        group = self.create_form_group(self, "大语言模型配置", fields)
        # 追加：模型 可编辑下拉 + 获取按钮
        form = group.layout()  # QFormLayout
        llm_model_row = QHBoxLayout()
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.setEditable(True)
        # 初始值来源于配置
        llm_model_val = self.config_data.get('llm', {}).get('model', '') if isinstance(self.config_data, dict) else ''
        if llm_model_val:
            self.llm_model_combo.setEditText(str(llm_model_val))
        llm_fetch_btn = QPushButton('获取模型')
        llm_fetch_btn.clicked.connect(lambda: self._on_click_fetch_models(
            api_url_key='llm.api_url', api_key_key='llm.api_key', combo=self.llm_model_combo, btn=llm_fetch_btn
        ))
        llm_model_row.addWidget(self.llm_model_combo)
        llm_model_row.addWidget(llm_fetch_btn)
        row_container = QWidget()
        row_container.setLayout(llm_model_row)
        form.addRow('模型', row_container)
        # 注册
        self.widgets['llm.model'] = {"widget": self.llm_model_combo, "type": "combobox"}
        self.vBoxLayout.addWidget(group)

        # 视觉模型配置组
        vision_group = QGroupBox("视觉模型配置")
        vision_form = QFormLayout(vision_group)
        
        # 启用视觉模式
        vision_enabled_check = CheckBox()
        vision_enabled_check.setChecked(bool(self.config_data.get('vision', {}).get('enabled', False)))
        self.widgets['vision.enabled'] = {"widget": vision_enabled_check, "type": "checkbox"}
        vision_form.addRow("启用视觉模式:", vision_enabled_check)
        
        # 视觉模型API Key
        vision_api_key = PasswordLineEdit()
        vision_api_key.setText(self.config_data.get('vision', {}).get('api_key', ''))
        vision_api_key.setPlaceholderText("视觉模型的API Key")
        self.widgets['vision.api_key'] = {"widget": vision_api_key, "type": "passwordlineedit"}
        vision_form.addRow("视觉模型API Key:", vision_api_key)
        
        # 视觉模型API URL
        vision_api_url = LineEdit()
        vision_api_url.setText(self.config_data.get('vision', {}).get('api_url', ''))
        vision_api_url.setPlaceholderText("如: https://api.openai.com 或其他兼容接口")
        self.widgets['vision.api_url'] = {"widget": vision_api_url, "type": "lineedit"}
        vision_form.addRow("视觉模型API URL:", vision_api_url)
        
        # 视觉模型选择（可编辑下拉 + 获取按钮）
        vision_model_row = QHBoxLayout()
        self.vision_model_combo = QComboBox()
        self.vision_model_combo.setEditable(True)
        vision_model_val = self.config_data.get('vision', {}).get('model', 'gpt-4-vision-preview')
        if vision_model_val:
            self.vision_model_combo.setEditText(str(vision_model_val))
        vision_fetch_btn = QPushButton('获取模型')
        vision_fetch_btn.clicked.connect(lambda: self._on_click_fetch_models(
            api_url_key='vision.api_url', api_key_key='vision.api_key', combo=self.vision_model_combo, btn=vision_fetch_btn
        ))
        vision_model_row.addWidget(self.vision_model_combo)
        vision_model_row.addWidget(vision_fetch_btn)
        vision_row_container = QWidget()
        vision_row_container.setLayout(vision_model_row)
        vision_form.addRow('视觉模型:', vision_row_container)
        self.widgets['vision.model'] = {"widget": self.vision_model_combo, "type": "combobox"}
        
        # 视觉识别提示词
        vision_prompt = QTextEdit()
        vision_prompt.setPlainText(self.config_data.get('vision', {}).get('system_prompt', '请仔细观察这张图片，描述你看到的内容。重点关注图片中的文字、物体、人物、场景等关键信息。'))
        vision_prompt.setMinimumHeight(80)
        vision_prompt.setPlaceholderText("视觉识别时使用的提示词，用于指导AI如何分析图片")
        self.widgets['vision.system_prompt'] = {"widget": vision_prompt, "type": "textedit"}
        vision_form.addRow("视觉识别提示词:", vision_prompt)
        
        # 只在不支持视觉的LLM下使用
        vision_fallback_check = CheckBox()
        vision_fallback_check.setChecked(bool(self.config_data.get('vision', {}).get('fallback_only', True)))
        self.widgets['vision.fallback_only'] = {"widget": vision_fallback_check, "type": "checkbox"}
        vision_form.addRow("仅在主LLM不支持视觉时使用:", vision_fallback_check)
        
        self.vBoxLayout.addWidget(vision_group)

        # 视觉测试组
        vision_test_group = QGroupBox("视觉功能测试")
        vision_test_form = QFormLayout(vision_test_group)
        
        # 测试按钮和说明
        vision_test_button = PushButton("测试视觉识别 (从剪贴板/文件)")
        vision_test_button.clicked.connect(self._test_vision_recognition)
        vision_test_form.addRow("", vision_test_button)
        
        # 添加说明文字
        vision_help_label = QLabel("使用方法：\n1. 复制图片到剪贴板，或准备好图片文件\n2. 点击测试按钮\n3. 如果剪贴板没有图片，会弹出文件选择框")
        vision_help_label.setWordWrap(True)
        vision_help_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        vision_test_form.addRow("", vision_help_label)
        
        self.vBoxLayout.addWidget(vision_test_group)

        # 同声传译配置
        trans_group = QGroupBox("同声传译设置")
        trans_form = QFormLayout(trans_group)

        # 开关
        trans_enable = CheckBox()
        trans_enable.setChecked(bool(self.config_data.get('translation', {}).get('enabled', False)))
        self.widgets['translation.enabled'] = {"widget": trans_enable, "type": "checkbox"}
        trans_form.addRow("启动同声传译（外语音频播放，中文字幕显示）", trans_enable)

        # API KEY（密码框）
        trans_key = PasswordLineEdit()
        trans_key.setText(self.config_data.get('translation', {}).get('api_key', ''))
        self.widgets['translation.api_key'] = {"widget": trans_key, "type": "passwordlineedit"}
        trans_form.addRow("同传API KEY:", trans_key)

        # API URL
        trans_url = LineEdit()
        trans_url.setText(self.config_data.get('translation', {}).get('api_url', ''))
        self.widgets['translation.api_url'] = {"widget": trans_url, "type": "lineedit"}
        trans_form.addRow("同传API URL:", trans_url)

        # 模型（可编辑下拉 + 获取按钮）
        self.trans_model_combo = QComboBox()
        self.trans_model_combo.setEditable(True)
        trans_model_val = self.config_data.get('translation', {}).get('model', '') if isinstance(self.config_data, dict) else ''
        if trans_model_val:
            self.trans_model_combo.setEditText(str(trans_model_val))
        trans_fetch_btn = QPushButton('获取模型')
        trans_fetch_btn.clicked.connect(lambda: self._on_click_fetch_models(
            api_url_key='translation.api_url', api_key_key='translation.api_key', combo=self.trans_model_combo, btn=trans_fetch_btn
        ))
        trow = QHBoxLayout()
        trow.addWidget(self.trans_model_combo)
        trow.addWidget(trans_fetch_btn)
        trow_container = QWidget()
        trow_container.setLayout(trow)
        trans_form.addRow("同传模型:", trow_container)
        # 注册
        self.widgets['translation.model'] = {"widget": self.trans_model_combo, "type": "combobox"}

        # 提示词（多行）
        trans_prompt = QTextEdit()
        trans_prompt.setPlainText(self.config_data.get('translation', {}).get('system_prompt', ''))
        trans_prompt.setMinimumHeight(80)
        self.widgets['translation.system_prompt'] = {"widget": trans_prompt, "type": "textedit"}
        trans_form.addRow("同传模型人设:", trans_prompt)

        self.vBoxLayout.addWidget(trans_group)
        self.vBoxLayout.addStretch()

    # ====== 模型获取：通用逻辑 ======
    def _on_click_fetch_models(self, api_url_key: str, api_key_key: str, combo: QComboBox, btn: QPushButton):
        # 读取对应的 URL/KEY 控件值
        api_url_widget = self.widgets.get(api_url_key, {}).get('widget')
        api_key_widget = self.widgets.get(api_key_key, {}).get('widget')
        api_url = api_url_widget.text().strip() if api_url_widget else ''
        api_key = api_key_widget.text().strip() if api_key_widget else ''
        
        # 获取API类型（仅LLM标签页有此设置）
        api_type = "OpenAI兼容API"  # 默认值
        if hasattr(self, 'api_type_combo'):
            api_type = self.api_type_combo.currentText()
        
        if not api_url:
            InfoBar.warning(title='缺少 API URL', content='请先填写 API URL', orient=Qt.Horizontal,
                            isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
            return
        try:
            btn.setEnabled(False)
            prev_text = combo.currentText().strip()
            worker = ModelFetchWorker(api_url, api_key, api_type, parent=self)
            self._model_fetchers.append(worker)
            def on_success(models: list):
                self._populate_model_combo(combo, models, prev_text)
                InfoBar.success(title='获取成功', content=f'共获取到 {len(models)} 个模型', orient=Qt.Horizontal,
                                isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
                btn.setEnabled(True)
                if worker in self._model_fetchers:
                    self._model_fetchers.remove(worker)
            def on_error(msg: str):
                InfoBar.error(title='获取失败', content=msg, orient=Qt.Horizontal,
                              isClosable=True, position=InfoBarPosition.TOP, duration=4000, parent=self)
                btn.setEnabled(True)
                if worker in self._model_fetchers:
                    self._model_fetchers.remove(worker)
            worker.success.connect(on_success)
            worker.error.connect(on_error)
            worker.start()
        except Exception as e:
            btn.setEnabled(True)
            InfoBar.error(title='异常', content=str(e), orient=Qt.Horizontal,
                          isClosable=True, position=InfoBarPosition.TOP, duration=4000, parent=self)

    def _populate_model_combo(self, combo: QComboBox, models: list, prev_text: str):
        try:
            prev = prev_text or combo.currentText().strip()
            combo.blockSignals(True)
            combo.clear()
            for m in models:
                combo.addItem(m, m)
            if prev and prev in models:
                idx = models.index(prev)
                combo.setCurrentIndex(idx)
            elif prev:
                combo.setEditText(prev)
        finally:
            combo.blockSignals(False)

    def create_asr_tab(self):
        """创建ASR配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # ASR类型选择组
        asr_type_group = QGroupBox("ASR类型配置")
        asr_type_form = QFormLayout(asr_type_group)
        
        # ASR类型下拉选择
        self.asr_type_combo = QComboBox()
        self.asr_type_combo.addItems(["本地ASR", "豆包语音识别", "Fish Audio"])
        current_asr_type = self.config_data.get('asr', {}).get('asr_type', '本地ASR')
        index = self.asr_type_combo.findText(current_asr_type)
        if index >= 0:
            self.asr_type_combo.setCurrentIndex(index)
        self.widgets['asr.asr_type'] = {"widget": self.asr_type_combo, "type": "combobox"}
        asr_type_form.addRow("ASR类型:", self.asr_type_combo)
        
        # ASR日志开关
        asr_log_enabled_check = CheckBox()
        asr_log_enabled_check.setChecked(bool(self.config_data.get('asr', {}).get('log_enabled', True)))
        self.widgets['asr.log_enabled'] = {"widget": asr_log_enabled_check, "type": "checkbox"}
        asr_type_form.addRow("启用ASR日志:", asr_log_enabled_check)
        
        # ASR日志文件路径
        asr_log_path_edit = LineEdit()
        asr_log_path_edit.setText(self.config_data.get('asr', {}).get('log_path', 'logs/asr_interactions.log'))
        asr_log_path_edit.setPlaceholderText("ASR日志文件保存路径")
        self.widgets['asr.log_path'] = {"widget": asr_log_path_edit, "type": "lineedit"}
        asr_type_form.addRow("ASR日志文件路径:", asr_log_path_edit)
        
        self.vBoxLayout.addWidget(asr_type_group)
        
        # 本地ASR配置组
        local_asr_group = QGroupBox("本地ASR配置")
        local_asr_form = QFormLayout(local_asr_group)
        
        local_asr_fields = [
            ("VAD URL", "asr.vad_url", "lineedit", "ws://127.0.0.1:1000/v1/ws/vad"),
            ("ASR URL", "asr.asr_url", "lineedit", "http://127.0.0.1:1000/v1/upload_audio")
        ]
        
        for label, key_path, widget_type, default in local_asr_fields:
            widget = self.create_widget(widget_type, key_path, default)
            local_asr_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(local_asr_group)
        
        # 豆包语音识别配置组
        doubao_asr_group = QGroupBox("豆包语音识别配置")
        doubao_asr_form = QFormLayout(doubao_asr_group)
        
        # 豆包ASR基础配置
        doubao_asr_fields = [
            ("APP ID (X-Api-App-Key)", "asr.doubao_app_key", "lineedit", ""),
            ("Access Token (X-Api-Access-Key)", "asr.doubao_access_key", "passwordlineedit", ""),
            ("Resource ID", "asr.doubao_resource_id", "lineedit", "volc.bigasr.sauc.duration"),
            ("音频包大小(ms)", "asr.doubao_packet_size", "spinbox", 200),
            ("连接超时(秒)", "asr.doubao_timeout", "spinbox", 30)
        ]
        
        for label, key_path, widget_type, default in doubao_asr_fields:
            widget = self.create_widget(widget_type, key_path, default)
            doubao_asr_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(doubao_asr_group)
        
        # Fish Audio ASR配置组
        fish_audio_asr_group = QGroupBox("Fish Audio ASR配置")
        fish_audio_asr_form = QFormLayout(fish_audio_asr_group)
        
        # Fish Audio ASR基础配置
        fish_audio_asr_fields = [
            ("API Key", "asr.fish_audio_api_key", "passwordlineedit", ""),
            ("语言", "asr.fish_audio_language", "lineedit", "zh"),
            ("忽略时间戳", "asr.fish_audio_ignore_timestamps", "checkbox", True)
        ]
        
        for label, key_path, widget_type, default in fish_audio_asr_fields:
            widget = self.create_widget(widget_type, key_path, default)
            fish_audio_asr_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(fish_audio_asr_group)
        
        # ASR测试区域
        test_group = QGroupBox("ASR测试")
        test_form = QFormLayout(test_group)
        
        # 测试按钮
        test_layout = QHBoxLayout()
        
        test_local_btn = PushButton("测试本地ASR")
        test_local_btn.clicked.connect(self.test_local_asr)
        test_layout.addWidget(test_local_btn)
        
        test_doubao_btn = PushButton("测试豆包ASR连接")
        test_doubao_btn.clicked.connect(self.test_doubao_asr)
        test_layout.addWidget(test_doubao_btn)
        
        test_fish_audio_btn = PushButton("测试Fish Audio ASR")
        test_fish_audio_btn.clicked.connect(self.test_fish_audio_asr)
        test_layout.addWidget(test_fish_audio_btn)
        
        test_container = QWidget()
        test_container.setLayout(test_layout)
        test_form.addRow("连接测试:", test_container)
        
        self.vBoxLayout.addWidget(test_group)
        self.vBoxLayout.addStretch()
    
    def test_local_asr(self):
        """测试本地ASR连接"""
        asr_config = self.config_data.get('asr', {})
        vad_url = asr_config.get('vad_url', '')
        asr_url = asr_config.get('asr_url', '')
        
        if not vad_url and not asr_url:
            InfoBar.warning(
                title='配置缺失',
                content="请先配置VAD URL或ASR URL",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 记录测试日志
        self.log_asr_system_event("开始测试本地ASR连接")
        
        try:
            import requests
            
            # 测试VAD URL
            if vad_url:
                response = requests.get(vad_url, timeout=5)
                if response.status_code == 200:
                    self.log_asr_system_event(f"VAD URL连接成功: {vad_url}")
                else:
                    self.log_asr_error("VAD连接失败", f"状态码: {response.status_code}")
            
            # 测试ASR URL
            if asr_url:
                response = requests.get(asr_url, timeout=5)
                if response.status_code == 200:
                    self.log_asr_system_event(f"ASR URL连接成功: {asr_url}")
                else:
                    self.log_asr_error("ASR连接失败", f"状态码: {response.status_code}")
            
            InfoBar.success(
                title='测试完成',
                content="本地ASR连接测试完成，请查看日志",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
        except Exception as e:
            self.log_asr_error("连接测试异常", str(e))
            InfoBar.error(
                title='测试失败',
                content=f"连接测试失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
    
    def test_doubao_asr(self):
        """测试豆包ASR连接"""
        asr_config = self.config_data.get('asr', {})
        
        # 检查必要配置
        app_key = asr_config.get('doubao_app_key', '')
        access_key = asr_config.get('doubao_access_key', '')
        
        if not app_key or not access_key:
            InfoBar.warning(
                title='配置缺失',
                content="请先配置豆包ASR的APP ID和Access Token",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 记录测试日志
        self.log_asr_system_event("开始测试豆包ASR连接")
        
        try:
            # 创建豆包ASR客户端进行连接测试
            client = DoubaoASRClient(asr_config, self.asr_logger)
            
            # 获取连接信息
            url = client.get_websocket_url()
            headers = client.get_headers()
            
            self.log_doubao_request(
                asr_config.get('doubao_mode', '双向流式模式（优化版本）'),
                asr_config.get('doubao_packet_size', 200),
                headers.get('X-Api-Connect-Id', 'unknown')
            )
            
            InfoBar.success(
                title='配置验证',
                content=f"豆包ASR配置验证完成\n模式: {asr_config.get('doubao_mode', '双向流式模式（优化版本）')}\nURL: {url}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            
            self.log_asr_system_event("豆包ASR配置验证完成")
            
        except Exception as e:
            self.log_asr_error("豆包ASR配置验证失败", str(e))
            InfoBar.error(
                title='验证失败',
                content=f"豆包ASR配置验证失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )

    def test_fish_audio_asr(self):
        """测试Fish Audio ASR配置"""
        asr_config = self.config_data.get('asr', {})
        
        # 检查必要配置
        api_key = asr_config.get('fish_audio_api_key', '')
        
        if not api_key:
            InfoBar.warning(
                title='配置缺失',
                content="请先配置Fish Audio ASR的API Key",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 记录测试日志
        self.log_asr_system_event("开始测试Fish Audio ASR配置")
        
        try:
            # 测试Fish Audio SDK导入和初始化
            from fish_audio_sdk import Session, ASRRequest
            
            session = Session(api_key)
            
            # 创建一个简单的测试请求（不发送实际音频）
            test_request = ASRRequest(
                audio=b"test",  # 虚拟音频数据
                language=asr_config.get('fish_audio_language', 'zh'),
                ignore_timestamps=asr_config.get('fish_audio_ignore_timestamps', True)
            )
            
            InfoBar.success(
                title='配置验证',
                content=f"Fish Audio ASR配置验证完成\n语言: {asr_config.get('fish_audio_language', 'zh')}\n忽略时间戳: {asr_config.get('fish_audio_ignore_timestamps', True)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            
            self.log_asr_system_event("Fish Audio ASR配置验证完成")
            
        except ImportError as e:
            self.log_asr_error("Fish Audio SDK未安装", str(e))
            InfoBar.error(
                title='SDK缺失',
                content="Fish Audio SDK未安装，请运行: uv add fish-audio-sdk",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
        except Exception as e:
            self.log_asr_error("Fish Audio ASR配置验证失败", str(e))
            InfoBar.error(
                title='验证失败',
                content=f"Fish Audio ASR配置验证失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )

    def create_widget(self, widget_type, key_path, default):
        """创建指定类型的控件"""
        keys = key_path.split('.')
        config_value = self.config_data
        for key in keys:
            config_value = config_value.get(key, {}) if isinstance(config_value, dict) else {}
        
        # 处理兼容性问题
        if not config_value:
            # 处理TTS URL兼容性：如果tts.local_url为空，尝试使用tts.url
            if key_path == "tts.local_url":
                legacy_url = self.config_data.get('tts', {}).get('url', '')
                if legacy_url:
                    config_value = legacy_url
            # 处理ASR URL兼容性：如果asr.vad_url为空，保持现有配置
            elif key_path == "asr.vad_url":
                legacy_vad = self.config_data.get('asr', {}).get('vad_url', '')
                if legacy_vad:
                    config_value = legacy_vad
            # 处理ASR URL兼容性：如果asr.asr_url为空，保持现有配置
            elif key_path == "asr.asr_url":
                legacy_asr = self.config_data.get('asr', {}).get('asr_url', '')
                if legacy_asr:
                    config_value = legacy_asr
        
        if widget_type == "lineedit":
            widget = LineEdit()
            widget.setText(str(config_value) if config_value else str(default))
        elif widget_type == "passwordlineedit":
            widget = PasswordLineEdit()
            widget.setText(str(config_value) if config_value else str(default))
        elif widget_type == "spinbox":
            widget = SpinBox()
            widget.setRange(0, 99999)
            widget.setValue(int(config_value) if config_value else int(default))
        elif widget_type == "checkbox":
            widget = CheckBox()
            widget.setChecked(bool(config_value) if config_value is not None else bool(default))
        elif widget_type == "doublespin":
            widget = DoubleSpinBox()
            widget.setRange(0.0, 99999.0)
            widget.setValue(float(config_value) if config_value else float(default))
        else:
            widget = LineEdit()
            widget.setText(str(config_value) if config_value else str(default))
        
        return widget

    def create_tts_tab(self):
        """创建TTS配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # TTS类型选择组
        tts_type_group = QGroupBox("TTS类型配置")
        tts_type_form = QFormLayout(tts_type_group)
        
        # TTS类型下拉选择
        self.tts_type_combo = QComboBox()
        self.tts_type_combo.addItems(["本地TTS", "豆包TTS", "Fish Audio"])
        current_tts_type = self.config_data.get('tts', {}).get('tts_type', '本地TTS')
        index = self.tts_type_combo.findText(current_tts_type)
        if index >= 0:
            self.tts_type_combo.setCurrentIndex(index)
        self.widgets['tts.tts_type'] = {"widget": self.tts_type_combo, "type": "combobox"}
        tts_type_form.addRow("TTS类型:", self.tts_type_combo)
        
        # TTS日志开关
        tts_log_enabled_check = CheckBox()
        tts_log_enabled_check.setChecked(bool(self.config_data.get('tts', {}).get('log_enabled', True)))
        self.widgets['tts.log_enabled'] = {"widget": tts_log_enabled_check, "type": "checkbox"}
        tts_type_form.addRow("启用TTS日志:", tts_log_enabled_check)
        
        # TTS日志文件路径
        tts_log_path_edit = LineEdit()
        tts_log_path_edit.setText(self.config_data.get('tts', {}).get('log_path', 'logs/tts_interactions.log'))
        tts_log_path_edit.setPlaceholderText("TTS日志文件保存路径")
        self.widgets['tts.log_path'] = {"widget": tts_log_path_edit, "type": "lineedit"}
        tts_type_form.addRow("TTS日志文件路径:", tts_log_path_edit)
        
        self.vBoxLayout.addWidget(tts_type_group)
        
        # 本地TTS配置组
        local_tts_group = QGroupBox("本地TTS配置")
        local_tts_form = QFormLayout(local_tts_group)
        
        local_tts_fields = [
            ("TTS URL", "tts.local_url", "lineedit", "http://127.0.0.1:5000"),
            ("语言", "tts.language", "lineedit", "zh"),
            ("音色", "tts.voice", "lineedit", ""),
            ("语速", "tts.speed", "doublespin", 1.0),
            ("音量", "tts.volume", "doublespin", 1.0)
        ]
        
        for label, key_path, widget_type, default in local_tts_fields:
            widget = self.create_widget(widget_type, key_path, default)
            if widget_type == "doublespin":
                widget.setRange(0.1, 3.0)
                widget.setSingleStep(0.1)
            local_tts_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(local_tts_group)
        
        # 豆包TTS配置组
        doubao_tts_group = QGroupBox("豆包TTS配置")
        doubao_tts_form = QFormLayout(doubao_tts_group)
        
        # 豆包TTS基础配置
        # 豆包TTS音色列表 - 音色名称作为key，voice_type作为value
        doubao_voice_types = {
            # 多情感场景
            "北京小爷（多情感）": "zh_male_beijingxiaoye_emo_v2_mars_bigtts",
            "柔美女友（多情感）": "zh_female_roumeinvyou_emo_v2_mars_bigtts",
            "阳光青年（多情感）": "zh_male_yangguangqingnian_emo_v2_mars_bigtts",
            "魅力女友（多情感）": "zh_female_meilinvyou_emo_v2_mars_bigtts",
            "爽快思思（多情感）": "zh_female_shuangkuaisisi_emo_v2_mars_bigtts",
            "甜心小美（多情感）": "zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
            "高冷御姐（多情感）": "zh_female_gaolengyujie_emo_v2_mars_bigtts",
            "傲娇霸总（多情感）": "zh_male_aojiaobazong_emo_v2_mars_bigtts",
            "广州德哥（多情感）": "zh_male_guangzhoudege_emo_mars_bigtts",
            "京腔侃爷（多情感）": "zh_male_jingqiangkanye_emo_mars_bigtts",
            "邻居阿姨（多情感）": "zh_female_linjuayi_emo_v2_mars_bigtts",
            "优柔公子（多情感）": "zh_male_yourougongzi_emo_v2_mars_bigtts",
            "儒雅男友（多情感）": "zh_male_ruyayichen_emo_v2_mars_bigtts",
            "俊朗男友（多情感）": "zh_male_junlangnanyou_emo_v2_mars_bigtts",
            "冷酷哥哥（多情感）": "zh_male_lengkugege_emo_v2_mars_bigtts",
            "Glen": "en_male_glen_emo_v2_mars_bigtts",
            "Sylus": "en_male_sylus_emo_v2_mars_bigtts",
            "Candice": "en_female_candice_emo_v2_mars_bigtts",
            "Corey": "en_male_corey_emo_v2_mars_bigtts",
            "Nadia": "en_female_nadia_tips_emo_v2_mars_bigtts",
            "Serena": "en_female_skye_emo_v2_mars_bigtts",
            
            # 教育场景
            "Tina老师": "zh_female_yingyujiaoyu_mars_bigtts",
            
            # 客服场景
            "暖阳女声": "zh_female_kefunvsheng_mars_bigtts",
            "甜美小雨": "ICL_zh_female_tianmeixiaoyu_cs_tob",
            "热情艾娜": "ICL_zh_female_reqingaina_cs_tob",
            "甜美小橘": "ICL_zh_female_tianmeixiaoju_cs_tob",
            "沉稳明仔": "ICL_zh_male_chenwenmingzai_cs_tob",
            "亲切小卓": "ICL_zh_male_qinqiexiaozhuo_cs_tob",
            "灵动欣欣": "ICL_zh_female_lingdongxinxin_cs_tob",
            "乖巧可儿": "ICL_zh_female_guaiqiaokeer_cs_tob",
            "暖心茜茜": "ICL_zh_female_nuanxinqianqian_cs_tob",
            "软萌团子": "ICL_zh_female_ruanmengtuanzi_cs_tob",
            "阳光洋洋": "ICL_zh_male_yangguangyangyang_cs_tob",
            "软萌糖糖": "ICL_zh_female_ruanmengtangtang_cs_tob",
            "秀丽倩倩": "ICL_zh_female_xiuliqianqian_cs_tob",
            "开心小鸿": "ICL_zh_female_kaixinxiaohong_cs_tob",
            "轻盈朵朵": "ICL_zh_female_qingyingduoduo_cs_tob",
            "理性圆子": "ICL_zh_female_lixingyuanzi_cs_tob",
            "清甜桃桃": "ICL_zh_female_qingtiantaotao_cs_tob",
            "清晰小雪": "ICL_zh_female_qingxixiaoxue_cs_tob",
            "清甜莓莓": "ICL_zh_female_qingtianmeimei_cs_tob",
            "开朗婷婷": "ICL_zh_female_kailangtingting_cs_tob",
            "清新沐沐": "ICL_zh_male_qingxinmumu_cs_tob",
            "爽朗小阳": "ICL_zh_male_shuanglangxiaoyang_cs_tob",
            "清新波波": "ICL_zh_male_qingxinbobo_cs_tob",
            "温婉珊珊": "ICL_zh_female_wenwanshanshan_cs_tob",
            
            # 通用场景
            "甜美桃子": "zh_female_tianmeitaozi_mars_bigtts",
            "Vivi": "zh_female_vv_mars_bigtts",
            "温柔女神": "ICL_zh_female_wenrounvshen_239eff5e8ffa_tob",
            "灿灿/Shiny": "zh_female_cancan_mars_bigtts",
            "清新女声": "zh_female_qingxinnvsheng_mars_bigtts",
            "爽快思思/Skye": "zh_female_shuangkuaisisi_moon_bigtts",
            "温暖阿虎/Alvin": "zh_male_wennuanahu_moon_bigtts",
            "少年梓辛/Brayan": "zh_male_shaonianzixin_moon_bigtts",
            "知性女声": "zh_female_zhixingnvsheng_mars_bigtts",
            "清爽男大": "zh_male_qingshuangnanda_mars_bigtts",
            "邻家女孩": "zh_female_linjianvhai_moon_bigtts",
            "渊博小叔": "zh_male_yuanboxiaoshu_moon_bigtts",
            "阳光青年": "zh_male_yangguangqingnian_moon_bigtts",
            "甜美小源": "zh_female_tianmeixiaoyuan_moon_bigtts",
            "清澈梓梓": "zh_female_qingchezizi_moon_bigtts",
            "解说小明": "zh_male_jieshuoxiaoming_moon_bigtts",
            "开朗姐姐": "zh_female_kailangjiejie_moon_bigtts",
            "邻家男孩": "zh_male_linjiananhai_moon_bigtts",
            "甜美悦悦": "zh_female_tianmeiyueyue_moon_bigtts",
            "心灵鸡汤": "zh_female_xinlingjitang_moon_bigtts",
            "知性温婉": "ICL_zh_female_zhixingwenwan_tob",
            "暖心体贴": "ICL_zh_male_nuanxintitie_tob",
            "温柔文雅": "ICL_zh_female_wenrouwenya_tob",
            "开朗轻快": "ICL_zh_male_kailangqingkuai_tob",
            "活泼爽朗": "ICL_zh_male_huoposhuanglang_tob",
            "率真小伙": "ICL_zh_male_shuaizhenxiaohuo_tob",
            "温柔小哥": "zh_male_wenrouxiaoge_mars_bigtts",
            "亲切女声": "zh_female_qinqienvsheng_moon_bigtts",
            "机灵小伙": "ICL_zh_male_shenmi_v1_tob",
            "元气甜妹": "ICL_zh_female_wuxi_tob",
            "知心姐姐": "ICL_zh_female_wenyinvsheng_v1_tob",
            "阳光阿辰": "zh_male_qingyiyuxuan_mars_bigtts",
            "快乐小东": "zh_male_xudong_conversation_wvae_bigtts",
            "冷酷哥哥": "ICL_zh_male_lengkugege_v1_tob",
            "纯澈女生": "ICL_zh_female_feicui_v1_tob",
            "初恋女友": "ICL_zh_female_yuxin_v1_tob",
            "贴心闺蜜": "ICL_zh_female_xnx_tob",
            "温柔白月光": "ICL_zh_female_yry_tob",
            "开朗学长": "en_male_jason_conversation_wvae_bigtts",
            "魅力苏菲": "zh_female_sophie_conversation_wvae_bigtts",
            "贴心妹妹": "ICL_zh_female_yilin_tob",
            
            # 多语种
            "Lauren": "en_female_lauren_moon_bigtts",
            "Smith": "en_male_smith_mars_bigtts",
            "Anna": "en_female_anna_mars_bigtts",
            "Adam": "en_male_adam_mars_bigtts",
            "Sarah": "en_female_sarah_mars_bigtts",
            "Dryw": "en_male_dryw_mars_bigtts",
            "かずね（和音）/Javier or Álvaro": "multi_male_jingqiangkanye_moon_bigtts",
            "はるこ（晴子）/Esmeralda": "multi_female_shuangkuaisisi_moon_bigtts",
            "ひろし（広志）/Roberto": "multi_male_wanqudashu_moon_bigtts",
            "あけみ（朱美）": "multi_female_gaolengyujie_moon_bigtts",
            "Amanda": "en_female_amanda_mars_bigtts",
            "Jackson": "en_male_jackson_mars_bigtts",
            "Cartoon Chef": "ICL_en_male_cc_sha_v1_tob",
            "ひかる（光）": "multi_zh_male_youyoujunzi_moon_bigtts",
            "Emily": "en_female_emily_mars_bigtts",
            "Daniel": "zh_male_xudong_conversation_wvae_bigtts",
            "Lucas": "zh_male_M100_conversation_wvae_bigtts",
            "Diana": "multi_female_maomao_conversation_wvae_bigtts",
            "Lucía": "multi_male_M100_conversation_wvae_bigtts",
            "Sofía": "multi_female_sophie_conversation_wvae_bigtts",
            "Daníel": "multi_male_xudong_conversation_wvae_bigtts",
            "さとみ（智美）": "multi_female_sophie_conversation_wvae_bigtts",
            "まさお（正男）": "multi_male_xudong_conversation_wvae_bigtts",
            "つき（月）": "multi_female_maomao_conversation_wvae_bigtts",
            "Sophie": "zh_female_sophie_conversation_wvae_bigtts",
            "Daisy": "en_female_dacey_conversation_wvae_bigtts",
            "Owen": "en_male_charlie_conversation_wvae_bigtts",
            "Ethan": "ICL_en_male_aussie_v1_tob",
            "Luna": "en_female_sarah_new_conversation_wvae_bigtts",
            "Michael": "ICL_en_male_michael_tob",
            "Alastor": "ICL_en_male_cc_alastor_tob",
            "Charlie": "ICL_en_female_cc_cm_v1_tob",
            "Big Boogie": "ICL_en_male_oogie2_tob",
            "Frosty Man": "ICL_en_male_frosty1_tob",
            "The Grinch": "ICL_en_male_grinch2_tob",
            "Zayne": "ICL_en_male_zayne_tob",
            "Jigsaw": "ICL_en_male_cc_jigsaw_tob",
            "Chucky": "ICL_en_male_cc_chucky_tob",
            "Clown Man": "ICL_en_male_cc_penny_v1_tob",
            "Kevin McCallister": "ICL_en_male_kevin2_tob",
            "Xavier": "ICL_en_male_xavier1_v1_tob",
            "Noah": "ICL_en_male_cc_dracula_v1_tob",
            "Energetic Male II": "en_male_campaign_jamal_moon_bigtts",
            "Gotham Hero": "en_male_chris_moon_bigtts",
            "Delicate Girl": "en_female_daisy_moon_bigtts",
            "Flirty Female": "en_female_product_darcie_moon_bigtts",
            "Peaceful Female": "en_female_emotional_moon_bigtts",
            "Nara": "en_female_nara_moon_bigtts",
            "Candice": "en_female_candice_emo_v2_mars_bigtts",
            "Corey": "en_male_corey_emo_v2_mars_bigtts",
            "Nadia1": "en_female_nadia_tips_emo_v2_mars_bigtts",
            "Serena": "en_female_skye_emo_v2_mars_bigtts",
            "Bruce": "en_male_bruce_moon_bigtts",
            "Dave": "en_male_dave_moon_bigtts",
            "Michael": "en_male_michael_moon_bigtts",
            "Hades": "en_male_hades_moon_bigtts",
            "Onez": "en_female_onez_moon_bigtts",
            "Glen": "en_male_glen_emo_v2_mars_bigtts",
            "Nadia2": "en_female_nadia_poetry_emo_v2_mars_bigtts",
            "Sylus": "en_male_sylus_emo_v2_mars_bigtts",
            
            # 趣味口音
            "京腔侃爷/Harmony": "zh_male_jingqiangkanye_moon_bigtts",
            "湾湾小何": "zh_female_wanwanxiaohe_moon_bigtts",
            "湾区大叔": "zh_female_wanqudashu_moon_bigtts",
            "呆萌川妹": "zh_female_daimengchuanmei_moon_bigtts",
            "广州德哥": "zh_male_guozhoudege_moon_bigtts",
            "北京小爷": "zh_male_beijingxiaoye_moon_bigtts",
            "浩宇小哥": "zh_male_haoyuxiaoge_moon_bigtts",
            "广西远舟": "zh_male_guangxiyuanzhou_moon_bigtts",
            "妹坨洁儿": "zh_female_meituojieer_moon_bigtts",
            "豫州子轩": "zh_male_yuzhouzixuan_moon_bigtts",
            
            # 角色扮演
            "黯刃秦主": "ICL_zh_male_anrenqinzhu_cd62e63dcdab_tob",
            "纯真少女": "ICL_zh_female_chunzhenshaonv_e588402fb8ad_tob",
            "奶气小生": "ICL_zh_male_xiaonaigou_edf58cf28b8b_tob",
            "精灵向导": "ICL_zh_female_jinglingxiangdao_1beb294a9e3e_tob",
            "闷油瓶小哥": "ICL_zh_male_menyoupingxiaoge_ffed9fc2fee7_tob",
            "奶气萌娃": "zh_male_naiqimengwa_mars_bigtts",
            "婆婆": "zh_female_popo_mars_bigtts",
            "高冷御姐": "zh_female_gaolengyujie_moon_bigtts",
            "傲娇霸总": "zh_male_aojiaobazong_moon_bigtts",
            "魅力女友": "zh_female_meilinvyou_moon_bigtts",
            "深夜播客": "zh_male_shenyeboke_moon_bigtts",
            "柔美女友": "zh_female_sajiaonvyou_moon_bigtts",
            "撒娇学妹": "zh_female_yuanqinvyou_moon_bigtts",
            "病弱少女": "ICL_zh_female_bingruoshaonv_tob",
            "活泼女孩": "ICL_zh_female_huoponvhai_tob",
            "东方浩然": "zh_male_dongfanghaoran_moon_bigtts",
            "绿茶小哥": "ICL_zh_male_lvchaxiaoge_tob",
            "娇弱萝莉": "ICL_zh_female_jiaoruoluoli_tob",
            "冷淡疏离": "ICL_zh_male_lengdanshuli_tob",
            "憨厚敦实": "ICL_zh_male_hanhoudunshi_tob",
            "傲气凌人": "ICL_zh_male_aiqilingren_tob",
            "活泼刁蛮": "ICL_zh_female_huopodiaoman_tob",
            "固执病娇": "ICL_zh_male_guzhibingjiao_tob",
            "撒娇粘人": "ICL_zh_male_sajiaonianren_tob",
            "傲慢娇声": "ICL_zh_female_aomanjiaosheng_tob",
            "潇洒随性": "ICL_zh_male_xiaosasuixing_tob",
            "腹黑公子": "ICL_zh_male_fuheigongzi_tob",
            "诡异神秘": "ICL_zh_male_guiyishenmi_tob",
            "儒雅才俊": "ICL_zh_male_ruyacaijun_tob",
            "病娇白莲": "ICL_zh_male_bingjiaobailian_tob",
            "正直青年": "ICL_zh_male_zhengzhiqingnian_tob",
            "娇憨女王": "ICL_zh_female_jiaohannvwang_tob",
            "病娇萌妹": "ICL_zh_female_bingjiaomengmei_tob",
            "青涩小生": "ICL_zh_male_qingsenaigou_tob",
            "纯真学弟": "ICL_zh_male_chunzhenxuedi_tob",
            "暖心学姐": "ICL_zh_female_nuanxinxuejie_tob",
            "可爱女生": "ICL_zh_female_keainvsheng_tob",
            "成熟姐姐": "ICL_zh_female_chengshujiejie_tob",
            "病娇姐姐": "ICL_zh_female_bingjiaojiejie_tob",
            "优柔帮主": "ICL_zh_male_youroubangzhu_tob",
            "优柔公子": "ICL_zh_male_yourougongzi_tob",
            "妩媚御姐": "ICL_zh_female_wumeiyujie_tob",
            "调皮公主": "ICL_zh_female_tiaopigongzhu_tob",
            "傲娇女友": "ICL_zh_female_aojiaonvyou_tob",
            "贴心男友": "ICL_zh_male_tiexinnanyou_tob",
            "少年将军": "ICL_zh_male_shaonianjiangjun_tob",
            "贴心女友": "ICL_zh_female_tiexinnvyou_tob",
            "病娇哥哥": "ICL_zh_male_bingjiaogege_tob",
            "学霸男同桌": "ICL_zh_male_xuebanantongzhuo_tob",
            "幽默叔叔": "ICL_zh_male_youmodaye_tob",
            "妩媚可人": "ICL_zh_female_ganli_v1_tob",
            "邪魅御姐": "ICL_zh_female_xiangliangya_v1_tob",
            "性感御姐": "ICL_zh_female_xingganyujie_tob",
            "嚣张小哥": "ICL_zh_male_ms_tob",
            "油腻大叔": "ICL_zh_male_you_tob",
            "孤傲公子": "ICL_zh_male_guaogongzi_v1_tob",
            "胡子叔叔": "ICL_zh_male_huzi_v1_tob",
            "性感魅惑": "ICL_zh_female_luoqing_v1_tob",
            "双节棍小哥": "zh_male_zhoujielun_emo_v2_mars_bigtts",
            "病弱公子": "ICL_zh_male_bingruogongzi_tob",
            "邪魅女王": "ICL_zh_female_bingjiao3_tob",
            "假小子": "ICL_zh_female_jiaxiaozi_tob",
            "冷峻上司": "ICL_zh_male_lengjunshangsi_tob",
            "温柔男同桌": "ICL_zh_male_wenrounantongzhuo_tob",
            "病娇弟弟": "ICL_zh_male_bingjiaodidi_tob",
            "幽默大爷": "ICL_zh_male_youmodaye_tob",
            "傲慢少爷": "ICL_zh_male_aomanshaoye_tob",
            "枕边低语": "ICL_zh_male_asmryexiu_tob",
            "傲慢青年": "ICL_zh_male_aomanqingnian_tob",
            "醋精男友": "ICL_zh_male_cujingnanyou_tob",
            "醋精男生": "ICL_zh_male_cujingnansheng_tob",
            "爽朗少年": "ICL_zh_male_shuanglangshaonian_tob",
            "撒娇男友": "ICL_zh_male_sajiaonanyou_tob",
            "温柔男友": "ICL_zh_male_wenrounanyou_tob",
            "温顺少年": "ICL_zh_male_wenshunshaonian_tob",
            "粘人男友": "ICL_zh_male_naigounanyou_tob",
            "活泼男友": "ICL_zh_male_huoponanyou_tob",
            "甜系男友": "ICL_zh_male_tianxinanyou_tob",
            "活力青年": "ICL_zh_male_huoliqingnian_tob",
            "开朗青年": "ICL_zh_male_kailangqingnian_tob",
            "冷漠兄长": "ICL_zh_male_lengmoxiongzhang_tob",
            "天才同桌": "ICL_zh_male_tiancaitongzhuo_tob",
            "傲娇精英": "ICL_zh_male_aojiaojingying_tob",
            "翩翩公子": "ICL_zh_male_pianpiangongzi_tob",
            "懵懂青年": "ICL_zh_male_mengdongqingnian_tob",
            "冷脸兄长": "ICL_zh_male_lenglianxiongzhang_tob",
            "病娇少年": "ICL_zh_male_bingjiaoshaonian_tob",
            "病娇男友": "ICL_zh_male_bingjiaonanyou_tob",
            "病弱少年": "ICL_zh_male_bingruoshaonian_tob",
            "意气少年": "ICL_zh_male_yiqishaonian_tob",
            "干净少年": "ICL_zh_male_ganjingshaonian_tob",
            "冷漠男友": "ICL_zh_male_lengmonanyou_tob",
            "精英青年": "ICL_zh_male_jingyingqingnian_tob",
            "风发少年": "ICL_zh_male_fengfashaonian_tob",
            "热血少年": "ICL_zh_male_rexueshaonian_tob",
            "清爽少年": "ICL_zh_male_qingshuangshaonian_tob",
            "中二青年": "ICL_zh_male_zhongerqingnian_tob",
            "凌云青年": "ICL_zh_male_lingyunqingnian_tob",
            "自负青年": "ICL_zh_male_zifuqingnian_tob",
            "不羁青年": "ICL_zh_male_bujiqingnian_tob",
            "儒雅君子": "ICL_zh_male_ruyajunzi_tob",
            "低音沉郁": "ICL_zh_male_diyinchenyu_tob",
            "冷脸学霸": "ICL_zh_male_lenglianxueba_tob",
            "儒雅总裁": "ICL_zh_male_ruyazongcai_tob",
            "深沉总裁": "ICL_zh_male_shenchenzongcai_tob",
            "小侯爷": "ICL_zh_male_xiaohouye_tob",
            "孤高公子": "ICL_zh_male_gugaogongzi_tob",
            "仗剑君子": "ICL_zh_male_zhangjianjunzi_tob",
            "温润学者": "ICL_zh_male_wenrunxuezhe_tob",
            "亲切青年": "ICL_zh_male_qinqieqingnian_tob",
            "温柔学长": "ICL_zh_male_wenrouxuezhang_tob",
            "磁性男嗓": "ICL_zh_male_cixingnansang_tob",
            "高冷总裁": "ICL_zh_male_gaolengzongcai_tob",
            "冷峻高智": "ICL_zh_male_lengjungaozhi_tob",
            "孱弱少爷": "ICL_zh_male_chanruoshaoye_tob",
            "自信青年": "ICL_zh_male_zixinqingnian_tob",
            "青涩青年": "ICL_zh_male_qingseqingnian_tob",
            "学霸同桌": "ICL_zh_male_xuebatongzhuo_tob",
            "冷傲总裁": "ICL_zh_male_lengaozongcai_tob",
            "霸道少爷": "ICL_zh_male_badaoshaoye_tob",
            "元气少年": "ICL_zh_male_yuanqishaonian_tob",
            "洒脱青年": "ICL_zh_male_satuoqingnian_tob",
            "直率青年": "ICL_zh_male_zhishuaiqingnian_tob",
            "斯文青年": "ICL_zh_male_siwenqingnian_tob",
            "成熟总裁": "ICL_zh_male_chengshuzongcai_tob",
            "俊逸公子": "ICL_zh_male_junyigongzi_tob",
            "傲娇公子": "ICL_zh_male_aojiaogongzi_tob",
            "仗剑侠客": "ICL_zh_male_zhangjianxiake_tob",
            "机甲智能": "ICL_zh_male_jijiaozhineng_tob",
            "神秘法师": "ICL_zh_male_shenmifashi_tob",
            "霸道总裁": "ICL_zh_male_badaozongcai_v1_tob",
            
            # 视频配音
            "悠悠君子": "zh_male_M100_conversation_wvae_bigtts",
            "文静毛毛": "zh_female_maomao_conversation_wvae_bigtts",
            "倾心少女": "ICL_zh_female_qiuling_v1_tob",
            "醇厚低音": "ICL_zh_male_buyan_v1_tob",
            "咆哮小哥": "ICL_zh_male_BV144_paoxiaoge_v1_tob",
            "和蔼奶奶": "ICL_zh_female_heainainai_tob",
            "邻居阿姨": "ICL_zh_female_linjuayi_tob",
            "温柔小雅": "zh_female_wenrouxiaoya_moon_bigtts",
            "天才童声": "zh_male_tiancaitongsheng_mars_bigtts",
            "猴哥": "zh_male_sunwukong_mars_bigtts",
            "熊二": "zh_male_xionger_mars_bigtts",
            "佩奇猪": "zh_female_peiqi_mars_bigtts",
            "武则天": "zh_female_wuzetian_mars_bigtts",
            "顾姐": "zh_female_gujie_mars_bigtts",
            "樱桃丸子": "zh_female_yingtaowanzi_mars_bigtts",
            "广告解说": "zh_male_chunhui_mars_bigtts",
            "少儿故事": "zh_female_shaoergushi_mars_bigtts",
            "四郎": "zh_male_silang_mars_bigtts",
            "磁性解说男声/Morgan": "zh_male_jieshuonansheng_mars_bigtts",
            "鸡汤妹妹/Hope": "zh_female_jitangmeimei_mars_bigtts",
            "贴心女声/Candy": "zh_female_tiexinnvsheng_mars_bigtts",
            "俏皮女声": "zh_female_qiaopinvsheng_mars_bigtts",
            "萌丫头/Cutey": "zh_female_mengyatou_mars_bigtts",
            "懒音绵宝": "zh_male_lanxiaoyang_mars_bigtts",
            "亮嗓萌仔": "zh_male_dongmanhaimian_mars_bigtts",
            
            # 有声阅读
            "内敛才俊": "ICL_zh_male_neiliancaijun_e991be511569_tob",
            "温暖少年": "ICL_zh_male_yangyang_v1_tob",
            "儒雅公子": "ICL_zh_male_flc_v1_tob",
            "悬疑解说": "zh_male_changtianyi_mars_bigtts",
            "儒雅青年": "zh_male_ruyaqingnian_mars_bigtts",
            "霸气青叔": "zh_male_baqiqingshu_mars_bigtts",
            "擎苍": "zh_male_qingcang_mars_bigtts",
            "活力小哥": "zh_male_yangguangqingnian_mars_bigtts",
            "古风少御": "zh_female_gufengshaoyu_mars_bigtts",
            "温柔淑女": "zh_female_wenroushunv_mars_bigtts",
            "反卷青年": "zh_male_fanjuanqingnian_mars_bigtts"
        }
        
        doubao_tts_fields = [
            ("APP ID", "tts.doubao_app_id", "lineedit", ""),
            ("Access Token", "tts.doubao_access_token", "passwordlineedit", ""),
            ("Resource ID", "tts.doubao_resource_id", "lineedit", ""),
            ("音色类型", "tts.doubao_voice_type", "combobox", ""),
            ("编码格式", "tts.doubao_encoding", "combobox", "wav"),
            ("API URL", "tts.doubao_url", "lineedit", "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
        ]
        
        for label, key_path, widget_type, default in doubao_tts_fields:
            if widget_type == "combobox" and key_path == "tts.doubao_voice_type":
                widget = QComboBox()
                # 使用字典的keys作为选项（音色名称）
                widget.addItems(list(doubao_voice_types.keys()))
                widget.setEditable(True)  # 允许手动输入
                voice_type_val = self.config_data.get('tts', {}).get('doubao_voice_type', default)
                if voice_type_val:
                    # 检查是否是voice_type（value），如果是则找到对应的音色名称（key）
                    voice_name = None
                    if voice_type_val in doubao_voice_types.values():
                        # 如果存储的是voice_type，找到对应的音色名称
                        for name, vtype in doubao_voice_types.items():
                            if vtype == voice_type_val:
                                voice_name = name
                                break
                    else:
                        # 如果存储的是音色名称，直接使用
                        voice_name = voice_type_val
                    
                    if voice_name:
                        index = widget.findText(voice_name)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                        else:
                            widget.setCurrentText(voice_name)
            elif widget_type == "combobox" and key_path == "tts.doubao_encoding":
                widget = QComboBox()
                widget.addItems(["wav", "mp3", "ogg", "flac"])
                encoding_val = self.config_data.get('tts', {}).get('doubao_encoding', default)
                index = widget.findText(encoding_val)
                if index >= 0:
                    widget.setCurrentIndex(index)
            else:
                widget = self.create_widget(widget_type, key_path, default)
            
            doubao_tts_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        # 豆包TTS测试按钮
        doubao_test_btn = PushButton("测试豆包TTS")
        doubao_test_btn.clicked.connect(self.test_doubao_tts)
        doubao_tts_form.addRow("", doubao_test_btn)
        
        self.vBoxLayout.addWidget(doubao_tts_group)
        
        # Fish Audio配置组
        fish_audio_group = QGroupBox("Fish Audio配置")
        fish_audio_form = QFormLayout(fish_audio_group)
        
        # Fish Audio基础配置
        fish_audio_fields = [
            ("API Key", "tts.fish_audio_api_key", "passwordlineedit", ""),
            ("Reference ID", "tts.fish_audio_reference_id", "lineedit", ""),
            ("Backend Model", "tts.fish_audio_backend", "combobox", "speech-1.6"),
            ("Temperature", "tts.fish_audio_temperature", "doublespin", 0.7),
            ("Top P", "tts.fish_audio_top_p", "doublespin", 0.7)
        ]
        
        for label, key_path, widget_type, default in fish_audio_fields:
            if widget_type == "combobox" and key_path == "tts.fish_audio_backend":
                widget = QComboBox()
                widget.addItems(["speech-1.5", "speech-1.6", "s1"])
                backend_val = self.config_data.get('tts', {}).get('fish_audio_backend', default)
                index = widget.findText(backend_val)
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif widget_type == "doublespin":
                widget = self.create_widget(widget_type, key_path, default)
                widget.setRange(0.0, 1.0)
                widget.setSingleStep(0.1)
            else:
                widget = self.create_widget(widget_type, key_path, default)
            
            fish_audio_form.addRow(f"{label}:", widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        # Fish Audio参考音频文件选择
        fish_ref_audio_layout = QHBoxLayout()
        self.fish_ref_audio_edit = LineEdit()
        self.fish_ref_audio_edit.setText(self.config_data.get('tts', {}).get('fish_audio_ref_audio', ''))
        self.fish_ref_audio_edit.setPlaceholderText("选择参考音频文件 (.wav)")
        fish_ref_audio_btn = PushButton("选择文件")
        fish_ref_audio_btn.clicked.connect(self._select_fish_ref_audio)
        fish_ref_audio_layout.addWidget(self.fish_ref_audio_edit)
        fish_ref_audio_layout.addWidget(fish_ref_audio_btn)
        fish_ref_audio_widget = QWidget()
        fish_ref_audio_widget.setLayout(fish_ref_audio_layout)
        fish_audio_form.addRow("参考音频:", fish_ref_audio_widget)
        self.widgets['tts.fish_audio_ref_audio'] = {"widget": self.fish_ref_audio_edit, "type": "lineedit"}
        
        # Fish Audio参考音频文本
        fish_ref_text_edit = QTextEdit()
        fish_ref_text_edit.setPlainText(self.config_data.get('tts', {}).get('fish_audio_ref_text', ''))
        fish_ref_text_edit.setPlaceholderText("输入参考音频对应的文本内容")
        fish_ref_text_edit.setMaximumHeight(80)
        fish_audio_form.addRow("参考音频文本:", fish_ref_text_edit)
        self.widgets['tts.fish_audio_ref_text'] = {"widget": fish_ref_text_edit, "type": "textedit"}
        
        # Fish Audio测试按钮
        fish_test_btn = PushButton("测试Fish Audio")
        fish_test_btn.clicked.connect(self.test_fish_audio_tts)
        fish_audio_form.addRow("", fish_test_btn)
        
        self.vBoxLayout.addWidget(fish_audio_group)
        
        # 通用TTS配置
        common_tts_group = QGroupBox("通用TTS配置")
        common_tts_form = QFormLayout(common_tts_group)
        
        # 输出目录
        output_dir_layout = QHBoxLayout()
        self.tts_output_dir_edit = LineEdit()
        self.tts_output_dir_edit.setText(self.config_data.get('tts', {}).get('output_dir', 'output/audio'))
        self.tts_output_dir_edit.setPlaceholderText("TTS音频文件输出目录")
        output_dir_btn = PushButton("选择目录")
        output_dir_btn.clicked.connect(self._select_tts_output_dir)
        output_dir_layout.addWidget(self.tts_output_dir_edit)
        output_dir_layout.addWidget(output_dir_btn)
        output_dir_widget = QWidget()
        output_dir_widget.setLayout(output_dir_layout)
        common_tts_form.addRow("输出目录:", output_dir_widget)
        self.widgets['tts.output_dir'] = {"widget": self.tts_output_dir_edit, "type": "lineedit"}
        
        # 音频格式
        audio_format_combo = QComboBox()
        audio_format_combo.addItems(["wav", "mp3", "ogg", "flac"])
        format_val = self.config_data.get('tts', {}).get('audio_format', 'wav')
        index = audio_format_combo.findText(format_val)
        if index >= 0:
            audio_format_combo.setCurrentIndex(index)
        common_tts_form.addRow("音频格式:", audio_format_combo)
        self.widgets['tts.audio_format'] = {"widget": audio_format_combo, "type": "combobox"}
        
        self.vBoxLayout.addWidget(common_tts_group)
        self.vBoxLayout.addStretch()
    
    def _select_fish_ref_audio(self):
        """选择Fish Audio参考音频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频文件", "", "音频文件 (*.wav *.mp3 *.ogg *.flac)"
        )
        if file_path:
            self.fish_ref_audio_edit.setText(file_path)
    
    def _select_tts_output_dir(self):
        """选择TTS输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择TTS输出目录")
        if dir_path:
            self.tts_output_dir_edit.setText(dir_path)
    
    def test_doubao_tts(self):
        """测试豆包TTS配置"""
        try:
            # 豆包TTS音色映射（与UI中的相同）
            doubao_voice_types = {
                "北京小爷（多情感）": "zh_male_beijingxiaoye_emo_v2_mars_bigtts",
                "柔美女友（多情感）": "zh_female_roumeinvyou_emo_v2_mars_bigtts",
                "阳光青年（多情感）": "zh_male_yangguangqingnian_emo_v2_mars_bigtts",
                "魅力女友（多情感）": "zh_female_meilinvyou_emo_v2_mars_bigtts",
                "爽快思思（多情感）": "zh_female_shuangkuaisisi_emo_v2_mars_bigtts",
                "甜心小美（多情感）": "zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
                "高冷御姐（多情感）": "zh_female_gaolengyujie_emo_v2_mars_bigtts",
                "傲娇霸总（多情感）": "zh_male_aojiaobazong_emo_v2_mars_bigtts",
                "广州德哥（多情感）": "zh_male_guangzhoudege_emo_mars_bigtts",
                "京腔侃爷（多情感）": "zh_male_jingqiangkanye_emo_mars_bigtts",
                "邻居阿姨（多情感）": "zh_female_linjuayi_emo_v2_mars_bigtts",
                "优柔公子（多情感）": "zh_male_yourougongzi_emo_v2_mars_bigtts",
                "儒雅男友（多情感）": "zh_male_ruyayichen_emo_v2_mars_bigtts",
                "俊朗男友（多情感）": "zh_male_junlangnanyou_emo_v2_mars_bigtts",
                "冷酷哥哥（多情感）": "zh_male_lengkugege_emo_v2_mars_bigtts",
                "Glen": "en_male_glen_emo_v2_mars_bigtts",
                "Sylus": "en_male_sylus_emo_v2_mars_bigtts",
                "Candice": "en_female_candice_emo_v2_mars_bigtts",
                "Corey": "en_male_corey_emo_v2_mars_bigtts",
                "Nadia": "en_female_nadia_tips_emo_v2_mars_bigtts",
                "Serena": "en_female_skye_emo_v2_mars_bigtts"
            }
            
            # 获取配置
            app_id = self.widgets.get('tts.doubao_app_id', {}).get('widget', LineEdit()).text().strip()
            access_token = self.widgets.get('tts.doubao_access_token', {}).get('widget', PasswordLineEdit()).text().strip()

            # 获取音色类型 - 现在是QComboBox，需要使用currentText()获取音色名称，然后转换为voice_type
            voice_type_widget = self.widgets.get('tts.doubao_voice_type', {}).get('widget')
            if hasattr(voice_type_widget, 'currentText'):
                voice_name = voice_type_widget.currentText().strip()
                # 将音色名称转换为对应的voice_type
                voice_type = doubao_voice_types.get(voice_name, voice_name)
            else:
                voice_type = voice_type_widget.text().strip() if voice_type_widget else ""

            if not all([app_id, access_token, voice_type]):
                InfoBar.warning(
                    title='配置不完整',
                    content='请填写完整的豆包TTS配置信息',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return

            # 记录测试日志
            self.log_tts_system_event("开始测试豆包TTS配置")
            self.log_tts_doubao_request(app_id, voice_type, "wav", "这是一个测试文本")

            InfoBar.success(
                title='配置检查完成',
                content='豆包TTS配置信息已填写完整，请确保账户有效',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

        except Exception as e:
            self.log_tts_error("豆包TTS测试", str(e))
            InfoBar.error(
                title='测试失败',
                content=f'豆包TTS测试出错: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def test_fish_audio_tts(self):
        """测试Fish Audio TTS配置"""
        try:
            # 获取配置
            api_key = self.widgets.get('tts.fish_audio_api_key', {}).get('widget', PasswordLineEdit()).text().strip()
            reference_id = self.widgets.get('tts.fish_audio_reference_id', {}).get('widget', LineEdit()).text().strip()
            
            if not api_key:
                InfoBar.warning(
                    title='配置不完整',
                    content='请填写Fish Audio API Key',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 记录测试日志
            self.log_tts_system_event("开始测试Fish Audio TTS配置")
            backend = self.widgets.get('tts.fish_audio_backend', {}).get('widget', QComboBox()).currentText()
            temperature = self.widgets.get('tts.fish_audio_temperature', {}).get('widget', DoubleSpinBox()).value()
            top_p = self.widgets.get('tts.fish_audio_top_p', {}).get('widget', DoubleSpinBox()).value()
            self.log_tts_fish_audio_request(reference_id, "这是一个测试文本", backend, temperature, top_p)
            
            InfoBar.success(
                title='配置检查完成',
                content='Fish Audio TTS配置信息已填写完整，请确保API Key有效',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
        except Exception as e:
            self.log_tts_error("Fish Audio TTS测试", str(e))
            InfoBar.error(
                title='测试失败',
                content=f'Fish Audio TTS测试出错: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def create_ui_tab(self):
        """创建UI配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 基础配置（不包含模型路径）
        fields = [
            ("介绍文本", "ui.intro_text", "lineedit", ""),
            ("模型缩放", "ui.model_scale", "doublespin", 1.0)
        ]
        group_base = self.create_form_group(self, "UI配置", fields)
        self.vBoxLayout.addWidget(group_base)

        # 模型路径下拉选择：扫描 models/2d 下的 *.model3.json（并提供常见目录回退）
        model_group = QGroupBox("模型路径")
        form_layout = QFormLayout(model_group)
        self.model_combo = QComboBox()
        self._refresh_model_combo()  # 填充

        # 根据已有配置选中当前项
        current_path = (
            self.config_data.get('ui', {}).get('model_path', '')
            if isinstance(self.config_data, dict) else ''
        )
        if current_path:
            idx = -1
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == current_path:
                    idx = i
                    break
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

        # 刷新按钮
        refresh_btn = QPushButton('刷新')
        def on_refresh():
            prev = self.model_combo.currentData()
            self._refresh_model_combo()
            # 尝试保持原选择
            if prev:
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == prev:
                        self.model_combo.setCurrentIndex(i)
                        break
        refresh_btn.clicked.connect(on_refresh)

        row = QHBoxLayout()
        row.addWidget(self.model_combo)
        row.addWidget(refresh_btn)
        row_container = QWidget()
        row_container.setLayout(row)
        form_layout.addRow('Live2D 模型：', row_container)
        self.vBoxLayout.addWidget(model_group)

        # 注册到统一收集器
        self.widgets['ui.model_path'] = {"widget": self.model_combo, "type": "combobox"}
        
        # 添加模型详情浏览功能
        self.create_model_details_section()
        
        # 动作按钮绑定设置
        self.create_action_buttons_binding_section()
        
        self.vBoxLayout.addStretch()

    def _scan_model_roots(self):
        """返回可能的模型根目录列表，优先 models/2d，再回退 live-2d/2D 与 ai_live2d/2D"""
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        potential_roots = [
            os.path.join(proj_root, 'models', '2d'),
            os.path.join(proj_root, 'live-2d', '2D'),
            os.path.join(os.path.dirname(__file__), '2D'),
            os.path.join(proj_root, 'py-my-neuro', '2D'),  # 添加py-my-neuro路径
            os.path.join(proj_root, 'py-my-neuro', 'UI', '2D'),  # 添加py-my-neuro/UI路径
        ]
        
        # 只返回存在的目录
        existing_roots = []
        main_logger = logging.getLogger()
        for root in potential_roots:
            if os.path.isdir(root):
                existing_roots.append(root)
                main_logger.info(f"✅ 发现模型目录: {root}")
            else:
                main_logger.debug(f"ℹ️  跳过不存在的目录: {root}")
        
        return existing_roots

    def _refresh_model_combo(self):
        """扫描 *.model3.json 并刷新下拉列表，二级文件夹名作为显示文本，值为文件绝对路径"""
        self.model_combo.clear()
        added = set()
        for root in self._scan_model_roots():
            if not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    if fn.lower().endswith('model3.json'):
                        full = os.path.abspath(os.path.join(dirpath, fn))
                        # 二级文件夹名：相对 root 的第一层目录名
                        rel = os.path.relpath(full, root)
                        parts = rel.split(os.sep)
                        
                        # 获取模型文件夹名（不是根目录名）
                        if len(parts) >= 2:
                            display = parts[0]  # 第一层子目录名
                        else:
                            # 如果直接在根目录下，使用文件名（去掉扩展名）
                            display = os.path.splitext(fn)[0]
                        
                        # 过滤掉常见的根目录名和无意义的名称
                        if display.lower() in ['2d', 'models', 'live2d', 'ai_live2d', 'ui']:
                            # 如果显示名是根目录名，尝试使用更深层的目录名或文件名
                            if len(parts) >= 3:
                                display = parts[1]  # 使用第二层目录名
                            else:
                                display = os.path.splitext(fn)[0]  # 使用文件名
                        
                        # 确保显示名不为空且有意义
                        if not display or display.lower() in ['2d', 'models', 'live2d']:
                            display = os.path.splitext(fn)[0]  # 最后回退到文件名
                        
                        key = (display, full)
                        if display and key not in added:
                            self.model_combo.addItem(display, full)
                            added.add(key)

    def create_model_details_section(self):
        """创建模型详情浏览功能"""
        details_group = QGroupBox("Live2D模型详情")
        details_layout = QVBoxLayout(details_group)
        
        # 顶部按钮区域
        button_layout = QHBoxLayout()
        
        # 加载模型详情按钮
        self.load_details_btn = PrimaryToolButton(FIF.VIEW)
        self.load_details_btn.setText("加载模型详情")
        self.load_details_btn.clicked.connect(self.load_model_details)
        button_layout.addWidget(self.load_details_btn)
        
        # 测试表情按钮
        self.test_expression_btn = ToolButton(FIF.PLAY)
        self.test_expression_btn.setText("测试随机表情")
        self.test_expression_btn.clicked.connect(self.test_random_expression)
        self.test_expression_btn.setEnabled(False)
        button_layout.addWidget(self.test_expression_btn)
        
        # 预览Live2D按钮
        self.preview_live2d_btn = ToolButton(FIF.VIEW)
        self.preview_live2d_btn.setText("预览Live2D")
        self.preview_live2d_btn.clicked.connect(self.open_live2d_preview)
        self.preview_live2d_btn.setEnabled(False)
        self.preview_live2d_btn.setToolTip("在新窗口中预览Live2D模型")
        button_layout.addWidget(self.preview_live2d_btn)
        
        button_layout.addStretch()
        details_layout.addLayout(button_layout)
        
        # 创建水平分割的详情区域
        details_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：基础信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # 模型基础信息显示
        self.model_info_browser = TextBrowser()
        self.model_info_browser.setMaximumHeight(150)
        self.model_info_browser.setPlainText("请选择模型并点击'加载模型详情'按钮")
        info_layout.addWidget(QLabel("模型基础信息:"))
        info_layout.addWidget(self.model_info_browser)
        
        details_splitter.addWidget(info_widget)
        
        # 右侧：表情和动作列表
        lists_widget = QWidget()
        lists_layout = QVBoxLayout(lists_widget)
        
        # 表情列表
        expr_layout = QVBoxLayout()
        expr_layout.addWidget(QLabel("支持的表情:"))
        
        self.expression_list = QListWidget()
        self.expression_list.setMaximumHeight(120)
        self.expression_list.itemDoubleClicked.connect(self.on_expression_double_click)
        expr_layout.addWidget(self.expression_list)
        
        lists_layout.addLayout(expr_layout)
        
        # 动作组列表
        motion_layout = QVBoxLayout()
        motion_layout.addWidget(QLabel("支持的动作组:"))
        
        self.motion_list = QListWidget()
        self.motion_list.setMaximumHeight(120)
        self.motion_list.itemDoubleClicked.connect(self.on_motion_double_click)
        motion_layout.addWidget(self.motion_list)
        
        lists_layout.addLayout(motion_layout)
        
        details_splitter.addWidget(lists_widget)
        
        # 设置分割器比例
        details_splitter.setSizes([400, 300])
        
        details_layout.addWidget(details_splitter)
        
        self.vBoxLayout.addWidget(details_group)

    def create_action_buttons_binding_section(self):
        """创建动作按钮绑定设置功能"""
        binding_group = QGroupBox("动作按钮绑定设置")
        binding_layout = QVBoxLayout(binding_group)
        
        # 说明文本
        desc_label = QLabel("在这里可以为动作一和动作二按钮绑定特定的Live2D动作。\n"
                           "选择动作后，点击对应的'绑定'按钮即可设置。")
        desc_label.setStyleSheet("color: #666; font-size: 12px;")
        desc_label.setWordWrap(True)
        binding_layout.addWidget(desc_label)
        
        # 动作一绑定区域
        action1_layout = QHBoxLayout()
        action1_layout.addWidget(QLabel("动作一:"))
        
        self.action1_combo = QComboBox()
        self.action1_combo.addItem("未绑定", "")
        self._populate_action_combo(self.action1_combo)
        action1_layout.addWidget(self.action1_combo)
        
        self.bind_action1_btn = ToolButton(FIF.LINK)
        self.bind_action1_btn.setText("绑定")
        self.bind_action1_btn.setToolTip("将选中的动作绑定到动作一按钮")
        self.bind_action1_btn.clicked.connect(lambda: self.bind_action_to_button(1))
        action1_layout.addWidget(self.bind_action1_btn)
        
        action1_layout.addStretch()
        binding_layout.addLayout(action1_layout)
        
        # 动作二绑定区域
        action2_layout = QHBoxLayout()
        action2_layout.addWidget(QLabel("动作二:"))
        
        self.action2_combo = QComboBox()
        self.action2_combo.addItem("未绑定", "")
        self._populate_action_combo(self.action2_combo)
        action2_layout.addWidget(self.action2_combo)
        
        self.bind_action2_btn = ToolButton(FIF.LINK)
        self.bind_action2_btn.setText("绑定")
        self.bind_action2_btn.setToolTip("将选中的动作绑定到动作二按钮")
        self.bind_action2_btn.clicked.connect(lambda: self.bind_action_to_button(2))
        action2_layout.addWidget(self.bind_action2_btn)
        
        action2_layout.addStretch()
        binding_layout.addLayout(action2_layout)
        
        # 当前绑定状态显示
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("当前绑定状态:"))
        
        self.binding_status_browser = TextBrowser()
        self.binding_status_browser.setMaximumHeight(80)
        self.binding_status_browser.setPlainText("未设置绑定")
        status_layout.addWidget(self.binding_status_browser)
        
        binding_layout.addLayout(status_layout)
        
        # 刷新按钮
        refresh_binding_btn = ToolButton(FIF.UPDATE)
        refresh_binding_btn.setText("刷新动作列表")
        refresh_binding_btn.setToolTip("重新加载当前模型的动作列表")
        refresh_binding_btn.clicked.connect(self.refresh_action_bindings)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(refresh_binding_btn)
        button_layout.addStretch()
        binding_layout.addLayout(button_layout)
        
        self.vBoxLayout.addWidget(binding_group)
        
        # 初始化绑定状态
        self.refresh_action_bindings()

    def _populate_action_combo(self, combo):
        """填充动作下拉列表"""
        try:
            # 尝试从动画列表中获取动作
            if hasattr(self, 'animation_motion_list') and self.animation_motion_list.count() > 0:
                for i in range(self.animation_motion_list.count()):
                    item = self.animation_motion_list.item(i)
                    if item:
                        combo.addItem(item.text(), item.data(Qt.UserRole))
            else:
                # 如果没有动画列表，添加一些默认选项
                combo.addItem("Idle", 0)
                combo.addItem("Tap", 1)
                combo.addItem("随机动作", -1)
        except Exception as e:
            print(f"填充动作列表失败: {e}")
            combo.addItem("Idle", 0)

    def bind_action_to_button(self, button_num):
        """绑定动作到按钮"""
        try:
            combo = self.action1_combo if button_num == 1 else self.action2_combo
            action_name = combo.currentText()
            action_data = combo.currentData()
            
            if not action_name or action_name == "未绑定":
                InfoBar.warning(
                    title=f'动作{button_num}绑定',
                    content="请选择要绑定的动作",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 保存到配置
            action_config = self.config_data.setdefault('action_buttons', {})
            action_config[f'action_{button_num}'] = action_name
            
            # 保存配置
            self.save_config()
            
            # 更新状态显示
            self.refresh_action_bindings()
            
            InfoBar.success(
                title=f'动作{button_num}绑定成功',
                content=f"已将 '{action_name}' 绑定到动作{button_num}按钮",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title=f'动作{button_num}绑定失败',
                content=f"绑定失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def refresh_action_bindings(self):
        """刷新动作绑定状态"""
        try:
            action_config = self.config_data.get('action_buttons', {})
            
            status_text = ""
            for i in [1, 2]:
                action_name = action_config.get(f'action_{i}', '未绑定')
                status_text += f"动作{i}: {action_name}\n"
            
            if not status_text.strip():
                status_text = "未设置任何绑定"
            
            self.binding_status_browser.setPlainText(status_text.strip())
            
            # 更新下拉列表的选中状态
            for i in [1, 2]:
                combo = self.action1_combo if i == 1 else self.action2_combo
                action_name = action_config.get(f'action_{i}', '')
                
                if action_name:
                    # 查找对应的索引
                    for j in range(combo.count()):
                        if combo.itemText(j) == action_name:
                            combo.setCurrentIndex(j)
                            break
                else:
                    combo.setCurrentIndex(0)  # 未绑定
            
        except Exception as e:
            print(f"刷新动作绑定状态失败: {e}")
            self.binding_status_browser.setPlainText("刷新失败")

    def load_model_details(self):
        """加载当前选中模型的详情信息"""
        current_model_path = self.model_combo.currentData()
        if not current_model_path or not os.path.exists(current_model_path):
            self.model_info_browser.setPlainText("❌ 请先选择有效的模型文件")
            self.expression_list.clear()
            self.motion_list.clear()
            self.test_expression_btn.setEnabled(False)
            return
        
        try:
            # 首先检查文件完整性
            file_size = os.path.getsize(current_model_path)
            if file_size < 100:  # 如果文件太小，可能是损坏的
                raise Exception(f"模型文件可能损坏或不完整 (文件大小: {file_size} bytes)")
            
            # 直接使用备用方法解析JSON文件，这样更稳定
            print(f"🔍 开始解析模型文件: {current_model_path}")
            self.load_model_details_fallback(current_model_path)
            return
            
        except Exception as e:
            print(f"❌ 模型解析失败: {e}")
            self.model_info_browser.setHtml(f"""
            <div style='color: red;'>
            <h4>❌ 加载模型详情失败</h4>
            <p><b>错误信息:</b> {str(e)}</p>
            <p><b>模型路径:</b> {current_model_path}</p>
            <p><b>文件大小:</b> {os.path.getsize(current_model_path) / 1024:.2f} KB</p>
            <p><b>最后修改:</b> {time.ctime(os.path.getmtime(current_model_path))}</p>
            <p style='color: gray; font-size: 12px;'>提示：请确保Live2D模型文件完整且格式正确</p>
            <br>
            <button onclick='this.parentElement.style.display="none"' style='background: #0078d4; color: white; border: none; padding: 8px 16px; cursor: pointer; border-radius: 4px;'>关闭错误信息</button>
            </div>
            """)
            self.expression_list.clear()
            self.motion_list.clear()
            self.test_expression_btn.setEnabled(False)
            raise e
                
        except Exception as e:
            self.model_info_browser.setHtml(f"""
            <div style='color: red;'>
            <h4>❌ 加载模型详情失败</h4>
            <p><b>错误信息:</b> {str(e)}</p>
            <p><b>模型路径:</b> {current_model_path}</p>
            <p><b>文件大小:</b> {os.path.getsize(current_model_path) / 1024:.2f} KB</p>
            <p><b>最后修改:</b> {time.ctime(os.path.getmtime(current_model_path))}</p>
            <p style='color: gray; font-size: 12px;'>提示：请确保Live2D模型文件完整且格式正确</p>
            </div>
            """)
            self.expression_list.clear()
            self.motion_list.clear()
            self.test_expression_btn.setEnabled(False)

    def update_model_info_display(self, model_path, expressions, motions, param_count, canvas_info):
        """更新模型信息显示"""
        # 更新基础信息
        model_name = os.path.basename(os.path.dirname(model_path))
        file_size = os.path.getsize(model_path) / 1024
        mod_time = time.ctime(os.path.getmtime(model_path))
        
        info_html = f"""
        <div style='font-family: Microsoft YaHei;'>
        <h4 style='color: #0078d4; margin: 8px 0;'>✅ {model_name}</h4>
        <p><b>文件路径:</b> {model_path}</p>
        <p><b>文件大小:</b> {file_size:.2f} KB</p>
        <p><b>最后修改:</b> {mod_time}</p>
        <p><b>画布大小:</b> {canvas_info}</p>
        <p><b>参数数量:</b> {param_count}</p>
        <p><b>表情数量:</b> {len(expressions)}</p>
        <p><b>动作组数量:</b> {len(motions)}</p>
        </div>
        """
        self.model_info_browser.setHtml(info_html)
        
        # 更新表情列表
        self.expression_list.clear()
        if expressions:
            for expr in expressions:
                item = QListWidgetItem(f"🎭 {expr}")
                item.setData(Qt.UserRole, expr)
                item.setToolTip(f"双击测试表情: {expr}")
                self.expression_list.addItem(item)
            self.test_expression_btn.setEnabled(True)
        else:
            item = QListWidgetItem("😐 该模型不支持表情")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.expression_list.addItem(item)
            self.test_expression_btn.setEnabled(False)
        
        # 更新动作组列表
        self.motion_list.clear()
        if motions:
            for group_name, count in motions.items():
                item = QListWidgetItem(f"🎬 {group_name} ({count}个动作)")
                item.setData(Qt.UserRole, group_name)
                item.setToolTip(f"动作组: {group_name}，包含 {count} 个动作")
                self.motion_list.addItem(item)
        else:
            item = QListWidgetItem("🚫 该模型不包含动作组")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.motion_list.addItem(item)

    def on_expression_double_click(self, item):
        """双击表情项时测试该表情"""
        expression_name = item.data(Qt.UserRole)
        if expression_name:
            self.test_specific_expression(expression_name)

    def on_motion_double_click(self, item):
        """双击动作组项时显示详情"""
        motion_group = item.data(Qt.UserRole)
        if motion_group:
            InfoBar.success(
                title='动作组信息',
                content=f"动作组: {motion_group}\n双击动作组暂不支持直接测试，请在Live2D界面中测试",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def test_specific_expression(self, expression_name):
        """测试指定表情"""
        try:
            # 这里可以通过事件总线或直接调用Live2D模型来测试表情
            InfoBar.success(
                title='表情测试',
                content=f"正在测试表情: {expression_name}\n(需要Live2D模型正在运行)",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 如果有事件总线，可以发送表情切换事件
            # if hasattr(self, 'event_bus') and self.event_bus:
            #     self.event_bus.emit('expression_change', expression_name)
            
        except Exception as e:
            InfoBar.error(
                title='表情测试失败',
                content=f"无法测试表情 {expression_name}: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def test_random_expression(self):
        """测试随机表情"""
        if self.expression_list.count() > 0:
            # 随机选择一个表情项
            valid_items = []
            for i in range(self.expression_list.count()):
                item = self.expression_list.item(i)
                if item.data(Qt.UserRole):  # 只选择有效的表情项
                    valid_items.append(item)
            
            if valid_items:
                selected_item = random.choice(valid_items)
                expression_name = selected_item.data(Qt.UserRole)
                self.test_specific_expression(expression_name)
                # 高亮选中的表情
                self.expression_list.setCurrentItem(selected_item)
            else:
                InfoBar.warning(
                    title='无可用表情',
                    content="当前模型没有可测试的表情",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        else:
            InfoBar.warning(
                title='请先加载模型详情',
                content="请先选择模型并加载详情信息",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def open_live2d_preview(self):
        """打开Live2D预览窗口"""
        try:
            # 获取当前选中的模型路径
            current_model = ""
            if hasattr(self, 'model_combo') and self.model_combo.currentData():
                current_model = self.model_combo.currentData()
            elif hasattr(self, 'config_data'):
                # 从配置中获取模型路径作为备选
                current_model = self.config_data.get('ui', {}).get('model_path', '')
            
            if not current_model:
                InfoBar.warning(
                    title='请选择模型',
                    content="请先在UI配置中选择要预览的Live2D模型文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            if not os.path.exists(current_model):
                InfoBar.error(
                    title='模型文件不存在',
                    content=f"找不到模型文件: {current_model}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            # 创建并显示预览窗口
            try:
                preview_window = Live2DPreviewWindow(current_model, self)
                preview_window.exec_()  # 模态显示
            except Exception as e:
                InfoBar.error(
                    title='预览窗口创建失败',
                    content=f"无法创建预览窗口: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
                print(f"❌ 预览窗口创建失败: {e}")
                
        except Exception as e:
            InfoBar.error(
                title='预览功能错误',
                content=f"预览功能发生错误: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            print(f"❌ 预览功能错误: {e}")
            InfoBar.error(
                title='预览功能错误',
                content=f"预览功能发生错误: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            print(f"❌ 预览功能错误: {e}")

    def load_model_details_fallback(self, model_path):
        """备用方法：直接解析model3.json文件获取信息"""
        try:
            print(f"🔍 使用备用方法解析模型文件: {model_path}")
            
            # 检查文件是否可读
            if not os.access(model_path, os.R_OK):
                raise Exception("模型文件无法读取，请检查文件权限")
            
            # 读取model3.json文件
            with open(model_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    raise Exception("模型文件为空")
                
                try:
                    model_data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise Exception(f"模型文件JSON格式错误: {e}")
            
            # 验证基本结构
            if not isinstance(model_data, dict):
                raise Exception("模型文件格式不正确：根元素必须是对象")
            
            # 解析表情信息
            expressions = []
            if 'FileReferences' in model_data and 'Expressions' in model_data['FileReferences']:
                expr_data = model_data['FileReferences']['Expressions']
                if isinstance(expr_data, list):
                    for expr in expr_data:
                        if isinstance(expr, dict):
                            if 'Name' in expr:
                                expressions.append(expr['Name'])
                            elif 'File' in expr:
                                # 从文件名提取表情名
                                expr_name = os.path.splitext(os.path.basename(expr['File']))[0]
                                expressions.append(expr_name)
                        elif isinstance(expr, str):
                            # 直接是文件名
                            expr_name = os.path.splitext(os.path.basename(expr))[0]
                            expressions.append(expr_name)
            
            # 解析动作信息
            motions = {}
            if 'FileReferences' in model_data and 'Motions' in model_data['FileReferences']:
                motion_data = model_data['FileReferences']['Motions']
                if isinstance(motion_data, dict):
                    for group_name, motion_list in motion_data.items():
                        if isinstance(motion_list, list):
                            motions[group_name] = len(motion_list)
                        elif isinstance(motion_list, dict):
                            motions[group_name] = 1
                        else:
                            motions[group_name] = 1
            
            # 获取参数信息（从文件中解析）
            param_count = "未知"
            moc_file = "未找到"
            if 'FileReferences' in model_data and 'Moc' in model_data['FileReferences']:
                moc_file = model_data['FileReferences']['Moc']
                param_count = "通过.moc文件确定"
                
                # 尝试验证moc文件是否存在
                if isinstance(moc_file, str):
                    moc_path = os.path.join(os.path.dirname(model_path), moc_file)
                    if os.path.exists(moc_path):
                        param_count = f"Moc文件存在 ({os.path.getsize(moc_path) / 1024:.1f} KB)"
                    else:
                        param_count = f"Moc文件不存在: {moc_file}"
            
            # 获取画布信息
            canvas_info = "默认"
            if 'Layout' in model_data:
                layout = model_data['Layout']
                if isinstance(layout, dict):
                    center_x = layout.get('CenterX', 0)
                    center_y = layout.get('CenterY', 0)
                    width = layout.get('Width', 'auto')
                    height = layout.get('Height', 'auto')
                    canvas_info = f"中心: ({center_x}, {center_y}), 尺寸: {width}x{height}"
            
            # 更新显示
            self.update_model_info_display_fallback(
                model_path, expressions, motions, param_count, canvas_info, model_data
            )
            
            print(f"✅ 备用方法成功解析模型，找到 {len(expressions)} 个表情，{len(motions)} 个动作组")
            
        except Exception as e:
            print(f"❌ 备用方法解析失败: {e}")
            # 显示详细错误信息
            self.model_info_browser.setHtml(f"""
            <div style='color: red; font-family: Microsoft YaHei;'>
            <h4>❌ 模型文件解析失败</h4>
            <p><b>错误详情:</b> {str(e)}</p>
            <p><b>文件路径:</b> {model_path}</p>
            <p><b>文件大小:</b> {os.path.getsize(model_path) if os.path.exists(model_path) else 0} bytes</p>
            <p><b>可能的原因:</b></p>
            <ul>
                <li>模型文件损坏或不完整</li>
                <li>JSON格式错误</li>
                <li>文件编码问题</li>
                <li>文件权限不足</li>
            </ul>
            <p style='color: orange;'><b>建议:</b> 请检查模型文件是否正确下载，或尝试重新获取模型文件</p>
            </div>
            """)
            self.expression_list.clear()
            self.motion_list.clear()
            self.test_expression_btn.setEnabled(False)
            raise e

    def update_model_info_display_fallback(self, model_path, expressions, motions, param_count, canvas_info, model_data):
        """使用备用方法更新模型信息显示"""
        # 更新基础信息
        model_name = os.path.basename(os.path.dirname(model_path))
        file_size = os.path.getsize(model_path) / 1024
        mod_time = time.ctime(os.path.getmtime(model_path))
        
        # 获取额外信息
        version = model_data.get('Version', '未知')
        moc_file = model_data.get('FileReferences', {}).get('Moc', '未找到')
        
        info_html = f"""
        <div style='font-family: Microsoft YaHei;'>
        <h4 style='color: #0078d4; margin: 8px 0;'>✅ {model_name} (解析模式)</h4>
        <p><b>文件路径:</b> {model_path}</p>
        <p><b>文件大小:</b> {file_size:.2f} KB</p>
        <p><b>最后修改:</b> {mod_time}</p>
        <p><b>模型版本:</b> {version}</p>
        <p><b>Moc文件:</b> {moc_file}</p>
        <p><b>画布信息:</b> {canvas_info}</p>
        <p><b>参数信息:</b> {param_count}</p>
        <p><b>表情数量:</b> {len(expressions)}</p>
        <p><b>动作组数量:</b> {len(motions)}</p>
        <p style='color: #666; font-size: 12px;'>注：通过解析JSON文件获取信息，部分功能受限</p>
        </div>
        """
        self.model_info_browser.setHtml(info_html)
        
        # 更新表情列表
        self.expression_list.clear()
        if expressions:
            for expr in expressions:
                item = QListWidgetItem(f"🎭 {expr}")
                item.setData(Qt.UserRole, expr)
                item.setToolTip(f"表情: {expr} (仅显示，无法直接测试)")
                self.expression_list.addItem(item)
            # 启用测试按钮，但功能受限
            self.test_expression_btn.setEnabled(True)
            self.test_expression_btn.setToolTip("表情测试功能需要Live2D运行时支持")
        else:
            item = QListWidgetItem("😐 该模型不包含表情定义")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.expression_list.addItem(item)
            self.test_expression_btn.setEnabled(False)
        
        # 更新动作组列表
        self.motion_list.clear()
        if motions:
            for group_name, count in motions.items():
                item = QListWidgetItem(f"🎬 {group_name} ({count}个动作)")
                item.setData(Qt.UserRole, group_name)
                item.setToolTip(f"动作组: {group_name}，包含 {count} 个动作")
                self.motion_list.addItem(item)
        else:
            item = QListWidgetItem("🚫 该模型不包含动作组定义")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.motion_list.addItem(item)
        
        # 启用预览按钮（如果存在）
        if hasattr(self, 'preview_live2d_btn'):
            self.preview_live2d_btn.setEnabled(True)
            self.preview_live2d_btn.setToolTip(f"预览Live2D模型: {os.path.basename(model_path)}")

    def create_subtitle_tab(self):
        """创建字幕配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 读取配置
        subtitle_config = self.config_data.get('subtitle', {})
        
        # 基础设置组
        basic_group = QGroupBox("基础设置")
        basic_form = QFormLayout(basic_group)
        
        # 基础设置字段
        basic_fields = [
            ("字体", "subtitle.font_family", "lineedit", "Microsoft YaHei"),
            ("字体大小", "subtitle.font_size", "spinbox", 24),
            ("粗体", "subtitle.font_bold", "checkbox", False),
            ("文本框高度", "subtitle.box_height", "spinbox", 800),
            ("文本框宽度", "subtitle.box_width", "spinbox", 1800),
            ("内边距", "subtitle.padding", "spinbox", 20),
            ("边框半径", "subtitle.border_radius", "spinbox", 15),
            ("淡入淡出时间", "subtitle.fade_duration", "spinbox", 300),
            ("自动隐藏延迟", "subtitle.auto_hide_delay", "spinbox", 0),
            ("字符延迟", "subtitle.char_delay", "spinbox", 50)
        ]
        
        for label, key_path, widget_type, default in basic_fields:
            # 获取当前值
            keys = key_path.split('.')
            value = self.config_data
            for key in keys:
                value = value.get(key, default)
            
            # 创建控件
            if widget_type == "lineedit":
                widget = LineEdit()
                widget.setText(str(value))
            elif widget_type == "spinbox":
                widget = SpinBox()
                widget.setRange(0, 999999)
                widget.setValue(int(value))
            elif widget_type == "checkbox":
                widget = CheckBox()
                widget.setChecked(bool(value))
            
            basic_form.addRow(label, widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(basic_group)
        
        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_form = QFormLayout(display_group)
        
        # 显示器选择
        self.subtitle_monitor_combo = QComboBox()
        self.refresh_monitor_list()
        
        # 获取当前选择的显示器
        current_monitor = subtitle_config.get('display_monitor', 0)
        for i in range(self.subtitle_monitor_combo.count()):
            if self.subtitle_monitor_combo.itemData(i) == current_monitor:
                self.subtitle_monitor_combo.setCurrentIndex(i)
                break
        
        display_form.addRow("显示器选择:", self.subtitle_monitor_combo)
        self.widgets["subtitle.display_monitor"] = {"widget": self.subtitle_monitor_combo, "type": "combobox"}
        
        # 连接显示器选择变化事件
        self.subtitle_monitor_combo.currentIndexChanged.connect(self.on_monitor_selection_changed)
        
        # 添加刷新按钮
        refresh_monitor_btn = PushButton("刷新显示器列表")
        refresh_monitor_btn.clicked.connect(self.refresh_monitor_list)
        display_form.addRow("", refresh_monitor_btn)
        
        # 位置设置模式选择
        position_mode_group = QGroupBox("位置设置模式")
        position_mode_layout = QVBoxLayout(position_mode_group)
        
        # 预设位置模式
        preset_widget = QWidget()
        preset_layout = QFormLayout(preset_widget)
        
        # 快捷位置选择（原下拉框改为快捷计算）
        position_combo = QComboBox()
        positions = [
            ("屏幕中央", "center"),
            ("屏幕上方", "top"),
            ("屏幕下方", "bottom"),
            ("屏幕左侧", "left"),
            ("屏幕右侧", "right"),
            ("左上角", "top_left"),
            ("右上角", "top_right"),
            ("左下角", "bottom_left"),
            ("右下角", "bottom_right"),
            ("左上中", "top_left_center"),
            ("右上中", "top_right_center"),
            ("左下中", "bottom_left_center"),
            ("右下中", "bottom_right_center"),
            ("左中", "left_center"),
            ("右中", "right_center"),
            ("上中", "top_center"),
            ("下中", "bottom_center")
        ]
        
        current_position = subtitle_config.get('display_position', 'bottom')
        for i, (display_name, value) in enumerate(positions):
            position_combo.addItem(display_name, value)
            if value == current_position:
                position_combo.setCurrentIndex(i)
        
        preset_layout.addRow("快捷位置:", position_combo)
        self.widgets["subtitle.display_position"] = {"widget": position_combo, "type": "combobox"}
        
        # 连接位置选择变化事件
        position_combo.currentIndexChanged.connect(self._on_subtitle_position_changed)
        
        # 计算位置按钮
        calc_position_btn = PushButton("计算并应用位置")
        calc_position_btn.clicked.connect(self._calculate_position_coordinates)
        preset_layout.addRow("", calc_position_btn)
        
        position_mode_layout.addWidget(preset_widget)
        
        # 精确坐标设置
        coords_widget = QWidget()
        coords_layout = QFormLayout(coords_widget)
        
        # X坐标（相对于选择的显示器）
        x_coord_widget = SpinBox()
        x_coord_widget.setRange(0, 5000)
        x_coord_widget.setValue(subtitle_config.get('position_x', 0))
        coords_layout.addRow("X坐标:", x_coord_widget)
        self.widgets["subtitle.position_x"] = {"widget": x_coord_widget, "type": "spinbox"}
        
        # Y坐标（相对于选择的显示器）
        y_coord_widget = SpinBox()
        y_coord_widget.setRange(0, 3000)
        y_coord_widget.setValue(subtitle_config.get('position_y', 0))
        coords_layout.addRow("Y坐标:", y_coord_widget)
        self.widgets["subtitle.position_y"] = {"widget": y_coord_widget, "type": "spinbox"}
        
        # 连接坐标变化事件
        x_coord_widget.valueChanged.connect(self._on_subtitle_coordinates_changed)
        y_coord_widget.valueChanged.connect(self._on_subtitle_coordinates_changed)
        
        position_mode_layout.addWidget(coords_widget)
        
        # 偏移微调
        offset_widget = QWidget()
        offset_layout = QFormLayout(offset_widget)
        
        # X偏移（微调）
        x_offset_widget = SpinBox()
        x_offset_widget.setRange(-1000, 1000)
        x_offset_widget.setValue(subtitle_config.get('display_offset_x', 0))
        offset_layout.addRow("X偏移微调:", x_offset_widget)
        self.widgets["subtitle.display_offset_x"] = {"widget": x_offset_widget, "type": "spinbox"}
        
        # Y偏移（微调）
        y_offset_widget = SpinBox()
        y_offset_widget.setRange(-1000, 1000)
        y_offset_widget.setValue(subtitle_config.get('display_offset_y', 0))
        offset_layout.addRow("Y偏移微调:", y_offset_widget)
        self.widgets["subtitle.display_offset_y"] = {"widget": y_offset_widget, "type": "spinbox"}
        
        # 连接偏移变化事件
        x_offset_widget.valueChanged.connect(self._on_subtitle_offset_changed)
        y_offset_widget.valueChanged.connect(self._on_subtitle_offset_changed)
        
        position_mode_layout.addWidget(offset_widget)
        
        display_form.addRow(position_mode_group)
        
        # 当前位置信息显示
        self.position_info_label = QLabel("当前设置信息将在这里显示")
        self.position_info_label.setStyleSheet("color: gray; font-size: 12px;")
        display_form.addRow("位置信息:", self.position_info_label)
        
        # 更新位置信息显示
        self._update_position_info()
        
        self.vBoxLayout.addWidget(display_group)
        
        # 测试按钮组
        test_group = QGroupBox("字幕测试")
        test_layout = QHBoxLayout(test_group)
        
        # 预览字幕按钮（独立测试）
        preview_subtitle_btn = PushButton("预览字幕")
        preview_subtitle_btn.setIcon(FIF.VIEW)
        preview_subtitle_btn.clicked.connect(self._preview_subtitle_display)
        test_layout.addWidget(preview_subtitle_btn)
        
        # 测试字幕按钮（主程序测试）
        test_subtitle_btn = PushButton("测试字幕")
        test_subtitle_btn.setIcon(FIF.PLAY)
        test_subtitle_btn.clicked.connect(self._test_subtitle_display)
        test_layout.addWidget(test_subtitle_btn)
        
        # 关闭字幕按钮
        close_subtitle_btn = PushButton("关闭所有字幕")
        close_subtitle_btn.setIcon(FIF.CLOSE)
        close_subtitle_btn.clicked.connect(self._close_current_subtitle)
        test_layout.addWidget(close_subtitle_btn)
        
        # 测试说明
        test_info_label = QLabel("预览：直接在UI界面测试 | 测试：发送到主程序测试")
        test_info_label.setStyleSheet("color: gray; font-size: 12px;")
        test_layout.addWidget(test_info_label)
        
        test_layout.addStretch()
        self.vBoxLayout.addWidget(test_group)
        
        # 字幕颜色设置组
        subtitle_color_group = QGroupBox("字幕颜色设置")
        subtitle_color_form = QFormLayout(subtitle_color_group)
        
        # 文本颜色
        self.subtitle_text_color_picker = ColorPickerWidget(self, "文本颜色", has_alpha=True)
        text_r = subtitle_config.get('text_color_r', 255)
        text_g = subtitle_config.get('text_color_g', 255)
        text_b = subtitle_config.get('text_color_b', 255)
        text_a = subtitle_config.get('text_color_a', 255)
        self.subtitle_text_color_picker.set_color(text_r, text_g, text_b, text_a)
        subtitle_color_form.addRow("文本颜色:", self.subtitle_text_color_picker)
        
        # 轮廓颜色
        self.subtitle_outline_color_picker = ColorPickerWidget(self, "轮廓颜色", has_alpha=True)
        outline_r = subtitle_config.get('outline_color_r', 0)
        outline_g = subtitle_config.get('outline_color_g', 0)
        outline_b = subtitle_config.get('outline_color_b', 0)
        outline_a = subtitle_config.get('outline_color_a', 200)
        self.subtitle_outline_color_picker.set_color(outline_r, outline_g, outline_b, outline_a)
        subtitle_color_form.addRow("轮廓颜色:", self.subtitle_outline_color_picker)
        
        # 背景颜色
        self.subtitle_bg_color_picker = ColorPickerWidget(self, "背景颜色", has_alpha=True)
        bg_r = subtitle_config.get('bg_color_r', 0)
        bg_g = subtitle_config.get('bg_color_g', 0)
        bg_b = subtitle_config.get('bg_color_b', 0)
        bg_a = subtitle_config.get('bg_color_a', 60)
        self.subtitle_bg_color_picker.set_color(bg_r, bg_g, bg_b, bg_a)
        subtitle_color_form.addRow("背景颜色:", self.subtitle_bg_color_picker)
        
        self.vBoxLayout.addWidget(subtitle_color_group)
        self.vBoxLayout.addStretch()

    def create_user_input_tab(self):
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 读取配置
        user_input_config = self.config_data.get('user_input', {})
        
        # 基础设置组
        basic_group = QGroupBox("基础设置")
        basic_form = QFormLayout(basic_group)
        
        # 基础设置字段
        basic_fields = [
            ("窗口宽度", "user_input.width", "spinbox", 400),
            ("窗口高度", "user_input.height", "spinbox", 150),
            ("字体", "user_input.font_family", "lineedit", "Microsoft YaHei"),
            ("字体大小", "user_input.font_size", "spinbox", 16),
            ("边框圆角", "user_input.border_radius", "spinbox", 10),
        ]
        
        for label, key_path, widget_type, default in basic_fields:
            # 获取当前值
            keys = key_path.split('.')
            value = self.config_data
            for key in keys:
                value = value.get(key, default)
            
            # 创建控件
            if widget_type == "lineedit":
                widget = LineEdit()
                widget.setText(str(value))
            elif widget_type == "spinbox":
                widget = SpinBox()
                widget.setRange(0, 999999)
                widget.setValue(int(value))
            
            basic_form.addRow(label, widget)
            self.widgets[key_path] = {"widget": widget, "type": widget_type}
        
        self.vBoxLayout.addWidget(basic_group)
        
        # 颜色设置组
        color_group = QGroupBox("颜色设置")
        color_form = QFormLayout(color_group)
        
        # 背景颜色
        self.bg_color_picker = ColorPickerWidget(self, "背景颜色", has_alpha=True)
        bg_r = user_input_config.get('bg_color_r', 40)
        bg_g = user_input_config.get('bg_color_g', 44)
        bg_b = user_input_config.get('bg_color_b', 52)
        bg_a = user_input_config.get('bg_color_a', 220)
        self.bg_color_picker.set_color(bg_r, bg_g, bg_b, bg_a)
        color_form.addRow("背景颜色:", self.bg_color_picker)
        
        # 文字颜色（无透明度）
        self.text_color_picker = ColorPickerWidget(self, "文字颜色", has_alpha=False)
        text_r = user_input_config.get('text_color_r', 220)
        text_g = user_input_config.get('text_color_g', 220)
        text_b = user_input_config.get('text_color_b', 220)
        self.text_color_picker.set_color(text_r, text_g, text_b)
        color_form.addRow("文字颜色:", self.text_color_picker)
        
        # 边框颜色（无透明度）
        self.border_color_picker = ColorPickerWidget(self, "边框颜色", has_alpha=False)
        border_r = user_input_config.get('border_color_r', 86)
        border_g = user_input_config.get('border_color_g', 182)
        border_b = user_input_config.get('border_color_b', 194)
        self.border_color_picker.set_color(border_r, border_g, border_b)
        color_form.addRow("边框颜色:", self.border_color_picker)
        
        # 输入框背景颜色
        self.status_bg_color_picker = ColorPickerWidget(self, "输入框背景颜色", has_alpha=True)
        status_r = user_input_config.get('status_bg_color_r', 60)
        status_g = user_input_config.get('status_bg_color_g', 60)
        status_b = user_input_config.get('status_bg_color_b', 70)
        status_a = user_input_config.get('status_bg_color_a', 220)
        self.status_bg_color_picker.set_color(status_r, status_g, status_b, status_a)
        color_form.addRow("输入框背景颜色:", self.status_bg_color_picker)
        
        self.vBoxLayout.addWidget(color_group)
        self.vBoxLayout.addStretch()

    def create_animation_tab(self):
        """创建动画操控标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 主要布局 - 水平分割
        main_splitter = QSplitter(Qt.Horizontal)
        
        # === 左侧：操控面板 ===
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 快捷操控组
        quick_group = QGroupBox("快捷操控")
        quick_layout = QVBoxLayout(quick_group)
        
        # 快捷按钮布局
        quick_buttons_layout = QHBoxLayout()
        
        # 唱歌控制按钮
        self.start_singing_btn = PrimaryToolButton(FIF.PLAY)
        self.start_singing_btn.setText("开始唱歌")
        self.start_singing_btn.setToolTip("播放唱歌动画")
        self.start_singing_btn.clicked.connect(lambda: self.trigger_live2d_motion(5))
        
        self.stop_singing_btn = ToolButton(FIF.PAUSE)
        self.stop_singing_btn.setText("停止唱歌")
        self.stop_singing_btn.setToolTip("停止唱歌动画")
        self.stop_singing_btn.clicked.connect(lambda: self.trigger_live2d_motion(7))
        
        quick_buttons_layout.addWidget(self.start_singing_btn)
        quick_buttons_layout.addWidget(self.stop_singing_btn)
        quick_buttons_layout.addStretch()
        
        # 其他快捷动作按钮
        self.random_motion_btn = ToolButton(FIF.PLAY)
        self.random_motion_btn.setText("随机动作")
        self.random_motion_btn.setToolTip("播放随机动作")
        self.random_motion_btn.clicked.connect(self.trigger_random_motion)
        
        self.stop_all_motion_btn = ToolButton(FIF.PAUSE)
        self.stop_all_motion_btn.setText("停止所有动作")
        self.stop_all_motion_btn.setToolTip("停止所有正在播放的动作")
        self.stop_all_motion_btn.clicked.connect(self.stop_all_live2d_motions)
        
        quick_buttons_layout.addWidget(self.random_motion_btn)
        quick_buttons_layout.addWidget(self.stop_all_motion_btn)
        
        quick_layout.addLayout(quick_buttons_layout)
        control_layout.addWidget(quick_group)
        
        # 表情控制组
        expression_group = QGroupBox("表情控制")
        expression_layout = QVBoxLayout(expression_group)
        
        # 表情快捷按钮
        expr_buttons_layout = QHBoxLayout()
        
        self.random_expression_btn = PrimaryToolButton(FIF.PLAY)
        self.random_expression_btn.setText("随机表情")
        self.random_expression_btn.setToolTip("设置随机表情")
        self.random_expression_btn.clicked.connect(self.trigger_random_expression)
        
        self.reset_expression_btn = ToolButton(FIF.CLOSE)
        self.reset_expression_btn.setText("重置表情")
        self.reset_expression_btn.setToolTip("重置为默认表情")
        self.reset_expression_btn.clicked.connect(self.reset_live2d_expression)
        
        expr_buttons_layout.addWidget(self.random_expression_btn)
        expr_buttons_layout.addWidget(self.reset_expression_btn)
        expr_buttons_layout.addStretch()
        
        expression_layout.addLayout(expr_buttons_layout)
        control_layout.addWidget(expression_group)
        
        # 模型状态组
        status_group = QGroupBox("模型状态")
        status_layout = QVBoxLayout(status_group)
        
        self.model_status_label = QLabel("Live2D状态：检查中...")
        self.model_status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_layout.addWidget(self.model_status_label)
        
        # 刷新按钮
        refresh_layout = QHBoxLayout()
        self.refresh_model_btn = ToolButton(FIF.UPDATE)
        self.refresh_model_btn.setText("刷新模型信息")
        self.refresh_model_btn.setToolTip("重新加载当前模型的表情和动作列表")
        self.refresh_model_btn.clicked.connect(self.refresh_live2d_model_info)
        
        refresh_layout.addWidget(self.refresh_model_btn)
        refresh_layout.addStretch()
        status_layout.addLayout(refresh_layout)
        
        control_layout.addWidget(status_group)
        control_layout.addStretch()
        
        # === 右侧：表情和动作列表 ===
        lists_widget = QWidget()
        lists_layout = QVBoxLayout(lists_widget)
        
        # 表情列表
        expr_list_group = QGroupBox("可用表情列表")
        expr_list_layout = QVBoxLayout(expr_list_group)
        
        expr_info_layout = QHBoxLayout()
        expr_info_layout.addWidget(QLabel("双击表情名称播放"))
        
        self.expression_count_label = QLabel("表情数量: 0")
        self.expression_count_label.setStyleSheet("color: #666; font-size: 11px;")
        expr_info_layout.addStretch()
        expr_info_layout.addWidget(self.expression_count_label)
        
        expr_list_layout.addLayout(expr_info_layout)
        
        self.animation_expression_list = QListWidget()
        self.animation_expression_list.setMinimumHeight(200)
        self.animation_expression_list.itemDoubleClicked.connect(self.on_animation_expression_click)
        self.animation_expression_list.setToolTip("双击表情名称播放对应表情")
        expr_list_layout.addWidget(self.animation_expression_list)
        
        lists_layout.addWidget(expr_list_group)
        
        # 动作列表
        motion_list_group = QGroupBox("可用动作列表")
        motion_list_layout = QVBoxLayout(motion_list_group)
        
        motion_info_layout = QHBoxLayout()
        motion_info_layout.addWidget(QLabel("双击动作名称播放"))
        
        self.motion_count_label = QLabel("动作数量: 0")
        self.motion_count_label.setStyleSheet("color: #666; font-size: 11px;")
        motion_info_layout.addStretch()
        motion_info_layout.addWidget(self.motion_count_label)
        
        motion_list_layout.addLayout(motion_info_layout)
        
        self.animation_motion_list = QListWidget()
        self.animation_motion_list.setMinimumHeight(200)
        self.animation_motion_list.itemDoubleClicked.connect(self.on_animation_motion_click)
        self.animation_motion_list.setToolTip("双击动作名称播放对应动作")
        motion_list_layout.addWidget(self.animation_motion_list)
        
        lists_layout.addWidget(motion_list_group)
        
        # 将控制面板和列表添加到分割器
        main_splitter.addWidget(control_widget)
        main_splitter.addWidget(lists_widget)
        
        # 设置分割器比例 (控制面板:列表 = 1:2)
        main_splitter.setSizes([300, 600])
        
        self.vBoxLayout.addWidget(main_splitter)
        
        # 初始化时加载模型信息
        self.refresh_live2d_model_info()

    def create_other_tab(self):
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.create_rag_tab()
        self.create_mcp_tab()
        self.create_memory_tab()
        self.create_vision_tab()
        self.create_bilibili_tab()
        self.create_auto_chat_tab()


    def create_rag_tab(self):
        """创建RAG配置标签页"""
        fields = [
            ("RAG URL", "rag.rag_url", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "RAG配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_mcp_tab(self):
        """创建MCP配置标签页 - 使用标准MCP服务器管理器"""
        # 创建MCP服务器管理器
        self.mcp_manager = MCPToolManager(self)
        self.vBoxLayout.addWidget(self.mcp_manager)
        
        # 传统配置兼容性说明
        compat_group = QGroupBox("兼容性说明")
        compat_layout = QVBoxLayout(compat_group)
        
        compat_text = QLabel(
            "系统已自动将旧的 urls/paths 配置转换为标准的 mcpServers 格式。\n"
            "新的配置保存在 config.json 的 mcp.mcpServers 下，支持 stdio、sse、streamablehttp 和 python 四种传输方式。"
        )
        compat_text.setWordWrap(True)
        compat_text.setStyleSheet("color: #666; font-size: 12px;")
        compat_layout.addWidget(compat_text)
        
        self.vBoxLayout.addWidget(compat_group)
        self.vBoxLayout.addStretch()

    def create_memory_tab(self):
        """创建记忆配置标签页"""
        fields = [
            ("文件路径", "memory.file_path", "lineedit", ""),
            ("检查URL", "memory.check_url", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "记忆配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_vision_tab(self):
        """创建视觉配置标签页"""
        fields = [
            ("检查URL", "vision.check_url", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "视觉配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_bilibili_tab(self):
        """创建B站配置标签页"""
        fields = [
            ("房间ID", "bilibili.roomId", "lineedit", ""),
            ("检查间隔", "bilibili.checkInterval", "spinbox", 5000),
            ("最大消息数", "bilibili.maxMessages", "spinbox", 50),
            ("API URL", "bilibili.apiUrl", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "B站配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_auto_chat_tab(self):
        """创建自动聊天配置标签页"""
        fields = [
            ("间隔", "auto_chat.interval", "spinbox", 5000),
            ("最小间隔", "auto_chat.min_interval", "spinbox", 30000),
            ("最大间隔", "auto_chat.max_interval", "spinbox", 180000),
            ("空闲时间", "auto_chat.idle_time", "spinbox", 15000)
        ]
        
        group = self.create_form_group(self, "自动聊天配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_setting_tab(self):
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        fields = [
            ("LLM开关", "setting.llm_enabled", "checkbox", True),
            ("提示词增强开关(未完成)", "setting.prompt_enabled", "checkbox", True),
            ("TTS开关", "setting.tts_enabled", "checkbox", True),
            ("ASR开关", "setting.asr_enabled", "checkbox", True),
            ("Live2d开关", "setting.ui_enabled", "checkbox", True),
            ("字幕开关", "setting.subtitle_enabled", "checkbox", True),
            ("输入框开关", "setting.user_input_enabled", "checkbox", True),
            ("动作按钮开关", "setting.action_buttons_enabled", "checkbox", False),
            ("RAG开关", "setting.rag_enabled", "checkbox", True),
            ("MCP开关", "setting.mcp_enabled", "checkbox", True),
            ("视觉开关", "setting.vision_enabled", "checkbox", True),
            ("记忆开关", "setting.memory_enabled", "checkbox", True),
            ("主动对话开关", "setting.auto_chat_enabled", "checkbox", True),
            ("B站直播开关", "setting.bilibili_enabled", "checkbox", False),
        ]
        
        group = self.create_form_group(self, "项目设置", fields)
        
        # 为动作按钮开关添加状态变化处理
        if 'setting.action_buttons_enabled' in self.widgets:
            action_buttons_checkbox = self.widgets['setting.action_buttons_enabled']['widget']
            action_buttons_checkbox.stateChanged.connect(self.on_action_buttons_enabled_changed)
        
        self.vBoxLayout.addWidget(group)
        
        # WebAPI输入配置组
        webapi_group = QGroupBox("WebAPI输入设置")
        webapi_form = QFormLayout(webapi_group)
        
        # WebAPI开关
        webapi_enabled_check = CheckBox()
        webapi_enabled_check.setChecked(bool(self.config_data.get('webapi', {}).get('enabled', False)))
        self.widgets['webapi.enabled'] = {"widget": webapi_enabled_check, "type": "checkbox"}
        webapi_form.addRow("启用WebAPI输入:", webapi_enabled_check)
        
        # 自动启动WebAPI开关
        webapi_auto_start_check = CheckBox()
        webapi_auto_start_check.setChecked(bool(self.config_data.get('webapi', {}).get('auto_start', False)))
        self.widgets['webapi.auto_start'] = {"widget": webapi_auto_start_check, "type": "checkbox"}
        webapi_form.addRow("自动启动WebAPI:", webapi_auto_start_check)
        
        # 端口设置
        webapi_port_spin = SpinBox()
        webapi_port_spin.setRange(1000, 65535)
        webapi_port_spin.setValue(self.config_data.get('webapi', {}).get('port', 8888))
        self.widgets['webapi.port'] = {"widget": webapi_port_spin, "type": "spinbox"}
        webapi_form.addRow("监听端口:", webapi_port_spin)
        
        # 绑定地址
        webapi_host_edit = LineEdit()
        webapi_host_edit.setText(self.config_data.get('webapi', {}).get('host', '127.0.0.1'))
        webapi_host_edit.setPlaceholderText("0.0.0.0 表示监听所有网卡")
        self.widgets['webapi.host'] = {"widget": webapi_host_edit, "type": "lineedit"}
        webapi_form.addRow("绑定地址:", webapi_host_edit)
        
        # API密钥
        webapi_key_edit = PasswordLineEdit()
        webapi_key_edit.setText(self.config_data.get('webapi', {}).get('api_key', ''))
        webapi_key_edit.setPlaceholderText("可选：用于验证请求的API密钥")
        self.widgets['webapi.api_key'] = {"widget": webapi_key_edit, "type": "passwordlineedit"}
        webapi_form.addRow("API密钥 (可选):", webapi_key_edit)
        
        # 服务状态显示
        self.webapi_status_label = QLabel("服务状态: 未启动")
        self.webapi_status_label.setStyleSheet("color: #666;")
        webapi_form.addRow("", self.webapi_status_label)
        
        # 控制按钮
        webapi_btn_layout = QHBoxLayout()
        
        # WebAPI服务按钮 - 使用合适的图标和按钮类型
        self.webapi_start_btn = PrimaryToolButton(FIF.PLAY)
        self.webapi_start_btn.setText("启动服务")
        self.webapi_start_btn.setToolTip("启动WebAPI服务器，监听HTTP请求")
        
        self.webapi_stop_btn = ToolButton(FIF.PAUSE)
        self.webapi_stop_btn.setText("停止服务")
        self.webapi_stop_btn.setToolTip("停止WebAPI服务器")
        
        self.webapi_test_btn = ToolButton(FIF.SEND)
        self.webapi_test_btn.setText("测试API")
        self.webapi_test_btn.setToolTip("发送测试请求验证API服务")
        
        # 连接按钮事件
        self.webapi_start_btn.clicked.connect(self.start_webapi_server)
        self.webapi_stop_btn.clicked.connect(self.stop_webapi_server)
        self.webapi_test_btn.clicked.connect(self.test_webapi)
        
        webapi_btn_layout.addWidget(self.webapi_start_btn)
        webapi_btn_layout.addWidget(self.webapi_stop_btn)
        webapi_btn_layout.addWidget(self.webapi_test_btn)
        webapi_form.addRow("", webapi_btn_layout)
        
        # 使用说明
        webapi_help_text = QTextEdit()
        webapi_help_text.setMaximumHeight(120)
        webapi_help_text.setReadOnly(True)
        webapi_help_text.setPlainText(
            "WebAPI使用说明:\n"
            "POST /api/chat\n"
            "Content-Type: application/json\n"
            "{\n"
            '  "message": "你好",\n'
            '  "api_key": "你的密钥" (如果设置了密钥)\n'
            "}\n\n"
            "返回: {\"response\": \"LLM回复内容\", \"status\": \"success\"}"
        )
        webapi_form.addRow("使用说明:", webapi_help_text)
        
        self.vBoxLayout.addWidget(webapi_group)
        
        # 日志管理配置组
        log_group = QGroupBox("日志管理")
        log_form = QFormLayout(log_group)
        
        # 日志状态显示
        self.log_status_label = QLabel("日志文件状态: 正常")
        self.log_status_label.setStyleSheet("color: #666;")
        log_form.addRow("", self.log_status_label)
        
        # 更新日志状态
        self._update_log_status()
        
        # 控制按钮
        log_btn_layout = QHBoxLayout()
        
        # 保存日志包按钮 - 使用PrimaryToolButton表示主要操作
        self.save_logs_btn = PrimaryToolButton(FIF.SAVE)
        self.save_logs_btn.setText("保存日志包")
        self.save_logs_btn.setToolTip("将所有日志文件和系统信息打包保存为ZIP文件")
        
        # 清空日志按钮 - 使用ToolButton表示危险操作
        self.clear_logs_btn = ToolButton(FIF.DELETE)
        self.clear_logs_btn.setText("清空日志")
        self.clear_logs_btn.setToolTip("清空所有日志文件的内容，释放磁盘空间")
        
        # 查看日志目录按钮 - 使用ToolButton表示辅助操作
        self.view_logs_btn = ToolButton(FIF.FOLDER)
        self.view_logs_btn.setText("查看日志目录")
        self.view_logs_btn.setToolTip("在文件管理器中打开logs文件夹")
        
        # 连接按钮事件
        self.save_logs_btn.clicked.connect(self.save_logs_package)
        self.clear_logs_btn.clicked.connect(self.clear_all_logs)
        self.view_logs_btn.clicked.connect(self.view_logs_directory)
        
        log_btn_layout.addWidget(self.save_logs_btn)
        log_btn_layout.addWidget(self.clear_logs_btn)
        log_btn_layout.addWidget(self.view_logs_btn)
        log_form.addRow("操作:", log_btn_layout)
        
        # 日志说明
        log_help_text = QTextEdit()
        log_help_text.setMaximumHeight(100)
        log_help_text.setReadOnly(True)
        log_help_text.setPlainText(
            "日志管理说明:\n"
            "• 保存日志包: 打包所有日志文件和系统信息为ZIP文件\n"
            "• 清空日志: 删除所有日志文件内容，释放磁盘空间\n"
            "• 查看日志目录: 打开logs文件夹查看详细日志文件"
        )
        log_form.addRow("说明:", log_help_text)
        
        self.vBoxLayout.addWidget(log_group)
        
        # 系统信息显示组
        system_info_group = QGroupBox("系统信息")
        system_info_form = QFormLayout(system_info_group)
        
        # 系统信息显示区域
        self.system_info_display = QTextEdit()
        self.system_info_display.setReadOnly(True)
        self.system_info_display.setMaximumHeight(300)
        self.system_info_display.setStyleSheet("QTextEdit { background-color: #f5f5f5; font-family: 'Consolas', monospace; }")
        
        # 获取并显示系统信息
        system_info_text = self._get_detailed_system_info()
        self.system_info_display.setPlainText(system_info_text)
        
        system_info_form.addRow("", self.system_info_display)
        
        # 刷新按钮
        refresh_system_info_btn = ToolButton(FIF.SYNC)
        refresh_system_info_btn.setText("刷新系统信息")
        refresh_system_info_btn.setToolTip("重新获取并更新系统硬件信息")
        refresh_system_info_btn.clicked.connect(self._refresh_system_info)
        system_info_form.addRow("", refresh_system_info_btn)
        
        self.vBoxLayout.addWidget(system_info_group)
        
        # 音频设备配置组
        audio_device_group = QGroupBox("音频设备设置")
        audio_device_form = QFormLayout(audio_device_group)
        
        # 当前系统音频设备显示
        self.current_audio_device_label = QLabel("正在检测...")
        self.current_audio_device_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        audio_device_form.addRow("当前系统音频设备:", self.current_audio_device_label)
        
        # 音频设备选择下拉框
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setMinimumWidth(300)
        self.widgets['audio.device_index'] = {"widget": self.audio_device_combo, "type": "combobox"}
        audio_device_form.addRow("选择音频输出设备:", self.audio_device_combo)
        
        # 音量控制
        self.audio_volume_spin = DoubleSpinBox()
        self.audio_volume_spin.setRange(0.0, 2.0)
        self.audio_volume_spin.setValue(self.config_data.get('audio', {}).get('volume', 1.0))
        self.audio_volume_spin.setSingleStep(0.1)
        self.audio_volume_spin.setDecimals(1)
        self.audio_volume_spin.setSuffix("x")
        self.widgets['audio.volume'] = {"widget": self.audio_volume_spin, "type": "doublespinbox"}
        audio_device_form.addRow("音量:", self.audio_volume_spin)
        
        # 控制按钮
        audio_btn_layout = QHBoxLayout()
        
        # 刷新设备列表按钮
        self.refresh_audio_devices_btn = ToolButton(FIF.SYNC)
        self.refresh_audio_devices_btn.setText("刷新设备")
        self.refresh_audio_devices_btn.setToolTip("重新扫描可用的音频输出设备")
        self.refresh_audio_devices_btn.clicked.connect(self.refresh_audio_devices)
        
        # 测试音频按钮
        self.test_audio_btn = PrimaryToolButton(FIF.PLAY)
        self.test_audio_btn.setText("测试音频")
        self.test_audio_btn.setToolTip("播放测试音频验证设备是否正常工作")
        self.test_audio_btn.clicked.connect(self.test_audio_device)
        
        # 停止测试按钮
        self.stop_test_audio_btn = ToolButton(FIF.PAUSE)
        self.stop_test_audio_btn.setText("停止测试")
        self.stop_test_audio_btn.setToolTip("停止当前的音频测试")
        self.stop_test_audio_btn.clicked.connect(self.stop_test_audio)
        self.stop_test_audio_btn.setEnabled(False)
        
        audio_btn_layout.addWidget(self.refresh_audio_devices_btn)
        audio_btn_layout.addWidget(self.test_audio_btn)
        audio_btn_layout.addWidget(self.stop_test_audio_btn)
        audio_device_form.addRow("操作:", audio_btn_layout)
        
        # 音频设备信息显示
        self.audio_device_info = QTextEdit()
        self.audio_device_info.setReadOnly(True)
        self.audio_device_info.setMaximumHeight(120)
        self.audio_device_info.setStyleSheet("QTextEdit { background-color: #f5f5f5; font-family: 'Consolas', monospace; font-size: 10pt; }")
        audio_device_form.addRow("设备信息:", self.audio_device_info)
        
        # 初始化音频设备列表
        self.refresh_audio_devices()
        
        self.vBoxLayout.addWidget(audio_device_group)
        self.vBoxLayout.addStretch()

    def _get_detailed_system_info(self):
        """获取详细的系统信息"""
        try:
            import platform
            import subprocess
            try:
                import psutil
                HAS_PSUTIL = True
            except ImportError:
                HAS_PSUTIL = False
            
            info = []
            
            # === 基本系统信息 ===
            info.append("=== 基本系统信息 ===")
            info.append(f"操作系统: {platform.system()} {platform.release()} ({platform.version()})")
            info.append(f"计算机名: {platform.node()}")
            info.append(f"处理器架构: {platform.machine()}")
            info.append(f"Python版本: {platform.python_version()}")
            info.append("")
            
            # === CPU信息 ===
            info.append("=== CPU信息 ===")
            if HAS_PSUTIL:
                try:
                    info.append(f"处理器: {platform.processor()}")
                    info.append(f"物理核心数: {psutil.cpu_count(logical=False)}")
                    info.append(f"逻辑核心数: {psutil.cpu_count(logical=True)}")
                    cpu_freq = psutil.cpu_freq()
                    if cpu_freq:
                        info.append(f"CPU频率: {cpu_freq.current:.2f} MHz (最大: {cpu_freq.max:.2f} MHz)")
                    info.append(f"CPU使用率: {psutil.cpu_percent(interval=1):.1f}%")
                except Exception as e:
                    info.append(f"CPU信息获取失败: {e}")
            else:
                info.append(f"处理器: {platform.processor()}")
                info.append("详细CPU信息需要psutil库")
            info.append("")
            
            # === 内存信息 ===
            info.append("=== 内存信息 ===")
            if HAS_PSUTIL:
                try:
                    memory = psutil.virtual_memory()
                    info.append(f"总内存: {memory.total / (1024**3):.2f} GB")
                    info.append(f"可用内存: {memory.available / (1024**3):.2f} GB")
                    info.append(f"已用内存: {memory.used / (1024**3):.2f} GB")
                    info.append(f"内存使用率: {memory.percent:.1f}%")
                    
                    # 交换内存
                    swap = psutil.swap_memory()
                    info.append(f"交换内存总量: {swap.total / (1024**3):.2f} GB")
                    info.append(f"交换内存使用率: {swap.percent:.1f}%")
                except Exception as e:
                    info.append(f"内存信息获取失败: {e}")
            else:
                info.append("内存信息需要psutil库")
            info.append("")
            
            # === 显卡信息 ===
            info.append("=== 显卡信息 ===")
            try:
                # 尝试获取NVIDIA GPU信息
                try:
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,cuda_version', '--format=csv,noheader,nounits'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        gpu_lines = result.stdout.strip().split('\n')
                        for i, line in enumerate(gpu_lines):
                            parts = line.split(', ')
                            if len(parts) >= 4:
                                info.append(f"GPU {i+1}: {parts[0]}")
                                info.append(f"  显存: {parts[1]} MB")
                                info.append(f"  驱动版本: {parts[2]}")
                                info.append(f"  CUDA版本: {parts[3]}")
                    else:
                        info.append("未检测到NVIDIA显卡或nvidia-smi不可用")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    info.append("NVIDIA GPU信息获取失败 (nvidia-smi不可用)")
                
                # 尝试通过wmic获取显卡信息 (Windows)
                if platform.system() == "Windows":
                    try:
                        result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,AdapterRAM'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                            for line in lines:
                                line = line.strip()
                                if line and 'AdapterRAM' not in line:
                                    parts = line.split()
                                    if len(parts) >= 2:
                                        ram_bytes = parts[0] if parts[0].isdigit() else "N/A"
                                        gpu_name = ' '.join(parts[1:]) if len(parts) > 1 else "未知显卡"
                                        if ram_bytes != "N/A" and ram_bytes.isdigit():
                                            ram_mb = int(ram_bytes) // (1024*1024)
                                            info.append(f"显卡: {gpu_name} (显存: {ram_mb} MB)")
                                        else:
                                            info.append(f"显卡: {gpu_name}")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        info.append("Windows显卡信息获取失败")
                        
            except Exception as e:
                info.append(f"显卡信息获取失败: {e}")
            info.append("")
            
            # === CUDA信息 ===
            info.append("=== CUDA信息 ===")
            try:
                # 检查CUDA版本
                try:
                    result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'release' in line.lower():
                                info.append(f"NVCC版本: {line.strip()}")
                                break
                    else:
                        info.append("NVCC不可用")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    info.append("NVCC未安装或不在PATH中")
                
                # 尝试通过PyTorch检查CUDA
                try:
                    import torch
                    info.append(f"PyTorch CUDA可用: {torch.cuda.is_available()}")
                    if torch.cuda.is_available():
                        info.append(f"PyTorch CUDA版本: {torch.version.cuda}")
                        info.append(f"可用GPU数量: {torch.cuda.device_count()}")
                        for i in range(torch.cuda.device_count()):
                            info.append(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
                except ImportError:
                    info.append("PyTorch未安装，无法检查CUDA状态")
                except Exception as e:
                    info.append(f"PyTorch CUDA检查失败: {e}")
                    
            except Exception as e:
                info.append(f"CUDA信息获取失败: {e}")
            info.append("")
            
            # === 声卡信息 ===
            info.append("=== 声卡信息 ===")
            try:
                if platform.system() == "Windows":
                    try:
                        result = subprocess.run(['wmic', 'sounddev', 'get', 'name'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                            audio_devices = [line.strip() for line in lines if line.strip() and 'Name' not in line]
                            for device in audio_devices:
                                if device:
                                    info.append(f"声卡: {device}")
                        else:
                            info.append("Windows声卡信息获取失败")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        info.append("Windows声卡信息获取失败 (wmic不可用)")
                else:
                    info.append("仅支持Windows系统的声卡信息获取")
                    
            except Exception as e:
                info.append(f"声卡信息获取失败: {e}")
            info.append("")
            
            # === 网络信息 ===
            info.append("=== 网络信息 ===")
            try:
                import socket
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                info.append(f"主机名: {hostname}")
                info.append(f"本地IP: {local_ip}")
                
                if HAS_PSUTIL:
                    try:
                        # 网络接口信息
                        net_if_addrs = psutil.net_if_addrs()
                        for interface, addrs in net_if_addrs.items():
                            for addr in addrs:
                                if addr.family == socket.AF_INET:  # IPv4
                                    info.append(f"网络接口 {interface}: {addr.address}")
                    except Exception as e:
                        info.append(f"网络接口信息获取失败: {e}")
                        
            except Exception as e:
                info.append(f"网络信息获取失败: {e}")
            info.append("")
            
            # === 存储信息 ===
            info.append("=== 存储信息 ===")
            if HAS_PSUTIL:
                try:
                    partitions = psutil.disk_partitions()
                    for partition in partitions:
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            info.append(f"磁盘 {partition.device}:")
                            info.append(f"  文件系统: {partition.fstype}")
                            info.append(f"  总空间: {usage.total / (1024**3):.2f} GB")
                            info.append(f"  已用空间: {usage.used / (1024**3):.2f} GB")
                            info.append(f"  可用空间: {usage.free / (1024**3):.2f} GB")
                            info.append(f"  使用率: {(usage.used / usage.total) * 100:.1f}%")
                        except PermissionError:
                            info.append(f"磁盘 {partition.device}: 权限不足")
                except Exception as e:
                    info.append(f"存储信息获取失败: {e}")
            else:
                info.append("存储信息需要psutil库")
            
            info.append("")
            info.append(f"信息更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(info)
            
        except Exception as e:
            return f"系统信息获取失败: {e}"
    
    def _refresh_system_info(self):
        """刷新系统信息显示"""
        try:
            system_info_text = self._get_detailed_system_info()
            self.system_info_display.setPlainText(system_info_text)
            
            InfoBar.success(
                title="刷新成功",
                content="系统信息已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title="刷新失败",
                content=f"系统信息刷新失败: {e}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def on_action_buttons_enabled_changed(self, state):
        """处理动作按钮开关状态变化"""
        try:
            enabled = state == Qt.Checked

            # 更新配置
            self.config_data.setdefault('setting', {})['action_buttons_enabled'] = enabled

            # 通过socket发送信号给main.py来控制动作按钮显示
            try:
                import socket
                import json
                import time
                
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(2.0)
                client_socket.connect(('127.0.0.1', 8889))
                
                signal_data = {
                    "type": "show_action_buttons" if enabled else "hide_action_buttons",
                    "timestamp": time.time(),
                    "source": "ui_action_buttons_toggle"
                }
                
                client_socket.send(json.dumps(signal_data).encode('utf-8'))
                client_socket.close()
                
                if self.logger:
                    self.logger.info(f"已发送动作按钮{'显示' if enabled else '隐藏'}信号给main.py")
                    
            except (socket.timeout, socket.error) as e:
                if self.logger:
                    self.logger.warning(f"发送动作按钮控制信号失败: {e}")

            # 显示状态提示
            status_text = "已启用" if enabled else "已禁用"
            note_text = " (BAT运行时生效)" if not (hasattr(self, 'bat_worker') and self.bat_worker and self.bat_worker.isRunning()) else ""
            InfoBar.info(
                title='动作按钮设置',
                content=f"动作按钮悬浮窗口{status_text}{note_text}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            print(f"处理动作按钮开关状态变化失败: {e}")

    def _update_log_status(self):
        """更新日志状态显示"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                self.log_status_label.setText("日志文件状态: 日志目录不存在")
                self.log_status_label.setStyleSheet("color: #d83b01;")
                return
            
            log_files = [
                "llm_interactions.log",
                "asr_interactions.log", 
                "tts_interactions.log",
                "webapi_interactions.log"
            ]
            
            total_size = 0
            file_count = 0
            
            for log_file in log_files:
                log_path = os.path.join(log_dir, log_file)
                if os.path.exists(log_path):
                    file_count += 1
                    total_size += os.path.getsize(log_path)
            
            # 格式化文件大小
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            
            self.log_status_label.setText(f"日志文件状态: {file_count}个文件, 总大小 {size_str}")
            self.log_status_label.setStyleSheet("color: #666;")
            
        except Exception as e:
            self.log_status_label.setText(f"日志文件状态: 检查失败 ({str(e)})")
            self.log_status_label.setStyleSheet("color: #d83b01;")

    def save_logs_package(self):
        """保存日志包到用户选择的位置"""
        try:
            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存日志包",
                f"ai_live2d_logs_{time.strftime('%Y%m%d_%H%M%S')}.zip",
                "ZIP文件 (*.zip)"
            )
            
            if not file_path:
                return
            
            # 显示进度提示
            InfoBar.info(
                title='正在打包',
                content='正在收集日志和系统信息...',
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            import zipfile
            import platform
            try:
                import psutil
                HAS_PSUTIL = True
            except ImportError:
                HAS_PSUTIL = False
            
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. 添加所有日志文件
                log_dir = "logs"
                if os.path.exists(log_dir):
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            if file.endswith('.log'):
                                file_path_in_logs = os.path.join(root, file)
                                arcname = os.path.relpath(file_path_in_logs, ".")
                                zipf.write(file_path_in_logs, arcname)
                
                # 2. 添加配置文件
                config_files = ["config.json", "config_example.json"]
                for config_file in config_files:
                    if os.path.exists(config_file):
                        zipf.write(config_file, config_file)
                
                # 3. 添加其他重要日志文件
                other_logs = ["chat_log.txt", "pet_system.log"]
                for log_file in other_logs:
                    if os.path.exists(log_file):
                        zipf.write(log_file, log_file)
                
                # 4. 生成系统信息文件
                system_info = self._collect_system_info()
                zipf.writestr("system_info.txt", system_info)
                
                # 5. 生成运行状态文件
                runtime_info = self._collect_runtime_info()
                zipf.writestr("runtime_info.txt", runtime_info)
            
            # 更新日志状态
            self._update_log_status()
            
            InfoBar.success(
                title='保存成功',
                content=f'日志包已保存到: {file_path}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='保存失败',
                content=f'保存日志包时出错: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _collect_system_info(self):
        """收集系统信息"""
        try:
            import platform
            import subprocess
            try:
                import psutil
                HAS_PSUTIL = True
            except ImportError:
                HAS_PSUTIL = False
            
            info = []
            info.append("=== 系统信息 ===")
            info.append(f"操作系统: {platform.system()} {platform.release()}")
            info.append(f"处理器: {platform.processor()}")
            info.append(f"Python版本: {platform.python_version()}")
            info.append(f"架构: {platform.machine()}")
            info.append("")
            
            info.append("=== 硬件信息 ===")
            if HAS_PSUTIL:
                try:
                    # CPU信息
                    info.append(f"CPU核心数: {psutil.cpu_count(logical=False)} 物理核心, {psutil.cpu_count(logical=True)} 逻辑核心")
                    info.append(f"CPU使用率: {psutil.cpu_percent(interval=1)}%")
                    
                    # 内存信息
                    memory = psutil.virtual_memory()
                    info.append(f"总内存: {memory.total / (1024**3):.2f} GB")
                    info.append(f"可用内存: {memory.available / (1024**3):.2f} GB")
                    info.append(f"内存使用率: {memory.percent}%")
                    
                    # 磁盘信息
                    disk = psutil.disk_usage('.')
                    info.append(f"磁盘总空间: {disk.total / (1024**3):.2f} GB")
                    info.append(f"磁盘可用空间: {disk.free / (1024**3):.2f} GB")
                    info.append(f"磁盘使用率: {(disk.used / disk.total) * 100:.1f}%")
                    
                except Exception as e:
                    info.append(f"硬件信息收集失败: {e}")
            else:
                info.append("硬件信息收集需要psutil库，当前未安装")
            
            # === 显卡信息 ===
            info.append("")
            info.append("=== 显卡信息 ===")
            try:
                # 尝试获取NVIDIA GPU信息
                try:
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,cuda_version', '--format=csv,noheader,nounits'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        gpu_lines = result.stdout.strip().split('\n')
                        for i, line in enumerate(gpu_lines):
                            parts = line.split(', ')
                            if len(parts) >= 4:
                                info.append(f"NVIDIA GPU {i+1}: {parts[0]}")
                                info.append(f"  显存: {parts[1]} MB")
                                info.append(f"  驱动版本: {parts[2]}")
                                info.append(f"  CUDA版本: {parts[3]}")
                    else:
                        info.append("未检测到NVIDIA显卡或nvidia-smi不可用")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    info.append("NVIDIA GPU信息获取失败 (nvidia-smi不可用)")
                
                # 尝试通过wmic获取显卡信息 (Windows)
                if platform.system() == "Windows":
                    try:
                        result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,AdapterRAM'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                            for line in lines:
                                line = line.strip()
                                if line and 'AdapterRAM' not in line:
                                    parts = line.split()
                                    if len(parts) >= 2:
                                        ram_bytes = parts[0] if parts[0].isdigit() else "N/A"
                                        gpu_name = ' '.join(parts[1:]) if len(parts) > 1 else "未知显卡"
                                        if ram_bytes != "N/A" and ram_bytes.isdigit():
                                            ram_mb = int(ram_bytes) // (1024*1024)
                                            info.append(f"显卡: {gpu_name} (显存: {ram_mb} MB)")
                                        else:
                                            info.append(f"显卡: {gpu_name}")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass  # 已经有NVIDIA信息，这里的失败不需要额外提示
                        
                # CUDA信息
                try:
                    import torch
                    if torch.cuda.is_available():
                        info.append(f"PyTorch CUDA可用: 是")
                        info.append(f"PyTorch CUDA版本: {torch.version.cuda}")
                        info.append(f"可用GPU数量: {torch.cuda.device_count()}")
                    else:
                        info.append(f"PyTorch CUDA可用: 否")
                except ImportError:
                    pass  # PyTorch未安装
                except Exception as e:
                    info.append(f"CUDA检查失败: {e}")
                    
            except Exception as e:
                info.append(f"显卡信息获取失败: {e}")
            
            info.append("")
            info.append("=== 网络信息 ===")
            try:
                import socket
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                info.append(f"主机名: {hostname}")
                info.append(f"本地IP: {local_ip}")
            except Exception as e:
                info.append(f"网络信息收集失败: {e}")
            
            info.append("")
            info.append(f"信息收集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(info)
            
        except Exception as e:
            return f"系统信息收集失败: {e}"

    def _collect_runtime_info(self):
        """收集运行时信息"""
        try:
            try:
                import psutil
                HAS_PSUTIL = True
            except ImportError:
                HAS_PSUTIL = False
            
            info = []
            info.append("=== 运行时信息 ===")
            
            # 配置信息摘要
            info.append("=== 配置摘要 ===")
            if hasattr(self, 'config_data') and self.config_data:
                # LLM配置
                llm_config = self.config_data.get('llm', {})
                info.append(f"LLM启用: {llm_config.get('enabled', False)}")
                info.append(f"LLM模型: {llm_config.get('model', 'N/A')}")
                
                # TTS配置  
                tts_config = self.config_data.get('tts', {})
                info.append(f"TTS启用: {tts_config.get('enabled', False)}")
                info.append(f"TTS类型: {tts_config.get('type', 'N/A')}")
                
                # ASR配置
                asr_config = self.config_data.get('asr', {})
                info.append(f"ASR启用: {asr_config.get('enabled', False)}")
                info.append(f"ASR类型: {asr_config.get('type', 'N/A')}")
                
                # WebAPI配置
                webapi_config = self.config_data.get('webapi', {})
                info.append(f"WebAPI启用: {webapi_config.get('enabled', False)}")
                info.append(f"WebAPI端口: {webapi_config.get('port', 'N/A')}")
            
            info.append("")
            
            # 进程信息
            info.append("=== 进程信息 ===")
            if HAS_PSUTIL:
                try:
                    current_process = psutil.Process()
                    info.append(f"当前进程PID: {current_process.pid}")
                    info.append(f"内存使用: {current_process.memory_info().rss / (1024**2):.2f} MB")
                    info.append(f"CPU使用率: {current_process.cpu_percent()}%")
                    info.append(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_process.create_time()))}")
                except Exception as e:
                    info.append(f"进程信息收集失败: {e}")
            else:
                info.append("进程信息收集需要psutil库，当前未安装")
                info.append(f"当前进程PID: {os.getpid()}")
            
            info.append("")
            
            # 环境变量（部分）
            info.append("=== 重要环境变量 ===")
            important_env_vars = ['PATH', 'PYTHONPATH', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV']
            for var in important_env_vars:
                value = os.environ.get(var, 'N/A')
                if len(value) > 200:  # 截断过长的值
                    value = value[:200] + "..."
                info.append(f"{var}: {value}")
            
            info.append("")
            info.append(f"信息收集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(info)
            
        except Exception as e:
            return f"运行时信息收集失败: {e}"

    def clear_all_logs(self):
        """清空所有日志文件"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self,
                '确认清空日志',
                '这将清空所有日志文件的内容。\n\n此操作不可撤销，确定要继续吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            log_dir = "logs"
            if not os.path.exists(log_dir):
                InfoBar.warning(
                    title='警告',
                    content='日志目录不存在，无需清理',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            cleared_count = 0
            error_count = 0
            
            # 清空logs目录下的所有.log文件
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.log'):
                        try:
                            file_path = os.path.join(root, file)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write("")  # 清空文件内容
                            cleared_count += 1
                        except Exception as e:
                            error_count += 1
                            print(f"清理日志文件 {file} 失败: {e}")
            
            # 清空其他日志文件
            other_logs = ["chat_log.txt", "pet_system.log"]
            for log_file in other_logs:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.write("")
                        cleared_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"清理日志文件 {log_file} 失败: {e}")
            
            # 更新日志状态
            self._update_log_status()
            
            if error_count == 0:
                InfoBar.success(
                    title='清理完成',
                    content=f'已成功清空 {cleared_count} 个日志文件',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.warning(
                    title='清理完成',
                    content=f'成功清空 {cleared_count} 个文件，{error_count} 个文件清理失败',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                
        except Exception as e:
            InfoBar.error(
                title='清理失败',
                content=f'清空日志时出错: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def view_logs_directory(self):
        """打开日志目录"""
        try:
            log_dir = os.path.abspath("logs")
            
            if not os.path.exists(log_dir):
                InfoBar.warning(
                    title='目录不存在',
                    content='日志目录不存在，将创建该目录',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                os.makedirs(log_dir, exist_ok=True)
            
            # 根据操作系统打开文件管理器
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Windows":
                os.startfile(log_dir)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", log_dir])
            else:  # Linux
                subprocess.run(["xdg-open", log_dir])
                
            InfoBar.info(
                title='已打开',
                content='日志目录已在文件管理器中打开',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='打开失败',
                content=f'无法打开日志目录: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def refresh_audio_devices(self):
        """刷新音频设备列表"""
        try:
            import sounddevice as sd
            
            # 获取所有音频设备
            devices = sd.query_devices()
            
            # 清空下拉框
            self.audio_device_combo.clear()
            
            # 获取当前系统默认设备
            default_device = sd.default.device[1]  # 输出设备
            current_device_name = "未知设备"
            
            # 添加设备到下拉框
            output_devices = []
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:  # 只显示输出设备
                    device_name = f"{i}: {device['name']} ({device['max_output_channels']}ch)"
                    self.audio_device_combo.addItem(device_name, i)
                    output_devices.append((i, device))
                    
                    # 检查是否是当前默认设备
                    if i == default_device:
                        current_device_name = device['name']
            
            # 显示当前系统音频设备
            self.current_audio_device_label.setText(f"{current_device_name} (索引: {default_device})")
            
            # 尝试从配置中恢复选择
            saved_device_index = self.config_data.get('audio', {}).get('device_index', default_device)
            combo_index = -1
            for i in range(self.audio_device_combo.count()):
                if self.audio_device_combo.itemData(i) == saved_device_index:
                    combo_index = i
                    break
            
            if combo_index >= 0:
                self.audio_device_combo.setCurrentIndex(combo_index)
            else:
                # 如果没找到保存的设备，选择默认设备
                for i in range(self.audio_device_combo.count()):
                    if self.audio_device_combo.itemData(i) == default_device:
                        self.audio_device_combo.setCurrentIndex(i)
                        break
            
            # 连接选择变化事件
            self.audio_device_combo.currentTextChanged.connect(self.on_audio_device_changed)
            
            # 更新设备信息显示
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"刷新音频设备失败: {e}")
            print(f"刷新音频设备失败: {e}")
    
    def refresh_monitor_list(self):
        """刷新显示器列表"""
        try:
            from PyQt5.QtWidgets import QDesktopWidget
            from PyQt5.QtGui import QGuiApplication
            
            # 清空下拉框
            if hasattr(self, 'subtitle_monitor_combo'):
                self.subtitle_monitor_combo.clear()
                
                # 获取所有屏幕
                desktop = QDesktopWidget()
                screen_count = desktop.screenCount()
                
                # 获取更详细的屏幕信息
                app = QGuiApplication.instance()
                if app:
                    screens = app.screens()
                    
                    for i, screen in enumerate(screens):
                        # 获取屏幕几何信息
                        geometry = screen.geometry()
                        # 获取屏幕名称
                        screen_name = screen.name() if hasattr(screen, 'name') else f"显示器 {i+1}"
                        # 获取屏幕分辨率
                        width = geometry.width()
                        height = geometry.height()
                        # 检查是否是主屏幕
                        is_primary = screen == app.primaryScreen()
                        primary_text = " (主屏幕)" if is_primary else ""
                        
                        # 创建显示文本
                        display_text = f"{screen_name}: {width}x{height}{primary_text}"
                        self.subtitle_monitor_combo.addItem(display_text, i)
                else:
                    # 如果获取不到详细信息，使用基础方法
                    for i in range(screen_count):
                        geometry = desktop.screenGeometry(i)
                        width = geometry.width()
                        height = geometry.height()
                        is_primary = i == desktop.primaryScreen()
                        primary_text = " (主屏幕)" if is_primary else ""
                        
                        display_text = f"显示器 {i+1}: {width}x{height}{primary_text}"
                        self.subtitle_monitor_combo.addItem(display_text, i)
                
                print(f"检测到 {screen_count} 个显示器")
                
                # 设置当前选择的显示器
                saved_monitor = self.config_data.get('subtitle', {}).get('display_monitor', 0)
                for i in range(self.subtitle_monitor_combo.count()):
                    if self.subtitle_monitor_combo.itemData(i) == saved_monitor:
                        self.subtitle_monitor_combo.setCurrentIndex(i)
                        break
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"刷新显示器列表失败: {e}")
            print(f"刷新显示器列表失败: {e}")
            
            # 添加默认选项
            if hasattr(self, 'subtitle_monitor_combo'):
                self.subtitle_monitor_combo.clear()
                self.subtitle_monitor_combo.addItem("主显示器", 0)
                
    def on_monitor_selection_changed(self):
        """显示器选择变化时的处理"""
        try:
            if hasattr(self, 'subtitle_monitor_combo'):
                selected_monitor = self.subtitle_monitor_combo.currentData()
                if selected_monitor is not None:
                    # 更新配置
                    self.config_data.setdefault('subtitle', {})['display_monitor'] = selected_monitor
                    print(f"显示器选择已更改为: {selected_monitor}")
                    
                    # 更新位置信息显示
                    self._update_position_info()
                    
                    # 通知main.py更新字幕显示设置
                    self._send_subtitle_display_update()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"显示器选择变化处理失败: {e}")
            print(f"显示器选择变化处理失败: {e}")
    
    def _send_subtitle_display_update(self):
        """发送字幕显示设置更新消息到main.py"""
        try:
            subtitle_config = self.config_data.get('subtitle', {})
            
            # 准备消息数据
            update_data = {
                'monitor_index': subtitle_config.get('display_monitor', 0),
                'position': subtitle_config.get('display_position', 'center'),
                'position_x': subtitle_config.get('position_x', 0),
                'position_y': subtitle_config.get('position_y', 0),
                'offset_x': subtitle_config.get('display_offset_x', 0),
                'offset_y': subtitle_config.get('display_offset_y', 0)
            }
            
            # 直接使用消息队列发送消息
            try:
                from utils.message_queue import send_message
                success = send_message('update_subtitle_display', update_data, priority=1)
                if success:
                    print("字幕显示设置更新消息已发送")
                else:
                    print("字幕显示设置更新消息发送失败")
            except Exception as msg_error:
                print(f"消息队列发送失败: {msg_error}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"发送字幕显示设置更新失败: {e}")
            print(f"发送字幕显示设置更新失败: {e}")
    
    def _on_subtitle_position_changed(self):
        """字幕位置选择变化时的处理"""
        try:
            if hasattr(self, 'widgets') and 'subtitle.display_position' in self.widgets:
                position_combo = self.widgets['subtitle.display_position']['widget']
                selected_position = position_combo.currentData()
                if selected_position is not None:
                    # 更新配置
                    self.config_data.setdefault('subtitle', {})['display_position'] = selected_position
                    print(f"字幕显示位置已更改为: {selected_position}")
                    
                    # 更新位置信息显示
                    self._update_position_info()
                    
                    # 通知main.py更新字幕显示设置
                    self._send_subtitle_display_update()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"字幕位置变化处理失败: {e}")
            print(f"字幕位置变化处理失败: {e}")
    
    def _on_subtitle_offset_changed(self):
        """字幕偏移量变化时的处理"""
        try:
            if hasattr(self, 'widgets'):
                # 获取X和Y偏移值
                x_offset = 0
                y_offset = 0
                
                if 'subtitle.display_offset_x' in self.widgets:
                    x_offset = self.widgets['subtitle.display_offset_x']['widget'].value()
                    self.config_data.setdefault('subtitle', {})['display_offset_x'] = x_offset
                
                if 'subtitle.display_offset_y' in self.widgets:
                    y_offset = self.widgets['subtitle.display_offset_y']['widget'].value()
                    self.config_data.setdefault('subtitle', {})['display_offset_y'] = y_offset
                
                print(f"字幕偏移量已更改为: X={x_offset}, Y={y_offset}")
                
                # 更新位置信息显示
                self._update_position_info()
                
                # 通知main.py更新字幕显示设置
                self._send_subtitle_display_update()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"字幕偏移量变化处理失败: {e}")
            print(f"字幕偏移量变化处理失败: {e}")
    
    def _on_subtitle_coordinates_changed(self):
        """字幕坐标变化时的处理"""
        try:
            if hasattr(self, 'widgets'):
                # 获取X和Y坐标值
                x_coord = 0
                y_coord = 0
                
                if 'subtitle.position_x' in self.widgets:
                    x_coord = self.widgets['subtitle.position_x']['widget'].value()
                    self.config_data.setdefault('subtitle', {})['position_x'] = x_coord
                
                if 'subtitle.position_y' in self.widgets:
                    y_coord = self.widgets['subtitle.position_y']['widget'].value()
                    self.config_data.setdefault('subtitle', {})['position_y'] = y_coord
                
                print(f"字幕坐标已更改为: X={x_coord}, Y={y_coord}")
                
                # 更新位置信息显示
                self._update_position_info()
                
                # 通知main.py更新字幕显示设置
                self._send_subtitle_display_update()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"字幕坐标变化处理失败: {e}")
            print(f"字幕坐标变化处理失败: {e}")
    
    def _calculate_position_coordinates(self):
        """根据选择的显示器和预设位置计算具体坐标"""
        try:
            app = QApplication.instance()
            desktop = app.desktop()
            
            # 获取当前选择的显示器
            monitor_index = 0
            if hasattr(self, 'widgets') and 'subtitle.display_monitor' in self.widgets:
                monitor_combo = self.widgets['subtitle.display_monitor']['widget']
                monitor_index = monitor_combo.currentData()
                if monitor_index is None:
                    monitor_index = 0
            
            # 获取选择的位置
            position = 'center'
            if hasattr(self, 'widgets') and 'subtitle.display_position' in self.widgets:
                position_combo = self.widgets['subtitle.display_position']['widget']
                position = position_combo.currentData()
                if position is None:
                    position = 'center'
            
            # 获取显示器几何信息
            if monitor_index < desktop.screenCount():
                screen_rect = desktop.screenGeometry(monitor_index)
            else:
                screen_rect = desktop.primaryScreen().geometry()
            
            # 假设字幕窗口的大小（可以调整）
            subtitle_width = 600
            subtitle_height = 100
            
            # 根据位置计算坐标
            x, y = 0, 0
            
            if position == 'center':
                x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
                y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
            elif position == 'top':
                x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
                y = screen_rect.y() + 50
            elif position == 'bottom':
                x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            elif position == 'left':
                x = screen_rect.x() + 50
                y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
            elif position == 'right':
                x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
                y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
            elif position == 'top_left':
                x = screen_rect.x() + 50
                y = screen_rect.y() + 50
            elif position == 'top_right':
                x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
                y = screen_rect.y() + 50
            elif position == 'bottom_left':
                x = screen_rect.x() + 50
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            elif position == 'bottom_right':
                x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            # 新增的中心位置选项
            elif position == 'top_left_center':
                x = screen_rect.x() + screen_rect.width() // 4 - subtitle_width // 2
                y = screen_rect.y() + 50
            elif position == 'top_right_center':
                x = screen_rect.x() + screen_rect.width() * 3 // 4 - subtitle_width // 2
                y = screen_rect.y() + 50
            elif position == 'bottom_left_center':
                x = screen_rect.x() + screen_rect.width() // 4 - subtitle_width // 2
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            elif position == 'bottom_right_center':
                x = screen_rect.x() + screen_rect.width() * 3 // 4 - subtitle_width // 2
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            elif position == 'left_center':
                x = screen_rect.x() + 50
                y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
            elif position == 'right_center':
                x = screen_rect.x() + screen_rect.width() - subtitle_width - 50
                y = screen_rect.y() + (screen_rect.height() - subtitle_height) // 2
            elif position == 'top_center':
                x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
                y = screen_rect.y() + 50
            elif position == 'bottom_center':
                x = screen_rect.x() + (screen_rect.width() - subtitle_width) // 2
                y = screen_rect.y() + screen_rect.height() - subtitle_height - 50
            
            # 更新坐标输入框
            if hasattr(self, 'widgets'):
                if 'subtitle.position_x' in self.widgets:
                    self.widgets['subtitle.position_x']['widget'].setValue(x)
                    self.config_data.setdefault('subtitle', {})['position_x'] = x
                
                if 'subtitle.position_y' in self.widgets:
                    self.widgets['subtitle.position_y']['widget'].setValue(y)
                    self.config_data.setdefault('subtitle', {})['position_y'] = y
            
            # 更新位置信息显示
            self._update_position_info()
            
            print(f"根据显示器{monitor_index}和位置{position}计算坐标: X={x}, Y={y}")
            
            # 通知main.py更新字幕显示设置
            self._send_subtitle_display_update()
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"计算位置坐标失败: {e}")
            print(f"计算位置坐标失败: {e}")
    
    def _update_position_info(self):
        """更新位置信息显示"""
        try:
            if not hasattr(self, 'position_info_label'):
                return
            
            # 获取当前配置
            subtitle_config = self.config_data.get('subtitle', {})
            
            monitor_index = subtitle_config.get('display_monitor', 0)
            position_x = subtitle_config.get('position_x', 0)
            position_y = subtitle_config.get('position_y', 0)
            offset_x = subtitle_config.get('display_offset_x', 0)
            offset_y = subtitle_config.get('display_offset_y', 0)
            
            # 获取显示器信息
            app = QApplication.instance()
            desktop = app.desktop()
            
            monitor_info = f"显示器{monitor_index}"
            if monitor_index < desktop.screenCount():
                screen_rect = desktop.screenGeometry(monitor_index)
                monitor_info += f" ({screen_rect.width()}x{screen_rect.height()})"
            
            # 计算最终位置
            final_x = position_x + offset_x
            final_y = position_y + offset_y
            
            info_text = f"{monitor_info} | 基础坐标: ({position_x}, {position_y}) | 偏移: ({offset_x}, {offset_y}) | 最终位置: ({final_x}, {final_y})"
            
            self.position_info_label.setText(info_text)
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"更新位置信息失败: {e}")
            print(f"更新位置信息失败: {e}")
    
    def _preview_subtitle_display(self):
        """预览字幕显示（独立UI测试）"""
        try:
            from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout
            from PyQt5.QtCore import Qt, QTimer
            from PyQt5.QtGui import QFont
            import sys
            
            # 获取当前配置
            subtitle_config = self.config_data.get('subtitle', {})
            
            # 创建测试窗口
            test_window = QWidget()
            test_window.setWindowTitle("字幕预览测试")
            test_window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            
            # 设置窗口属性
            test_window.setAttribute(Qt.WA_TranslucentBackground)
            
            # 获取位置信息
            monitor_index = subtitle_config.get('display_monitor', 0)
            position_x = subtitle_config.get('position_x', 960)
            position_y = subtitle_config.get('position_y', 540)
            offset_x = subtitle_config.get('display_offset_x', 0)
            offset_y = subtitle_config.get('display_offset_y', 0)
            
            # 计算最终位置
            final_x = position_x + offset_x
            final_y = position_y + offset_y
            
            # 设置窗口位置
            test_window.move(final_x, final_y)
            
            # 创建字幕标签
            subtitle_label = QLabel("这是字幕预览测试 - 预览当前设置效果")
            
            # 设置字体
            font = QFont(subtitle_config.get('font_family', 'Microsoft YaHei'))
            font.setPointSize(subtitle_config.get('font_size', 24))
            subtitle_label.setFont(font)
            
            # 设置样式
            text_r = subtitle_config.get('text_color_r', 255)
            text_g = subtitle_config.get('text_color_g', 255) 
            text_b = subtitle_config.get('text_color_b', 255)
            text_a = subtitle_config.get('text_color_a', 255)
            
            bg_r = subtitle_config.get('bg_color_r', 255)
            bg_g = subtitle_config.get('bg_color_g', 0)
            bg_b = subtitle_config.get('bg_color_b', 0)
            bg_a = subtitle_config.get('bg_color_a', 120)
            
            outline_r = subtitle_config.get('outline_color_r', 0)
            outline_g = subtitle_config.get('outline_color_g', 0)
            outline_b = subtitle_config.get('outline_color_b', 0)
            outline_size = subtitle_config.get('outline_size', 2)
            padding = subtitle_config.get('background_padding', 5)
            
            style = f"""
                QLabel {{
                    color: rgba({text_r}, {text_g}, {text_b}, {text_a});
                    background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_a});
                    border: {outline_size}px solid rgba({outline_r}, {outline_g}, {outline_b}, 255);
                    padding: {padding}px;
                    border-radius: 5px;
                }}
            """
            
            subtitle_label.setStyleSheet(style)
            subtitle_label.setAlignment(Qt.AlignCenter)
            
            # 设置布局
            layout = QVBoxLayout(test_window)
            layout.addWidget(subtitle_label)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # 显示窗口
            test_window.show()
            
            # 创建定时器自动关闭窗口
            timer = QTimer()
            timer.timeout.connect(test_window.close)
            timer.setSingleShot(True)
            timer.start(3000)  # 3秒后自动关闭
            
            # 保存窗口引用避免被垃圾回收
            self._test_window = test_window
            
            if hasattr(self, 'logger'):
                self.logger.info("字幕预览测试启动成功")
            print("字幕预览测试启动成功")
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"预览字幕显示失败: {e}")
            print(f"预览字幕显示失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"字幕预览失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _test_subtitle_display(self):
        """测试字幕显示（主程序进程间通信）"""
        try:
            # 获取当前配置
            subtitle_config = self.config_data.get('subtitle', {})
            
            # 准备测试数据
            test_message = {
                "type": "show_subtitle",
                "content": "这是字幕测试消息 - 测试主程序字幕显示",
                "duration": 3,
                "config": {
                    "enabled": True,
                    "display_monitor": subtitle_config.get('display_monitor', 0),
                    "position_x": subtitle_config.get('position_x', 960),
                    "position_y": subtitle_config.get('position_y', 540),
                    "display_offset_x": subtitle_config.get('display_offset_x', 0),
                    "display_offset_y": subtitle_config.get('display_offset_y', 0),
                    "font_size": subtitle_config.get('font_size', 24),
                    "font_family": subtitle_config.get('font_family', 'Arial'),
                    "text_color_r": subtitle_config.get('text_color_r', 255),
                    "text_color_g": subtitle_config.get('text_color_g', 255),
                    "text_color_b": subtitle_config.get('text_color_b', 255),
                    "text_color_a": subtitle_config.get('text_color_a', 255),
                    "outline_color_r": subtitle_config.get('outline_color_r', 0),
                    "outline_color_g": subtitle_config.get('outline_color_g', 0),
                    "outline_color_b": subtitle_config.get('outline_color_b', 0),
                    "outline_color_a": subtitle_config.get('outline_color_a', 200),
                    "bg_color_r": subtitle_config.get('bg_color_r', 255),
                    "bg_color_g": subtitle_config.get('bg_color_g', 0),
                    "bg_color_b": subtitle_config.get('bg_color_b', 0),
                    "bg_color_a": subtitle_config.get('bg_color_a', 120),
                    "outline_size": subtitle_config.get('outline_size', 2),
                    "background_padding": subtitle_config.get('background_padding', 5)
                }
            }
            
            # 使用消息队列发送测试请求
            try:
                from utils.message_queue import send_message
                send_message(test_message)
                
                if hasattr(self, 'logger'):
                    self.logger.info("字幕测试消息已发送到主程序")
                print("字幕测试消息已发送到主程序")
                
                InfoBar.success(
                    title="成功",
                    content="字幕测试消息已发送，请查看主程序显示效果",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                
            except Exception as e:
                # 如果消息队列失败，尝试HTTP API
                import requests
                try:
                    response = requests.post(
                        'http://localhost:12345/subtitle',
                        json=test_message,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        if hasattr(self, 'logger'):
                            self.logger.info("字幕测试请求通过HTTP API发送成功")
                        print("字幕测试请求通过HTTP API发送成功")
                        
                        InfoBar.success(
                            title="成功",
                            content="字幕测试请求已发送",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=3000,
                            parent=self
                        )
                    else:
                        raise Exception(f"HTTP请求失败: {response.status_code}")
                        
                except requests.exceptions.ConnectionError:
                    # 如果主程序未运行，显示提示
                    InfoBar.warning(
                        title="提示",
                        content="主程序未运行，无法测试字幕。请先启动主程序或使用预览按钮。",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                except Exception as e2:
                    raise Exception(f"消息队列和HTTP API均失败: {e}, {e2}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"测试字幕显示失败: {e}")
            print(f"测试字幕显示失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"字幕测试失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _close_current_subtitle(self):
        """关闭当前字幕（包括预览字幕和主程序字幕）"""
        try:
            # 1. 首先关闭预览字幕窗口
            if hasattr(self, '_test_window') and self._test_window:
                try:
                    self._test_window.close()
                    self._test_window = None
                    print("预览字幕窗口已关闭")
                except Exception as e:
                    print(f"关闭预览字幕窗口时出错: {e}")
            
            # 2. 发送消息关闭主程序字幕
            try:
                from utils.message_queue import send_message
                send_message("hide_subtitle", {"source": "UI_close_button"})
                
                if hasattr(self, 'logger'):
                    self.logger.info("字幕关闭消息已发送")
                print("主程序字幕关闭消息已发送")
                
                InfoBar.success(
                    title="成功",
                    content="预览字幕和主程序字幕关闭消息已发送",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
            except Exception as e:
                # 如果消息队列失败，尝试HTTP API
                import requests
                try:
                    response = requests.post(
                        'http://localhost:12345/clear_subtitle',
                        json={"action": "clear"},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        if hasattr(self, 'logger'):
                            self.logger.info("主程序字幕关闭请求通过HTTP API发送成功")
                        print("主程序字幕关闭请求通过HTTP API发送成功")
                        
                        InfoBar.success(
                            title="成功",
                            content="预览字幕已关闭，主程序字幕已关闭",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                    else:
                        raise Exception(f"HTTP请求失败: {response.status_code}")
                        
                except requests.exceptions.ConnectionError:
                    InfoBar.warning(
                        title="提示",
                        content="预览字幕已关闭，主程序未运行无法关闭主程序字幕",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                except Exception as e2:
                    raise Exception(f"消息队列和HTTP API均失败: {e}, {e2}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"关闭字幕失败: {e}")
            print(f"关闭字幕失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"关闭字幕失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
    def on_audio_device_changed(self):
        """音频设备选择变化时的处理"""
        self.update_audio_device_info()

    def update_audio_device_info(self):
        """更新音频设备信息显示"""
        try:
            import sounddevice as sd
            
            current_index = self.audio_device_combo.currentIndex()
            if current_index < 0:
                return
            
            device_index = self.audio_device_combo.itemData(current_index)
            if device_index is None or device_index < 0:
                return
            
            # 获取设备详细信息
            device = sd.query_devices(device_index)
            
            info_text = f"""设备索引: {device_index}
设备名称: {device['name']}
输出声道数: {device['max_output_channels']}
输入声道数: {device['max_input_channels']}
默认采样率: {device['default_samplerate']} Hz
主机API: {sd.query_hostapis(device['hostapi'])['name']}
延迟 (低/高): {device['default_low_output_latency']:.3f}s / {device['default_high_output_latency']:.3f}s"""
            
            self.audio_device_info.setText(info_text)
            
        except Exception as e:
            self.audio_device_info.setText(f"获取设备信息失败: {str(e)}")

    def test_audio_device(self):
        """测试选中的音频设备"""
        try:
            import sounddevice as sd
            import numpy as np
            import threading
            
            current_index = self.audio_device_combo.currentIndex()
            if current_index < 0:
                InfoBar.warning(
                    title='无设备选择',
                    content='请先选择一个音频输出设备',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            device_index = self.audio_device_combo.itemData(current_index)
            if device_index is None or device_index < 0:
                InfoBar.warning(
                    title='设备无效',
                    content='选中的音频设备无效',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 获取音量设置
            volume = self.audio_volume_spin.value()
            
            # 生成测试音频（1秒440Hz正弦波）
            duration = 1.0  # 秒
            sample_rate = 44100
            frequency = 440  # A4音
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            test_audio = np.sin(frequency * 2 * np.pi * t) * volume * 0.3  # 降低音量避免过响
            
            # 禁用测试按钮，启用停止按钮
            self.test_audio_btn.setEnabled(False)
            self.stop_test_audio_btn.setEnabled(True)
            
            # 在后台线程播放测试音频
            def play_test_audio():
                try:
                    # 设置音频设备
                    sd.default.device[1] = device_index
                    
                    InfoBar.info(
                        title='正在测试',
                        content=f'正在通过设备 {device_index} 播放测试音频...',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=1500,
                        parent=self
                    )
                    
                    # 播放测试音频
                    sd.play(test_audio, sample_rate, blocking=True)
                    
                    InfoBar.success(
                        title='测试完成',
                        content='音频测试播放完成',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    
                except Exception as e:
                    InfoBar.error(
                        title='播放失败',
                        content=f'音频测试失败: {str(e)}',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                finally:
                    # 恢复按钮状态
                    self.test_audio_btn.setEnabled(True)
                    self.stop_test_audio_btn.setEnabled(False)
            
            # 启动测试线程
            self.audio_test_thread = threading.Thread(target=play_test_audio)
            self.audio_test_thread.daemon = True
            self.audio_test_thread.start()
            
        except ImportError:
            InfoBar.error(
                title='模块缺失',
                content='sounddevice或numpy模块未安装，无法测试音频',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='测试失败',
                content=f'音频测试失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            # 恢复按钮状态
            self.test_audio_btn.setEnabled(True)
            self.stop_test_audio_btn.setEnabled(False)

    def stop_test_audio(self):
        """停止音频测试"""
        try:
            import sounddevice as sd
            
            # 停止所有音频播放
            sd.stop()
            
            # 恢复按钮状态
            self.test_audio_btn.setEnabled(True)
            self.stop_test_audio_btn.setEnabled(False)
            
            InfoBar.info(
                title='已停止',
                content='音频测试已停止',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='停止失败',
                content=f'停止音频测试失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def create_voice_clone_tab(self):
        """创建“声音克隆”页面：包含两个子选项卡
        1) TTS模型更换：选择模型.pth与参考音频.wav，角色名、语种与参考文本，生成配置/批处理
        2) 一键克隆音色：上传音频到 fine_tuning/input/audio.mp3，包装一键克隆脚本（优先英文版），输出日志，可停止
        """
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 状态数据
        self.voice_clone = getattr(self, 'voice_clone', {
            'model_path': '',
            'audio_path': '',
            'role_name': '',
            'language': 'zh',
            'transcript': ''
        })

        tabs = QTabWidget(self)
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Tab1: 模型更换
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)

        # 顶部两个拖拽区域
        self.drop_model = DropArea("模型文件 (.pth)", "选择模型文件或拖拽文件到此处")
        self.drop_audio = DropArea("参考音频 (.wav)", "选择音频文件或拖拽文件到此处")
        t1_top = QHBoxLayout()
        t1_top.addWidget(self.drop_model)
        t1_top.addWidget(self.drop_audio)
        t1_layout.addLayout(t1_top)

        # 绑定选择按钮
        self.drop_model.select_btn.clicked.connect(self._select_pth)
        self.drop_audio.select_btn.clicked.connect(self._select_wav)

        # 角色名、语种
        row_box = QHBoxLayout()
        row_left = QGroupBox("角色名称：")
        row_left_l = QVBoxLayout(row_left)
        self.vc_role_edit = QLineEdit()
        self.vc_role_edit.setPlaceholderText("输入角色名称，用于生成bat/文件名")
        row_left_l.addWidget(self.vc_role_edit)

        row_right = QGroupBox("参考音频语种：")
        row_right_l = QVBoxLayout(row_right)
        self.vc_lang_combo = QComboBox()
        self.vc_lang_combo.addItems(["zh - 中文", "en - 英文", "ja - 日文"])
        row_right_l.addWidget(self.vc_lang_combo)

        row_box.addWidget(row_left)
        row_box.addWidget(row_right)
        t1_layout.addLayout(row_box)

        # 参考文本
        txt_box = QGroupBox("参考音频的文本内容：")
        txt_layout = QVBoxLayout(txt_box)
        self.vc_transcript = QTextEdit()
        self.vc_transcript.setPlaceholderText("请输入参考音频对应的文本内容")
        txt_layout.addWidget(self.vc_transcript)
        t1_layout.addWidget(txt_box)

        # 生成按钮与状态
        btn_line = QHBoxLayout()
        self.vc_gen_btn = QPushButton("生成TTS的bat文件")
        self.vc_gen_btn.clicked.connect(self._generate_tts_bat)
        btn_line.addStretch(1)
        btn_line.addWidget(self.vc_gen_btn)
        t1_layout.addLayout(btn_line)

        self.vc_status = QLabel("状态：请上传文件并生成配置")
        self.vc_status.setStyleSheet("color:#888;")
        t1_layout.addWidget(self.vc_status)

        tabs.addTab(tab1, "TTS模型更换")

        # Tab2: 一键克隆
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)

        # 输入行：语言与模型名
        input_row = QHBoxLayout()
        lang_box = QGroupBox("语言(Language)")
        lang_layout = QVBoxLayout(lang_box)
        self.clone_lang_combo = QComboBox()
        self.clone_lang_combo.addItems(["en", "zh"])  # bat仅支持 en/zh
        self.clone_lang_combo.setCurrentText("zh")
        lang_layout.addWidget(self.clone_lang_combo)

        name_box = QGroupBox("模型名称(Model Name)")
        name_layout = QVBoxLayout(name_box)
        self.clone_model_name = QLineEdit()
        self.clone_model_name.setPlaceholderText("e.g. my-voice")
        name_layout.addWidget(self.clone_model_name)

        input_row.addWidget(lang_box)
        input_row.addWidget(name_box)
        t2_layout.addLayout(input_row)

        # 控制按钮与日志
        self.train_browser = TextBrowser(self)
        t2_btns = QHBoxLayout()
        self.train_start_btn = PrimaryToolButton(FIF.PLAY)
        self.train_start_btn.setText("开始克隆")
        self.train_stop_btn = ToolButton(FIF.PAUSE)
        self.train_stop_btn.setText("停止")

        # 上传控件与一键上传并克隆
        self.clone_source_audio = DropArea("源音频文件(.mp3/.wav)", "拖拽或选择；将被复制到 fine_tuning/input/audio.mp3")
        self.clone_source_audio.select_btn.clicked.connect(lambda: self._select_audio_for_clone())
        # 兼容不同版本的 FluentIcon，UPLOAD 在部分版本不存在，提供多级回退
        upload_icon = getattr(FIF, 'UPLOAD', None)
        if upload_icon is None:
            upload_icon = getattr(FIF, 'CLOUD_UPLOAD', None)
        if upload_icon is None:
            upload_icon = getattr(FIF, 'SEND', None)
        if upload_icon is None:
            upload_icon = getattr(FIF, 'SAVE', FIF.PLAY)
        self.train_upload_and_start_btn = PrimaryToolButton(upload_icon)
        self.train_upload_and_start_btn.setText("上传并开始克隆")
        self.train_upload_and_start_btn.clicked.connect(self._upload_and_start_clone)

        # 清空日志按钮（兼容不同版本的 FluentIcon，多级回退）
        clear_icon = getattr(FIF, 'CLEAR', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'DELETE', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'ERASE', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'ERASER', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'TRASH', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'BRUSH', None)
        if clear_icon is None:
            clear_icon = getattr(FIF, 'CLOSE', FIF.CANCEL)
        self.train_clear_btn = ToolButton(clear_icon)
        self.train_clear_btn.setText("清空日志")
        self.train_clear_btn.clicked.connect(self.train_browser.clear)

        t2_btns.addWidget(self.train_start_btn)
        t2_btns.addWidget(self.train_stop_btn)
        t2_btns.addWidget(self.train_upload_and_start_btn)
        t2_btns.addWidget(self.train_clear_btn)
        t2_btns.addStretch(1)

        # 将上传区域置于按钮上方
        t2_layout.addWidget(self.clone_source_audio)
        t2_layout.addLayout(t2_btns)
        t2_layout.addWidget(self.train_browser)

        tabs.addTab(tab2, "一键克隆音色")

        # 训练逻辑
        self.train_worker = None
        self.train_start_btn.clicked.connect(self._start_voice_train)
        self.train_stop_btn.clicked.connect(self._stop_voice_train)

        self.vBoxLayout.addWidget(tabs)
        self.vBoxLayout.addStretch()

    # ====== 声音克隆 - 交互方法 ======
    def _select_pth(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", os.getcwd(), "PyTorch/Weights (*.pth *.pt *.safetensors);;All Files (*.*)")
        if path:
            self.drop_model.set_file_path(path)

    def _select_wav(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择参考音频", os.getcwd(), "Audio (*.wav);;All Files (*.*)")
        if path:
            self.drop_audio.set_file_path(path)

    def _generate_tts_bat(self):
        model = self.drop_model.file_path
        audio = self.drop_audio.file_path
        role = self.vc_role_edit.text().strip()
        lang_text = self.vc_lang_combo.currentText().split(' ')[0]
        transcript = self.vc_transcript.toPlainText().strip()

        if not model or not os.path.exists(model):
            self.vc_status.setText("状态：请先选择有效的模型文件")
            self.vc_status.setStyleSheet("color:#d9534f;")
            return
        if not audio or not os.path.exists(audio):
            self.vc_status.setText("状态：请先选择有效的参考音频")
            self.vc_status.setStyleSheet("color:#d9534f;")
            return
        if not role:
            self.vc_status.setText("状态：请输入角色名称")
            self.vc_status.setStyleSheet("color:#d9534f;")
            return

        out_dir = os.path.abspath(os.path.join("Voice_Model_Factory", role))
        os.makedirs(out_dir, exist_ok=True)
        cfg_path = os.path.join(out_dir, "voice_clone_config.json")
        bat_path = os.path.join(out_dir, f"生成TTS_{role}.bat")

        cfg = {
            "model_path": model,
            "audio_path": audio,
            "language": lang_text,
            "transcript": transcript,
            "role": role
        }
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            # 预处理：为 Windows cmd 转义 ^ 和 "
            safe_transcript = transcript.replace('^', '^^').replace('"', '^"')

            # 生成批处理：设置环境变量并调用根目录的一键脚本（若存在）
            lines = [
                "@echo off",
                "setlocal enabledelayedexpansion",
                f"set \"VC_MODEL={model}\"",
                f"set \"VC_AUDIO={audio}\"",
                f"set \"VC_LANG={lang_text}\"",
                f"set \"VC_ROLE={role}\"",
                f"set \"VC_TRANSCRIPT={safe_transcript}\"",
                "set NO_PAUSE=1",
                "echo 已写入配置: voice_clone_config.json",
                "if exist ..\\..\\OneClick_Clone_Voice_EN.bat (",
                "  call ..\\..\\OneClick_Clone_Voice_EN.bat",
                ") else if exist ..\\..\\一键克隆音色.bat (",
                "  call ..\\..\\一键克隆音色.bat",
                ") else (",
                "  echo 未找到克隆脚本，请手动处理",
                ")",
                "pause"
            ]
            with open(bat_path, 'w', encoding='gbk', newline='') as f:
                f.write("\r\n".join(lines))

            self.vc_status.setText(f"状态：已生成配置与批处理\n{cfg_path}\n{bat_path}")
            self.vc_status.setStyleSheet("color:#28a745;")
        except Exception as e:
            self.vc_status.setText(f"状态：生成失败 - {e}")
            self.vc_status.setStyleSheet("color:#d9534f;")

    def _start_voice_train(self):
        if self.train_worker and self.train_worker.isRunning():
            InfoBar.warning(title='训练中', content='已有训练进程在运行', orient=Qt.Horizontal,
                            isClosable=True, position=InfoBarPosition.BOTTOM_RIGHT, duration=2000, parent=self)
            return
        # 选择优先脚本：英文版 > 中文版（基于项目根目录）
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        en_bat = os.path.join(proj_root, "OneClick_Clone_Voice_EN.bat")
        zh_bat = os.path.join(proj_root, "一键克隆音色.bat")
        target_bat = en_bat if os.path.exists(en_bat) else zh_bat
        if not os.path.exists(target_bat):
            self.train_browser.append("未找到克隆脚本（OneClick_Clone_Voice_EN.bat / 一键克隆音色.bat）。")
            return

        # 根据UI输入生成包装bat，注入环境变量，避免交互
        lang = self.clone_lang_combo.currentText().strip() if hasattr(self, 'clone_lang_combo') else 'zh'
        role = self.clone_model_name.text().strip() if hasattr(self, 'clone_model_name') else ''
        if not role:
            self.train_browser.append("请先填写模型名称(Model Name)。")
            return

        wrapper_path = os.path.join(proj_root, "run_voice_clone_ui.bat")
        try:
            lines = [
                "@echo off",
                "setlocal",
                f"set \"VC_LANG={lang}\"",
                f"set \"VC_ROLE={role}\"",
                "set NO_PAUSE=1",
            ]
            # 若缺少 UVR 权重目录则跳过分离步骤以减少报错与耗时
            uvr_weights = os.path.join(proj_root, "fine_tuning", "tools", "uvr5", "uvr5_weights")
            if not os.path.exists(uvr_weights):
                lines.append("set SKIP_UVR=1")
            lines.append(f"call \"{target_bat}\"")
            with open(wrapper_path, 'w', encoding='gbk', newline='') as f:
                f.write("\r\n".join(lines))
        except Exception as e:
            self.train_browser.append(f"生成包装脚本失败: {e}")
            return

        self.train_worker = BatWorker(wrapper_path)
        self.train_worker.output_signal.connect(self.train_browser.append)
        self.train_worker.finished_signal.connect(lambda: self.train_browser.append("克隆进程已结束"))
        self.train_worker.start()
        self.train_browser.append("已启动一键克隆脚本…")

    def _stop_voice_train(self):
        if self.train_worker and self.train_worker.isRunning():
            self.train_worker.stop()
            self.train_browser.append("正在尝试停止训练脚本…")
        else:
            self.train_browser.append("没有运行中的训练脚本。")

    def _select_audio_for_clone(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择源音频文件", os.getcwd(), "Audio (*.mp3 *.wav);;All Files (*.*)")
        if path:
            self.clone_source_audio.set_file_path(path)

    def _upload_source_audio(self) -> bool:
        """将所选音频复制到 fine_tuning/input/audio.mp3。返回 True 表示成功。"""
        import shutil
        src = getattr(self.clone_source_audio, 'file_path', '') if hasattr(self, 'clone_source_audio') else ''
        if not src or not os.path.exists(src):
            self.train_browser.append("请先选择源音频文件(.mp3/.wav)。")
            return False
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        target_dir = os.path.join(proj_root, 'fine_tuning', 'input')
        try:
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, 'audio.mp3')
            # 统一改名为 audio.mp3（如为 wav 也统一命名，底层脚本按 mp3 名读取）
            shutil.copy2(src, target)
            self.train_browser.append(f"已上传音频到: {target}")
            return True
        except Exception as e:
            self.train_browser.append(f"上传失败: {e}")
            return False

    def _upload_and_start_clone(self):
        """一键上传并触发克隆流程。"""
        if self._upload_source_audio():
            self._start_voice_train()

    # ====== Live2D 动画操控相关方法 ======
    
    def trigger_live2d_motion(self, motion_index):
        """触发Live2D动作"""
        try:
            success = False
            
            # 方法1：优先使用实例引用
            if hasattr(self, 'live2d_model') and self.live2d_model:
                try:
                    if hasattr(self.live2d_model, 'play_tapbody_motion'):
                        self.live2d_model.play_tapbody_motion(motion_index)
                        success = True
                    elif hasattr(self.live2d_model, 'model') and self.live2d_model.model:
                        # 直接调用底层Live2D模型
                        self.live2d_model.model.StartMotion("TapBody", motion_index, 3)
                        success = True
                except Exception as e:
                    print(f"通过实例引用控制Live2D动作失败: {e}")
            
            # 方法2：尝试从全局获取Live2D模型实例
            if not success:
                try:
                    import models.live2d_model as live2d_module
                    if hasattr(live2d_module, '_model') and live2d_module._model:
                        model = live2d_module._model
                        if hasattr(model, 'play_tapbody_motion'):
                            model.play_tapbody_motion(motion_index)
                            success = True
                        elif hasattr(model, 'model') and model.model:
                            # 直接调用底层Live2D模型
                            model.model.StartMotion("TapBody", motion_index, 3)
                            success = True
                except Exception as e:
                    print(f"通过全局模块控制Live2D动作失败: {e}")
            
            # 方法3：通过WebAPI发送请求（已移除，避免404错误）
            # WebAPI Live2D控制功能已移除，使用文件写入方式作为备选
            
            # 方法4：通过文件写入方式向Live2D程序发送动作指令（备选）
            if not success:
                motion_file = "motion_trigger.tmp"
                with open(motion_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "action": "trigger_motion", 
                        "motion_index": motion_index,
                        "motion_group": "TapBody",
                        "priority": 3,
                        "timestamp": time.time()
                    }))
            
            # 显示操作提示
            InfoBar.success(
                title='动作触发',
                content=f"已播放动作: 动作{motion_index + 1} {'(直接控制)' if success else '(通过文件)'}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='动作触发失败',
                content=f"无法触发动作: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def trigger_random_motion(self):
        """触发随机动作"""
        try:
            # 从动作列表中随机选择一个
            if hasattr(self, 'animation_motion_list') and self.animation_motion_list.count() > 0:
                import random
                random_index = random.randint(0, self.animation_motion_list.count() - 1)
                item = self.animation_motion_list.item(random_index)
                if item and item.data(Qt.UserRole) is not None:
                    motion_index = item.data(Qt.UserRole)
                    self.trigger_live2d_motion(motion_index)
                    
                    InfoBar.success(
                        title='随机动作',
                        content=f"播放随机动作: {item.text()}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    self.trigger_live2d_motion(random.randint(0, 9))  # fallback
            else:
                # 如果没有动作列表，使用默认随机动作
                import random
                random_motion = random.randint(0, 9)
                self.trigger_live2d_motion(random_motion)
                
        except Exception as e:
            InfoBar.error(
                title='随机动作失败',
                content=f"无法播放随机动作: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def trigger_custom_action(self, action_num):
        """触发自定义动作 - 通过socket发送请求给main.py"""
        try:
            import socket
            import json
            import time
            
            # 通过socket发送自定义动作请求给main.py
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(2.0)  # 2秒超时
                client_socket.connect(('127.0.0.1', 8889))  # main.py监听的端口
                
                signal_data = {
                    "type": "custom_action",
                    "action_num": action_num,
                    "timestamp": time.time(),
                    "source": "ui_action"
                }
                
                client_socket.send(json.dumps(signal_data).encode('utf-8'))
                client_socket.close()
                
                InfoBar.success(
                    title=f'动作{action_num}',
                    content="已发送动作请求",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
            except (socket.timeout, socket.error) as e:
                InfoBar.warning(
                    title=f'动作{action_num}失败',
                    content=f"无法连接到主服务: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            
        except Exception as e:
            InfoBar.error(
                title=f'动作{action_num}失败',
                content=f"发送动作请求失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def find_motion_index_by_name(self, motion_name):
        """根据动作名称查找动作索引"""
        try:
            if hasattr(self, 'animation_motion_list'):
                for i in range(self.animation_motion_list.count()):
                    item = self.animation_motion_list.item(i)
                    if item and item.text() == motion_name:
                        return item.data(Qt.UserRole)
        except Exception as e:
            print(f"查找动作索引失败: {e}")
        return None
    
    def stop_all_live2d_motions(self):
        """停止所有Live2D动作"""
        try:
            success = False
            
            # 方法1：优先使用实例引用
            if hasattr(self, 'live2d_model') and self.live2d_model:
                try:
                    if hasattr(self.live2d_model, 'model') and self.live2d_model.model:
                        # 停止所有动作组的动作
                        try:
                            self.live2d_model.model.StopMotion("TapBody")
                            self.live2d_model.model.StopMotion("Tap") 
                            self.live2d_model.model.StopMotion("Idle")
                            success = True
                        except:
                            # 如果没有特定的停止方法，尝试播放一个空闲动作
                            self.live2d_model.model.StartMotion("Idle", 0, 1)
                            success = True
                except Exception as e:
                    print(f"通过实例引用停止Live2D动作失败: {e}")
            
            # 方法2：尝试从全局获取Live2D模型实例
            if not success:
                try:
                    import models.live2d_model as live2d_module
                    if hasattr(live2d_module, '_model') and live2d_module._model:
                        model = live2d_module._model
                        if hasattr(model, 'model') and model.model:
                            # 停止所有动作组的动作
                            try:
                                model.model.StopMotion("TapBody")
                                model.model.StopMotion("Tap") 
                                model.model.StopMotion("Idle")
                                success = True
                            except:
                                # 如果没有特定的停止方法，尝试播放一个空闲动作
                                model.model.StartMotion("Idle", 0, 1)
                                success = True
                except Exception as e:
                    print(f"通过全局模块停止Live2D动作失败: {e}")
            
            # 方法3：发送停止所有动作的指令文件
            if not success:
                motion_file = "motion_trigger.tmp"
                with open(motion_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "action": "stop_all_motions",
                        "timestamp": time.time()
                    }))
            
            InfoBar.success(
                title='动作控制',
                content=f"已停止所有动作 {'(直接控制)' if success else '(通过文件)'}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='停止动作失败',
                content=f"无法停止动作: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def trigger_random_expression(self):
        """触发随机表情"""
        try:
            # 从表情列表中随机选择一个
            if hasattr(self, 'animation_expression_list') and self.animation_expression_list.count() > 0:
                import random
                random_index = random.randint(0, self.animation_expression_list.count() - 1)
                item = self.animation_expression_list.item(random_index)
                if item and item.data(Qt.UserRole):
                    expression_name = item.data(Qt.UserRole)
                    self.trigger_live2d_expression(expression_name)
                    
                    InfoBar.success(
                        title='随机表情',
                        content=f"设置表情: {item.text()}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    self.trigger_live2d_expression("default")
            else:
                # 如果没有表情列表，使用默认随机表情
                self.trigger_live2d_expression("random")
                
        except Exception as e:
            InfoBar.error(
                title='随机表情失败',
                content=f"无法设置随机表情: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def trigger_live2d_expression(self, expression_name):
        """触发Live2D表情"""
        try:
            success = False
            
            # 方法1：优先使用实例引用
            if hasattr(self, 'live2d_model') and self.live2d_model:
                try:
                    if hasattr(self.live2d_model, 'set_expression'):
                        if expression_name == "random":
                            self.live2d_model.set_random_expression()
                        else:
                            self.live2d_model.set_expression(expression_name)
                        success = True
                    elif hasattr(self.live2d_model, 'model') and self.live2d_model.model:
                        # 直接调用底层Live2D模型
                        if expression_name == "random":
                            self.live2d_model.model.SetRandomExpression()
                        else:
                            self.live2d_model.model.SetExpression(expression_name)
                        success = True
                except Exception as e:
                    print(f"通过实例引用控制Live2D表情失败: {e}")
            
            # 方法2：尝试从全局获取Live2D模型实例
            if not success:
                try:
                    import models.live2d_model as live2d_module
                    if hasattr(live2d_module, '_model') and live2d_module._model:
                        model = live2d_module._model
                        if hasattr(model, 'set_expression'):
                            if expression_name == "random":
                                model.set_random_expression()
                            else:
                                model.set_expression(expression_name)
                            success = True
                        elif hasattr(model, 'model') and model.model:
                            # 直接调用底层Live2D模型
                            if expression_name == "random":
                                model.model.SetRandomExpression()
                            else:
                                model.model.SetExpression(expression_name)
                            success = True
                except Exception as e:
                    print(f"通过全局模块控制Live2D表情失败: {e}")
            
            # 方法3：通过WebAPI发送请求（已移除，避免404错误）
            # WebAPI Live2D控制功能已移除，使用文件写入方式作为备选
            
            # 方法4：通过文件写入方式向Live2D程序发送表情指令（备选）
            if not success:
                expression_file = "expression_trigger.tmp"
                with open(expression_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "action": "trigger_expression",
                        "expression_name": expression_name,
                        "timestamp": time.time()
                    }))
            
            InfoBar.success(
                title='表情设置',
                content=f"已设置表情: {expression_name} {'(直接控制)' if success else '(通过文件)'}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title='表情设置失败',
                content=f"无法设置表情: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def reset_live2d_expression(self):
        """重置Live2D表情"""
        try:
            success = False
            
            # 方法1：优先使用实例引用
            if hasattr(self, 'live2d_model') and self.live2d_model:
                try:
                    if hasattr(self.live2d_model, 'reset_expression'):
                        self.live2d_model.reset_expression()
                        success = True
                    elif hasattr(self.live2d_model, 'model') and self.live2d_model.model:
                        # 直接调用底层Live2D模型
                        self.live2d_model.model.ResetExpression()
                        success = True
                except Exception as e:
                    print(f"通过实例引用重置Live2D表情失败: {e}")
            
            # 方法2：尝试从全局获取Live2D模型实例
            if not success:
                try:
                    import models.live2d_model as live2d_module
                    if hasattr(live2d_module, '_model') and live2d_module._model:
                        model = live2d_module._model
                        if hasattr(model, 'reset_expression'):
                            model.reset_expression()
                            success = True
                        elif hasattr(model, 'model') and model.model:
                            # 直接调用底层Live2D模型
                            model.model.ResetExpression()
                            success = True
                except Exception as e:
                    print(f"通过全局模块重置Live2D表情失败: {e}")
            
            # 方法3：fallback to default expression
            if not success:
                self.trigger_live2d_expression("default")
            else:
                InfoBar.success(
                    title='表情重置',
                    content="已重置为默认表情 (直接控制)",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            
        except Exception as e:
            InfoBar.error(
                title='重置表情失败',
                content=f"无法重置表情: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def on_animation_expression_click(self, item):
        """点击表情列表项"""
        expression_name = item.data(Qt.UserRole)
        if expression_name:
            self.trigger_live2d_expression(expression_name)
        else:
            # fallback: 使用显示的文本
            self.trigger_live2d_expression(item.text())
    
    def on_animation_motion_click(self, item):
        """点击动作列表项"""
        motion_index = item.data(Qt.UserRole)
        if motion_index is not None:
            self.trigger_live2d_motion(motion_index)
        else:
            # fallback: 尝试从文本解析索引
            try:
                text = item.text()
                if '[' in text and ']' in text:
                    index_str = text.split('[')[1].split(']')[0]
                    motion_index = int(index_str)
                    self.trigger_live2d_motion(motion_index)
            except:
                InfoBar.warning(
                    title='动作播放',
                    content="无法获取动作索引",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def refresh_live2d_model_info(self):
        """刷新Live2D模型信息"""
        try:
            # 更新状态标签
            if hasattr(self, 'model_status_label'):
                self.model_status_label.setText("Live2D状态：正在加载...")
            
            # 清空现有列表
            if hasattr(self, 'animation_expression_list'):
                self.animation_expression_list.clear()
            if hasattr(self, 'animation_motion_list'):
                self.animation_motion_list.clear()
            
            # 尝试从配置文件或模型文件夹加载模型信息
            self.load_live2d_model_lists()
            
        except Exception as e:
            if hasattr(self, 'model_status_label'):
                self.model_status_label.setText(f"Live2D状态：加载失败 - {str(e)}")
            
            InfoBar.error(
                title='模型信息加载失败',
                content=f"无法刷新模型信息: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def load_live2d_model_lists(self):
        """加载Live2D模型的表情和动作列表"""
        try:
            # 检查是否有活跃的Live2D模型
            current_model = self.config_data.get('ui', {}).get('live2d_model', '')
            
            if not current_model:
                # 尝试从模型文件夹扫描
                self.scan_and_load_model_info()
                return
            
            # 尝试从模型配置文件加载
            model_config_path = None
            
            # 搜索可能的模型路径
            possible_paths = [
                f"models/2d/{current_model}",
                f"live-2d/2D/{current_model}",
                f"2D/{current_model}",
                current_model
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    model_config_path = path
                    break
            
            if model_config_path:
                self.load_model_from_path(model_config_path)
            else:
                self.load_default_model_info()
                
        except Exception as e:
            print(f"加载模型列表失败: {e}")
            self.load_default_model_info()
    
    def scan_and_load_model_info(self):
        """扫描并加载模型信息"""
        try:
            # 扫描可能的模型目录
            model_dirs = ["models/2d", "live-2d/2D", "2D", "ai_live2d/models"]
            
            for model_dir in model_dirs:
                if os.path.exists(model_dir):
                    for item in os.listdir(model_dir):
                        item_path = os.path.join(model_dir, item)
                        if os.path.isdir(item_path):
                            # 检查是否是Live2D模型文件夹
                            if any(f.endswith('.model3.json') for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))):
                                self.load_model_from_path(item_path)
                                return
            
            # 如果没有找到模型，加载默认信息
            self.load_default_model_info()
            
        except Exception as e:
            print(f"扫描模型信息失败: {e}")
            self.load_default_model_info()
    
    def load_model_from_path(self, model_path):
        """从指定路径加载模型信息"""
        try:
            # 查找model3.json文件
            model_files = [f for f in os.listdir(model_path) if f.endswith('.model3.json')]
            
            if not model_files:
                self.load_default_model_info()
                return
            
            model_file = os.path.join(model_path, model_files[0])
            
            # 读取模型配置
            with open(model_file, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            # 加载表情
            expressions = []
            if 'FileReferences' in model_data and 'Expressions' in model_data['FileReferences']:
                for expr in model_data['FileReferences']['Expressions']:
                    if 'Name' in expr:
                        expressions.append(expr['Name'])
            
            # 加载动作组
            motions = []
            if 'FileReferences' in model_data and 'Motions' in model_data['FileReferences']:
                for group_name, group_motions in model_data['FileReferences']['Motions'].items():
                    for i, motion in enumerate(group_motions):
                        motion_name = f"{group_name}[{i}]"
                        motions.append((motion_name, i))
            
            # 更新UI列表
            self.update_animation_lists(expressions, motions)
            
            # 更新状态
            if hasattr(self, 'model_status_label'):
                self.model_status_label.setText(f"Live2D状态：已加载模型 - {os.path.basename(model_path)}")
            
        except Exception as e:
            print(f"从路径加载模型失败: {e}")
            self.load_default_model_info()
    
    def load_default_model_info(self):
        """加载默认模型信息"""
        try:
            # 默认表情列表
            default_expressions = [
                "default", "angry", "happy", "sad", "surprised", 
                "blink", "smile", "wink", "normal"
            ]
            
            # 默认动作列表（索引形式）
            default_motions = [
                ("待机动作[0]", 0),
                ("打招呼[1]", 1),
                ("点头[2]", 2),
                ("摇头[3]", 3),
                ("跳舞[4]", 4),
                ("开始唱歌[5]", 5),
                ("兴奋[6]", 6),
                ("停止唱歌[7]", 7),
                ("鼓掌[8]", 8),
                ("挥手[9]", 9)
            ]
            
            self.update_animation_lists(default_expressions, default_motions)
            
            if hasattr(self, 'model_status_label'):
                self.model_status_label.setText("Live2D状态：使用默认配置")
                
        except Exception as e:
            print(f"加载默认模型信息失败: {e}")
            if hasattr(self, 'model_status_label'):
                self.model_status_label.setText(f"Live2D状态：加载失败 - {str(e)}")
    
    def update_animation_lists(self, expressions, motions):
        """更新动画列表显示"""
        try:
            # 更新表情列表
            if hasattr(self, 'animation_expression_list'):
                self.animation_expression_list.clear()
                for expr in expressions:
                    item = QListWidgetItem(expr)
                    item.setData(Qt.UserRole, expr)
                    item.setToolTip(f"双击播放表情: {expr}")
                    self.animation_expression_list.addItem(item)
                
                # 更新表情数量标签
                if hasattr(self, 'expression_count_label'):
                    self.expression_count_label.setText(f"表情数量: {len(expressions)}")
            
            # 更新动作列表
            if hasattr(self, 'animation_motion_list'):
                self.animation_motion_list.clear()
                for motion_name, motion_index in motions:
                    item = QListWidgetItem(motion_name)
                    item.setData(Qt.UserRole, motion_index)
                    item.setToolTip(f"双击播放动作: {motion_name}")
                    self.animation_motion_list.addItem(item)
                
                # 更新动作数量标签
                if hasattr(self, 'motion_count_label'):
                    self.motion_count_label.setText(f"动作数量: {len(motions)}")
            
        except Exception as e:
            print(f"更新动画列表失败: {e}")


class SystemTrayIcon(QSystemTrayIcon):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setIcon(parent.windowIcon())
        self.setToolTip('肥牛菜单')

        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addActions([
            Action('显示肥牛', triggered=self.restore_window),
            Action('直接退出', triggered=self.exit_direct)
        ])
        self.setContextMenu(self.menu)
        # 左键单击托盘图标恢复窗口
        self.activated.connect(self._on_activated)

    def exit_menu(self):
        self.parent().show()
        content = """
            你真的要抛弃肥牛了吗？
        """
        w = MessageBox(
            title='是否关闭菜单',
            content=content,
            parent=self.parent()
        )
        w.yesButton.setText('没错')
        w.cancelButton.setText('我点错啦')
        if w.exec():
            sys.exit()

    def exit_direct(self):
        """直接退出应用程序"""
        sys.exit()

    def restore_window(self):
        w = self.parent()
        w.show()
        w.setWindowState(w.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        w.raise_()
        w.activateWindow()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.restore_window()
        

class StreamReader(QThread):
    """读取子进程标准输出的线程"""
    line = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, proc: subprocess.Popen):
        super().__init__()
        self.proc = proc
        self._running = True

    def run(self):
        try:
            while self._running and self.proc and self.proc.poll() is None:
                try:
                    raw = self.proc.stdout.readline()
                    if not raw:
                        break
                    # 如果是字符串（text=True或encoding指定），直接使用
                    if isinstance(raw, str):
                        s = raw.rstrip()
                    # 如果是字节（二进制模式），解码
                    elif isinstance(raw, bytes):
                        try:
                            s = raw.decode('utf-8').rstrip()
                        except UnicodeDecodeError:
                            try:
                                s = raw.decode('gbk', errors='replace').rstrip()
                            except Exception:
                                s = raw.decode('utf-8', errors='replace').rstrip()
                    else:
                        s = str(raw).rstrip()
                    
                    if s:  # 只发送非空行
                        self.line.emit(s)
                except Exception as e:
                    # 如果读取出现任何错误，记录并继续
                    error_msg = f"读取输出时出错: {str(e)}"
                    self.line.emit(error_msg)
                    break
            if self.proc:
                self.proc.wait()
        finally:
            self.finished.emit()

    def stop(self):
        self._running = False


class TerminalRoom(Interface):
    """终端控制室：两列布局，左侧控制，右侧日志标签"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('Terminal-Room')
        # 浮动按钮对该页无意义
        self.saveButton.hide()
        self.reloadButton.hide()
        self.startButton.hide()
        self.closeButton.hide()

        # 进程与读取器
        self.processes = {}
        self.readers = {}

        # bat 路径（项目根目录）
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.bats = {
            'tts': os.path.join(base_dir, 'TTS.bat'),  # 使用专门的终端TTS脚本
            'asr': os.path.join(base_dir, 'ASR.bat'),
            'bert': os.path.join(base_dir, 'bert.bat'),
            'rag': os.path.join(base_dir, 'RAG.bat'),
        }

        # 右侧日志标签
        self.log_tabs = QTabWidget(self)
        self.logs = {
            'tts': TextBrowser(self),
            'asr': TextBrowser(self),
            'bert': TextBrowser(self),
            'rag': TextBrowser(self),
        }
        self.log_tabs.addTab(self.logs['tts'], '🎵 TTS日志')
        self.log_tabs.addTab(self.logs['asr'], '🎤 ASR日志')
        self.log_tabs.addTab(self.logs['bert'], '🤖 BERT日志')
        self.log_tabs.addTab(self.logs['rag'], '📚 RAG日志')

        # 左侧控制面板
        left_layout = QVBoxLayout()
        left_layout.setSpacing(16)
        self.status_labels = {}
        items = [
            ('tts', 'TTS语音合成', '🎵'),
            ('asr', 'ASR语音识别', '🎤'),
            ('bert', 'BERT模型服务', '🤖'),
            ('rag', 'RAG知识库', '📚'),
        ]
        for key, title, icon in items:
            box = QGroupBox(f'{icon} {title}')
            v = QVBoxLayout(box)
            status = QLabel('状态：服务未启动')
            self.status_labels[key] = status
            btns = QHBoxLayout()
            btn_start = QPushButton(f'启动{key.upper()}')
            btn_stop = QPushButton(f'停止{key.upper()}')
            btn_start.clicked.connect(lambda _, k=key: self.start_service(k))
            btn_stop.clicked.connect(lambda _, k=key: self.stop_service(k))
            btns.addWidget(btn_start)
            btns.addWidget(btn_stop)
            v.addWidget(status)
            v.addLayout(btns)
            left_layout.addWidget(box)
        left_layout.addStretch(1)

        # 两列布局
        two_cols = QHBoxLayout()
        left_container = QWidget(self)
        left_container.setLayout(left_layout)
        two_cols.addWidget(left_container, 0)
        two_cols.addWidget(self.log_tabs, 1)

        # 放入页面
        # 清空现有布局内容
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.vBoxLayout.addLayout(two_cols)

    def _append(self, key: str, text: str):
        w = self.logs.get(key)
        if w:
            w.append(text)

    def _update_status(self, key: str, running: bool):
        lab = self.status_labels.get(key)
        if lab:
            lab.setText(f"状态：{'服务已启动' if running else '服务未启动'}")

    def start_service(self, key: str):
        # 已运行则忽略
        p = self.processes.get(key)
        if p and p.poll() is None:
            self._append(key, '服务已在运行…')
            return
        bat = self.bats.get(key)
        if not bat or not os.path.exists(bat):
            self._append(key, f'未找到脚本：{bat}')
            return
        try:
            bat_abs = os.path.abspath(bat)
            bat_dir = os.path.dirname(bat_abs)
            
            self._append(key, f'{key.upper()}启动中…')
            # 其他服务使用默认方式
            # 判断bat_abs的后缀是否带有ps1（忽略大小写）
            if bat_abs.lower().endswith('.ps1'):
                command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", bat_abs]
            else:
                command = [bat_abs]

            # 使用subprocess启动命令
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=bat_dir,
                shell=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.processes[key] = proc
            
            # 使用StreamReader来处理输出
            reader = StreamReader(proc)
            self.readers[key] = reader
            reader.line.connect(lambda s, k=key: self._append(k, s))
            reader.finished.connect(lambda k=key: self._on_finished(k))
            reader.start()
            self._update_status(key, True)
            
        except Exception as e:
            self._append(key, f'启动失败：{e}')
            self.status_labels[key].setText('状态：启动失败')

    def stop_service(self, key: str):
        proc = self.processes.get(key)
        if not proc or proc.poll() is not None:
            self._append(key, '服务未在运行。')
            return
        reader = self.readers.get(key)
        if reader and reader.isRunning():
            reader.stop()
        try:
            subprocess.run(["taskkill", "/t", "/f", "/pid", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        except Exception as e:
            self._append(key, f'停止异常：{e}')
        self._update_status(key, False)

    def _on_finished(self, key: str):
        self._update_status(key, False)
        self._append(key, '进程已退出。')

class AvatarWidget(NavigationWidget):
    """ Avatar widget """

    def __init__(self, parent=None):
        super().__init__(isSelectable=False, parent=parent)
        self.avatar = QImage('resource/fake_neuro.jpg').scaled(
            24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.SmoothPixmapTransform | QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)

        if self.isPressed:
            painter.setOpacity(0.7)

        # draw background
        if self.isEnter:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        # draw avatar
        painter.setBrush(QBrush(self.avatar))
        painter.translate(8, 6)
        painter.drawEllipse(0, 0, 24, 24)
        painter.translate(-8, -6)

        if not self.isCompacted:
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)
            font = QFont('Segoe UI')
            font.setPixelSize(14)
            painter.setFont(font)
            painter.drawText(QRect(44, 0, 255, 36), Qt.AlignVCenter, '项目简介')


class CustomTitleBar(TitleBar):
    """ Title bar with icon and title """

    def __init__(self, parent):
        super().__init__(parent)
        # add window icon
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(18, 18)
        self.hBoxLayout.insertSpacing(0, 10)
        self.hBoxLayout.insertWidget(1, self.iconLabel, 0, Qt.AlignLeft | Qt.AlignBottom)
        self.window().windowIconChanged.connect(self.setIcon)

        # add title label
        self.titleLabel = QLabel(self)
        self.hBoxLayout.insertWidget(2, self.titleLabel, 0, Qt.AlignLeft | Qt.AlignBottom)
        self.titleLabel.setObjectName('titleLabel')
        self.window().windowTitleChanged.connect(self.setTitle)

        # 轻微样式，模拟 Fluent 关闭按钮的悬停/按下反馈
        self.fluentCloseButton.setStyleSheet(
            "QToolButton{border:none;}"
            "QToolButton:hover{ background-color: rgba(232,17,35,0.15);} "
            "QToolButton:pressed{ background-color: rgba(232,17,35,0.25);} "
        )
        self.fluentCloseButton.clicked.connect(self.window().close)
        self.hBoxLayout.addWidget(self.fluentCloseButton, 0, Qt.AlignRight | Qt.AlignVCenter)

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(18, 18))


class Window(FramelessWindow):

    def __init__(self):
        super().__init__()

        # use dark theme mode
        # setTheme(Theme.DARK)

        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(
            self, showMenuButton=True, showReturnButton=True)
        self.stackWidget = QStackedWidget(self)

        # create sub interface
        self.MainInterface = Widget('Main', 0, parent=self)
        self.LLMInterface = Widget('LLM', 1, parent=self)
        self.ASRInterface = Widget('TTS', 2, parent=self)
        self.TTSInterface = Widget('ASR', 3, parent=self)
        self.Live2dInterface = Widget('Live2d', 4, parent=self)
        self.SubtitleInterface = Widget('Subtitle', 5, parent=self)
        self.UserInputInterface = Widget('UserInput', 6, parent=self)
        self.AnimationInterface = Widget('Animation', 7, parent=self)
        self.OtherInterface = Widget('Others', 8, parent=self)
        self.SettingInterface = Widget('Setting', 9, parent=self)
        self.VoiceCloneInterface = Widget('VoiceClone', 10, parent=self)
        self.TerminalInterface = TerminalRoom(self)

        # 动作按钮悬浮窗口已迁移到main.py中的PetService类


        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()

        # 系统托盘
        self.systemTrayIcon = SystemTrayIcon(self)
        self.systemTrayIcon.show()

        # 注册退出处理函数，确保脚本直接退出时也能关闭worker
        import atexit
        atexit.register(self._shutdown_all_workers)

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

        self.titleBar.raise_()
        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)

    def initNavigation(self):
        # enable acrylic effect
        # self.navigationInterface.setAcrylicEnabled(True)
        self.navigationInterface.addSeparator()

        # 顶部菜单
        self.addSubInterface(self.MainInterface, FIF.HOME_FILL, '主菜单')
        self.addSubInterface(self.LLMInterface, FIF.ROBOT, 'LLM')
        self.addSubInterface(self.ASRInterface, FIF.HEADPHONE, 'ASR')
        self.addSubInterface(self.TTSInterface, FIF.MICROPHONE, 'TTS')
        self.addSubInterface(self.Live2dInterface, FIF.PEOPLE, 'Live 2D')
        self.addSubInterface(self.SubtitleInterface, FIF.FONT, '字幕')
        self.addSubInterface(self.UserInputInterface, FIF.SEND, '对话框')
        self.addSubInterface(self.AnimationInterface, FIF.PLAY, '动画操控')
        self.addSubInterface(self.OtherInterface, FIF.APPLICATION, '其他')
        self.addSubInterface(self.VoiceCloneInterface, FIF.SPEAKERS, '声音克隆')
        terminal_icon = getattr(FIF, 'TERMINAL', getattr(FIF, 'CONSOLE', getattr(FIF, 'CODE', FIF.APPLICATION)))
        self.addSubInterface(self.TerminalInterface, terminal_icon, '终端控制室')

        # 底部自定义小部件
        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=AvatarWidget(),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM
        )

        # 底部设置入口
        self.addSubInterface(self.SettingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)

        # 默认路由
        qrouter.setDefaultRouteKey(self.stackWidget, self.MainInterface.objectName())

        # self.navigationInterface.setExpandWidth(300)

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon('resource/logo.jpg'))
        self.setWindowTitle('My Neuro')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        self.setQss()

        # 初始化动作按钮悬浮窗口状态
        # 动作按钮已迁移到main.py，默认隐藏

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP):
        """ add sub interface """
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            position=position,
            tooltip=text
        )

    def setQss(self):
        color = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{color}/demo.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def switchTo(self, widget):
        self.stackWidget.setCurrentWidget(widget)

    def onCurrentInterfaceChanged(self, index):
        widget = self.stackWidget.widget(index)
        self.navigationInterface.setCurrentItem(widget.objectName())
        qrouter.push(self.stackWidget, widget.objectName())

    def showMessageBox(self):
        w = MessageBox(
            '欢迎使用肥牛菜单！！！',
            '如果你喜欢本项目的话记得在GitHub上点个⭐，你的支持就是我们最大的动力！',
            self
        )
        w.yesButton.setText('那必须的')
        w.cancelButton.setText('下次一定')

        if w.exec():
            QDesktopServices.openUrl(QUrl("https://github.com/morettt/my-neuro"))

    def resizeEvent(self, e):
        self.titleBar.move(46, 0)
        self.titleBar.resize(self.width()-46, self.titleBar.height())

    def closeEvent(self, event):
        # 先显示一个简单的退出确认，使用与项目介绍相同风格的MessageBox
        w = MessageBox(
            '是否退出程序？',
            '你真的要离开肥牛了吗？\n\n点击"确定"直接退出，点击"取消"将最小化到托盘~',
            self
        )
        w.yesButton.setText('直接退出')
        w.cancelButton.setText('最小化到托盘')

        if w.exec():
            # 用户选择直接退出
            event.accept()
            
            # 关闭所有worker线程
            self._shutdown_all_workers()
            
            # 关闭动作按钮悬浮窗口
            # 动作按钮已迁移到main.py，由main.py负责关闭
            # 隐藏系统托盘
            if self.systemTrayIcon:
                self.systemTrayIcon.hide()
        else:
            # 用户选择最小化到托盘
            event.ignore()
            self.hide()
            if self.systemTrayIcon:
                self.systemTrayIcon.showMessage(
                    '肥牛提醒',
                    '肥牛已经躲到托盘里啦~ 点击托盘图标可以重新召唤我哦！',
                    QSystemTrayIcon.Information,
                    3000
                )

    def _shutdown_all_workers(self):
        """关闭所有后台worker线程"""
        try:
            # 1. 停止BAT worker (主界面)
            if hasattr(self, 'MainInterface') and self.MainInterface and hasattr(self.MainInterface, 'bat_worker') and self.MainInterface.bat_worker:
                if self.MainInterface.bat_worker.isRunning():
                    self.MainInterface.bat_worker.stop()
                    # 等待线程结束，最多等待5秒
                    if not self.MainInterface.bat_worker.wait(5000):
                        self.MainInterface.bat_worker.terminate()
                        self.MainInterface.bat_worker.wait()
            
            # 2. 停止训练worker (声音克隆界面)
            if hasattr(self, 'VoiceCloneInterface') and self.VoiceCloneInterface and hasattr(self.VoiceCloneInterface, 'train_worker') and self.VoiceCloneInterface.train_worker:
                if self.VoiceCloneInterface.train_worker.isRunning():
                    self.VoiceCloneInterface.train_worker.stop()
                    # 等待线程结束，最多等待5秒
                    if not self.VoiceCloneInterface.train_worker.wait(5000):
                        self.VoiceCloneInterface.train_worker.terminate()
                        self.VoiceCloneInterface.train_worker.wait()
            
            # 3. 停止WebAPI服务器
            if hasattr(self, 'MainInterface') and self.MainInterface and hasattr(self.MainInterface, 'webapi_server') and self.MainInterface.webapi_server:
                try:
                    self.MainInterface.stop_webapi_server()
                except:
                    pass  # 忽略可能的错误，因为应用可能正在关闭
            
            # 4. 停止模型获取worker
            if hasattr(self, 'MainInterface') and self.MainInterface and hasattr(self.MainInterface, '_model_fetchers'):
                for fetcher in self.MainInterface._model_fetchers:
                    if fetcher and fetcher.isRunning():
                        fetcher.quit()
                        fetcher.wait(2000)
            
            # 5. 清理MCP相关异步任务
            if hasattr(self, 'MainInterface') and self.MainInterface and hasattr(self.MainInterface, 'mcp_manager'):
                # 这里可以添加MCP相关的清理逻辑
                pass
            
            # 6. 停止TerminalRoom中的所有服务进程
            if hasattr(self, 'TerminalInterface') and self.TerminalInterface:
                try:
                    # 停止所有TerminalRoom中的进程
                    for key in ['tts', 'asr', 'bert', 'rag']:
                        proc = self.TerminalInterface.processes.get(key)
                        if proc and proc.poll() is None:
                            # 停止对应的reader线程
                            reader = self.TerminalInterface.readers.get(key)
                            if reader and reader.isRunning():
                                reader.stop()
                            # 强制终止进程
                            try:
                                import subprocess
                                subprocess.run(["taskkill", "/t", "/f", "/pid", str(proc.pid)],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                             creationflags=0x08000000)
                            except Exception as e:
                                print(f"停止TerminalRoom进程 {key} 时出错: {e}")
                except Exception as e:
                    print(f"停止TerminalRoom进程时出错: {e}")
            
            # 7. 停止音频播放
            if hasattr(self, 'MainInterface') and self.MainInterface:
                try:
                    self.MainInterface.stop_audio_playback()
                except Exception as e:
                    print(f"停止音频播放时出错: {e}")
            
            print("所有worker线程和进程已关闭")
            
        except Exception as e:
            print(f"关闭worker线程时出错: {e}")

    def changeEvent(self, e):
        super().changeEvent(e)
        # 点击最小化按钮时，隐藏到托盘
        if e.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                # 同时隐藏动作按钮悬浮窗口
                # 动作按钮已迁移到main.py，由main.py管理
                if self.systemTrayIcon:
                    self.systemTrayIcon.showMessage('提示', '程序已最小化到托盘', QSystemTrayIcon.Information, 2000)

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 主窗口显示时，动作按钮由main.py管理
        # 动作按钮已迁移到main.py，根据设置和BAT运行状态由main.py控制显示

    def close_bat_msg(self):
        """重写关闭方法，动作按钮由main.py管理"""
        # 动作按钮悬浮窗口已迁移到main.py，由main.py负责关闭

    def interrupt_current_operations(self):
        """打断当前AI输出和语音播放"""
        try:
            # 调用MainInterface的interrupt_current_operations方法
            if hasattr(self, 'MainInterface') and hasattr(self.MainInterface, 'interrupt_current_operations'):
                return self.MainInterface.interrupt_current_operations()
            else:
                print("MainInterface或interrupt_current_operations方法不存在")
                return False
        except Exception as e:
            print(f"Window类打断操作时出错: {e}")
            return False


class Live2DPreviewWindow(QDialog):
    """Live2D模型预览窗口 - 支持动态预览"""
    
    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model_name = os.path.basename(os.path.dirname(model_path))
        self.model_data = None
        self.live2d_widget = None
        self.current_expression = None
        self.current_motion = None
        self.init_ui()
        self.load_model_preview()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"Live2D动态预览 - {self.model_name}")
        self.setWindowIcon(QIcon("resources/logo.png"))
        self.resize(1000, 700)
        
        # 设置窗口标志
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel(f"🎭 Live2D动态预览")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #0078d4;
                padding: 5px;
            }
        """)
        title_layout.addWidget(title_label)
        
        # 预览模式切换
        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItems(["静态预览", "动态预览"])
        self.preview_mode_combo.currentTextChanged.connect(self.on_preview_mode_changed)
        title_layout.addWidget(QLabel("预览模式:"))
        title_layout.addWidget(self.preview_mode_combo)
        
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕ 关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        main_layout.addLayout(title_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：模型信息和控制
        left_widget = self.create_control_panel()
        splitter.addWidget(left_widget)
        
        # 右侧：预览区域
        right_widget = self.create_preview_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([350, 650])
        main_layout.addWidget(splitter)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("正在加载模型信息...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # 操作按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_model_preview)
        status_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(status_layout)
    
    def create_control_panel(self):
        """创建控制面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 模型信息显示
        info_group = QGroupBox("📋 模型信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_browser = QTextBrowser()
        self.info_browser.setMaximumHeight(180)
        self.info_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 11px;
            }
        """)
        info_layout.addWidget(self.info_browser)
        layout.addWidget(info_group)
        
        # 表情控制
        expr_group = QGroupBox("😊 表情控制")
        expr_layout = QVBoxLayout(expr_group)
        
        self.expr_list = QListWidget()
        self.expr_list.setMaximumHeight(120)
        self.expr_list.itemClicked.connect(self.on_expression_selected)
        self.expr_list.itemDoubleClicked.connect(self.on_expression_double_clicked)
        expr_layout.addWidget(self.expr_list)
        
        # 表情控制按钮
        expr_btn_layout = QHBoxLayout()
        self.apply_expr_btn = QPushButton("应用表情")
        self.reset_expr_btn = QPushButton("重置表情")
        self.apply_expr_btn.clicked.connect(self.apply_current_expression)
        self.reset_expr_btn.clicked.connect(self.reset_expression)
        self.apply_expr_btn.setEnabled(False)
        expr_btn_layout.addWidget(self.apply_expr_btn)
        expr_btn_layout.addWidget(self.reset_expr_btn)
        expr_layout.addLayout(expr_btn_layout)
        
        layout.addWidget(expr_group)
        
        # 动作控制
        motion_group = QGroupBox("🎬 动作控制")
        motion_layout = QVBoxLayout(motion_group)
        
        self.motion_list = QListWidget()
        self.motion_list.setMaximumHeight(120)
        self.motion_list.itemClicked.connect(self.on_motion_selected)
        self.motion_list.itemDoubleClicked.connect(self.on_motion_double_clicked)
        motion_layout.addWidget(self.motion_list)
        
        # 动作控制按钮
        motion_btn_layout = QHBoxLayout()
        self.play_motion_btn = QPushButton("播放动作")
        self.stop_motion_btn = QPushButton("停止动作")
        self.play_motion_btn.clicked.connect(self.play_current_motion)
        self.stop_motion_btn.clicked.connect(self.stop_motion)
        self.play_motion_btn.setEnabled(False)
        motion_btn_layout.addWidget(self.play_motion_btn)
        motion_btn_layout.addWidget(self.stop_motion_btn)
        motion_layout.addLayout(motion_btn_layout)
        
        # 动作设置
        motion_settings_layout = QFormLayout()
        self.motion_loop_check = CheckBox()
        self.motion_loop_check.setText("循环播放")
        self.motion_loop_check.setChecked(False)
        motion_settings_layout.addRow("播放设置:", self.motion_loop_check)
        motion_layout.addLayout(motion_settings_layout)
        
        layout.addWidget(motion_group)
        
        # 全局控制
        global_group = QGroupBox("🎮 全局控制")
        global_layout = QVBoxLayout(global_group)
        
        global_btn_layout = QHBoxLayout()
        self.reset_all_btn = QPushButton("🔄 重置全部")
        self.random_motion_btn = QPushButton("🎲 随机动作")
        self.random_expr_btn = QPushButton("🎭 随机表情")
        
        self.reset_all_btn.clicked.connect(self.reset_all)
        self.random_motion_btn.clicked.connect(self.play_random_motion)
        self.random_expr_btn.clicked.connect(self.apply_random_expression)
        
        global_btn_layout.addWidget(self.reset_all_btn)
        global_btn_layout.addWidget(self.random_motion_btn)
        global_btn_layout.addWidget(self.random_expr_btn)
        global_layout.addLayout(global_btn_layout)
        
        layout.addWidget(global_group)
        
        layout.addStretch()
        return widget
    
    def create_preview_panel(self):
        """创建预览面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 预览标题和控制
        header_layout = QHBoxLayout()
        preview_label = QLabel("🖼️ 模型预览")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        header_layout.addWidget(preview_label)
        
        header_layout.addStretch()
        
        # 预览质量设置
        quality_label = QLabel("渲染质量:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量", "标准", "性能优先"])
        self.quality_combo.setCurrentText("标准")
        header_layout.addWidget(quality_label)
        header_layout.addWidget(self.quality_combo)
        
        layout.addLayout(header_layout)
        
        # 创建预览区域容器
        self.preview_container = QWidget()
        self.preview_container.setMinimumSize(600, 450)
        self.preview_container.setStyleSheet("""
            QWidget {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: #ecf0f1;
            }
        """)
        
        # 预览区域布局
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        # 静态预览区域
        self.static_preview_area = QLabel()
        self.static_preview_area.setAlignment(Qt.AlignCenter)
        self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n选择上方'动态预览'模式\n体验真实Live2D动画")
        self.static_preview_area.setStyleSheet("""
            QLabel {
                border: none;
                background-color: transparent;
                color: #7f8c8d;
                font-size: 14px;
            }
        """)
        preview_layout.addWidget(self.static_preview_area)
        
        # 动态预览区域 (将在需要时创建)
        self.dynamic_preview_area = None
        
        layout.addWidget(self.preview_container)
        
        # 预览控制面板
        control_group = QGroupBox("预览控制")
        control_layout = QGridLayout(control_group)
        
        # 播放控制
        self.play_btn = QPushButton("▶️ 开始动画")
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.reset_pose_btn = QPushButton("🔄 重置姿态")
        
        self.play_btn.clicked.connect(self.start_animation)
        self.pause_btn.clicked.connect(self.pause_animation)
        self.reset_pose_btn.clicked.connect(self.reset_pose)
        
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        control_layout.addWidget(self.play_btn, 0, 0)
        control_layout.addWidget(self.pause_btn, 0, 1)
        control_layout.addWidget(self.reset_pose_btn, 0, 2)
        
        # 视图控制
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_widget = QWidget()
        zoom_widget.setLayout(zoom_layout)
        control_layout.addWidget(zoom_widget, 1, 0, 1, 3)
        
        layout.addWidget(control_group)
        
        return widget
    
    def on_preview_mode_changed(self, mode):
        """预览模式切换处理"""
        if mode == "动态预览":
            self.enable_dynamic_preview()
        else:
            self.enable_static_preview()
    
    def enable_static_preview(self):
        """启用静态预览模式"""
        try:
            # 隐藏动态预览组件
            if self.dynamic_preview_area:
                self.dynamic_preview_area.hide()
            
            # 显示静态预览
            self.static_preview_area.show()
            self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n选择上方'动态预览'模式\n体验真实Live2D动画")
            
            # 禁用动态控制
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.apply_expr_btn.setEnabled(False)
            self.play_motion_btn.setEnabled(False)
            
            self.status_label.setText("静态预览模式 - 显示模型信息和资源列表")
            
        except Exception as e:
            print(f"切换到静态预览模式失败: {e}")
    
    def enable_dynamic_preview(self):
        """启用动态预览模式"""
        try:
            # 隐藏静态预览
            self.static_preview_area.hide()
            
            # 创建或显示动态预览组件
            if not self.dynamic_preview_area:
                self.create_dynamic_preview_widget()
            
            if self.dynamic_preview_area:
                self.dynamic_preview_area.show()
                # 启动Live2D模型
                self.start_live2d_preview()
                
                # 启用动态控制
                self.play_btn.setEnabled(True)
                self.pause_btn.setEnabled(True)
                self.apply_expr_btn.setEnabled(True)
                self.play_motion_btn.setEnabled(True)
                
                self.status_label.setText("动态预览模式 - Live2D实时渲染")
            else:
                # 回退到静态模式
                self.preview_mode_combo.setCurrentText("静态预览")
                self.status_label.setText("动态预览初始化失败，已回退到静态模式")
                
        except Exception as e:
            print(f"切换到动态预览模式失败: {e}")
            self.preview_mode_combo.setCurrentText("静态预览")
            self.status_label.setText(f"动态预览启动失败: {str(e)}")
    
    def create_dynamic_preview_widget(self):
        """创建动态预览组件"""
        try:
            # 检查是否可以导入Live2D相关模块
            try:
                from main import Live2DApp
                live2d_available = True
            except ImportError:
                live2d_available = False
            
            if live2d_available:
                # 创建Live2D预览组件
                self.dynamic_preview_area = Live2DPreviewWidget(
                    model_path=self.model_path,
                    parent=self.preview_container
                )
                
                # 添加到预览容器布局
                layout = self.preview_container.layout()
                layout.addWidget(self.dynamic_preview_area)
                
                # 连接信号
                if hasattr(self.dynamic_preview_area, 'expression_changed'):
                    self.dynamic_preview_area.expression_changed.connect(self.on_dynamic_expression_changed)
                if hasattr(self.dynamic_preview_area, 'motion_changed'):
                    self.dynamic_preview_area.motion_changed.connect(self.on_dynamic_motion_changed)
                    
                print("动态预览组件创建成功")
                
            else:
                # 创建模拟Live2D组件
                self.dynamic_preview_area = QLabel()
                self.dynamic_preview_area.setAlignment(Qt.AlignCenter)
                self.dynamic_preview_area.setText("🎭\n\nLive2D动态预览\n\n模拟Live2D渲染区域\n\n(实际项目中此处会显示真实的Live2D动画)")
                self.dynamic_preview_area.setStyleSheet("""
                    QLabel {
                        border: 2px solid #3498db;
                        border-radius: 8px;
                        background-color: #f8f9fa;
                        color: #2c3e50;
                        font-size: 14px;
                    }
                """)
                
                # 添加到预览容器布局
                layout = self.preview_container.layout()
                layout.addWidget(self.dynamic_preview_area)
                
                print("创建模拟Live2D预览组件")
                
        except Exception as e:
            print(f"创建动态预览组件失败: {e}")
            self.dynamic_preview_area = None
    
    def start_live2d_preview(self):
        """启动Live2D预览"""
        try:
            if hasattr(self.dynamic_preview_area, 'load_model'):
                self.dynamic_preview_area.load_model(self.model_path)
                self.status_label.setText("Live2D模型加载成功")
            else:
                # 模拟启动
                if isinstance(self.dynamic_preview_area, QLabel):
                    self.dynamic_preview_area.setText("🎭\n\nLive2D动态预览已启动\n\n模型路径: " + 
                                                    os.path.basename(self.model_path) + 
                                                    "\n\n双击左侧列表项体验动画效果")
                self.status_label.setText("Live2D模拟预览已启动")
                
        except Exception as e:
            print(f"启动Live2D预览失败: {e}")
            self.status_label.setText(f"Live2D预览启动失败: {str(e)}")
    
    def on_dynamic_expression_changed(self, expression_name):
        """动态预览表情变化回调"""
        self.status_label.setText(f"当前表情: {expression_name}")
    
    def on_dynamic_motion_changed(self, motion_name):
        """动态预览动作变化回调"""
        self.status_label.setText(f"正在播放动作: {motion_name}")
    
    # 表情控制方法
    def on_expression_selected(self, item):
        """表情选择处理"""
        self.current_expression = item.text()
        self.apply_expr_btn.setEnabled(True)
        self.status_label.setText(f"已选择表情: {self.current_expression}")
    
    def on_expression_double_clicked(self, item):
        """表情双击处理 - 直接应用"""
        self.current_expression = item.text()
        self.apply_current_expression()
    
    def apply_current_expression(self):
        """应用当前选中的表情"""
        if not self.current_expression:
            return
            
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                # 动态预览模式
                if hasattr(self.dynamic_preview_area, 'set_expression'):
                    self.dynamic_preview_area.set_expression(self.current_expression)
                    self.status_label.setText(f"已应用表情: {self.current_expression}")
                else:
                    # 模拟应用表情
                    if isinstance(self.dynamic_preview_area, QLabel):
                        self.dynamic_preview_area.setText(f"🎭\n\nLive2D动态预览\n\n当前表情: {self.current_expression}\n\n表情已应用到模型")
                    self.status_label.setText(f"模拟应用表情: {self.current_expression}")
            else:
                # 静态预览模式
                self.static_preview_area.setText(f"🎭\n\nLive2D模型预览\n\n当前表情: {self.current_expression}\n\n切换到动态预览模式\n查看真实表情效果")
                self.status_label.setText(f"静态预览 - 选中表情: {self.current_expression}")
                
        except Exception as e:
            print(f"应用表情失败: {e}")
            self.status_label.setText(f"应用表情失败: {str(e)}")
    
    def reset_expression(self):
        """重置表情"""
        try:
            self.current_expression = None
            self.expr_list.clearSelection()
            self.apply_expr_btn.setEnabled(False)
            
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'reset_expression'):
                    self.dynamic_preview_area.reset_expression()
                else:
                    # 模拟重置
                    if isinstance(self.dynamic_preview_area, QLabel):
                        self.dynamic_preview_area.setText("🎭\n\nLive2D动态预览\n\n表情已重置为默认状态\n\n双击左侧列表项体验动画效果")
                self.status_label.setText("表情已重置")
            else:
                self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n表情已重置\n\n选择上方'动态预览'模式\n体验真实Live2D动画")
                self.status_label.setText("静态预览 - 表情已重置")
                
        except Exception as e:
            print(f"重置表情失败: {e}")
            self.status_label.setText(f"重置表情失败: {str(e)}")
    
    # 动作控制方法
    def on_motion_selected(self, item):
        """动作选择处理"""
        self.current_motion = item.text()
        self.play_motion_btn.setEnabled(True)
        self.status_label.setText(f"已选择动作: {self.current_motion}")
    
    def on_motion_double_clicked(self, item):
        """动作双击处理 - 直接播放"""
        self.current_motion = item.text()
        self.play_current_motion()
    
    def play_current_motion(self):
        """播放当前选中的动作"""
        if not self.current_motion:
            return
            
        try:
            loop_enabled = self.motion_loop_check.isChecked()
            
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                # 动态预览模式
                if hasattr(self.dynamic_preview_area, 'play_motion'):
                    self.dynamic_preview_area.play_motion(self.current_motion, loop=loop_enabled)
                    self.status_label.setText(f"正在播放动作: {self.current_motion} {'(循环)' if loop_enabled else ''}")
                else:
                    # 模拟播放动作
                    if isinstance(self.dynamic_preview_area, QLabel):
                        self.dynamic_preview_area.setText(f"🎭\n\nLive2D动态预览\n\n正在播放动作: {self.current_motion}\n\n{'循环播放模式' if loop_enabled else '单次播放模式'}")
                    self.status_label.setText(f"模拟播放动作: {self.current_motion}")
            else:
                # 静态预览模式
                self.static_preview_area.setText(f"🎭\n\nLive2D模型预览\n\n选中动作: {self.current_motion}\n\n切换到动态预览模式\n查看真实动作效果")
                self.status_label.setText(f"静态预览 - 选中动作: {self.current_motion}")
                
        except Exception as e:
            print(f"播放动作失败: {e}")
            self.status_label.setText(f"播放动作失败: {str(e)}")
    
    def stop_motion(self):
        """停止动作播放"""
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'stop_motion'):
                    self.dynamic_preview_area.stop_motion()
                else:
                    # 模拟停止
                    if isinstance(self.dynamic_preview_area, QLabel):
                        self.dynamic_preview_area.setText("🎭\n\nLive2D动态预览\n\n动作播放已停止\n\n双击左侧列表项体验动画效果")
                self.status_label.setText("动作播放已停止")
            else:
                self.status_label.setText("静态预览模式 - 无动作播放")
                
        except Exception as e:
            print(f"停止动作失败: {e}")
            self.status_label.setText(f"停止动作失败: {str(e)}")
    
    # 全局控制方法
    def reset_all(self):
        """重置所有状态"""
        try:
            self.reset_expression()
            self.stop_motion()
            self.current_motion = None
            self.motion_list.clearSelection()
            self.play_motion_btn.setEnabled(False)
            
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'reset_pose'):
                    self.dynamic_preview_area.reset_pose()
                else:
                    # 模拟重置
                    if isinstance(self.dynamic_preview_area, QLabel):
                        self.dynamic_preview_area.setText("🎭\n\nLive2D动态预览\n\n所有状态已重置\n\n双击左侧列表项体验动画效果")
                self.status_label.setText("所有状态已重置")
            else:
                self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n所有状态已重置\n\n选择上方'动态预览'模式\n体验真实Live2D动画")
                self.status_label.setText("静态预览 - 所有状态已重置")
                
        except Exception as e:
            print(f"重置失败: {e}")
            self.status_label.setText(f"重置失败: {str(e)}")
    
    def play_random_motion(self):
        """播放随机动作"""
        try:
            if self.motion_list.count() > 0:
                import random
                random_index = random.randint(0, self.motion_list.count() - 1)
                random_item = self.motion_list.item(random_index)
                self.motion_list.setCurrentItem(random_item)
                self.current_motion = random_item.text()
                self.play_current_motion()
            else:
                self.status_label.setText("没有可用的动作")
        except Exception as e:
            print(f"播放随机动作失败: {e}")
            self.status_label.setText(f"播放随机动作失败: {str(e)}")
    
    def apply_random_expression(self):
        """应用随机表情"""
        try:
            if self.expr_list.count() > 0:
                import random
                random_index = random.randint(0, self.expr_list.count() - 1)
                random_item = self.expr_list.item(random_index)
                self.expr_list.setCurrentItem(random_item)
                self.current_expression = random_item.text()
                self.apply_current_expression()
            else:
                self.status_label.setText("没有可用的表情")
        except Exception as e:
            print(f"应用随机表情失败: {e}")
            self.status_label.setText(f"应用随机表情失败: {str(e)}")
    
    # 播放控制方法
    def start_animation(self):
        """开始动画"""
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'start_animation'):
                    self.dynamic_preview_area.start_animation()
                self.status_label.setText("Live2D动画已开始")
            else:
                self.status_label.setText("请切换到动态预览模式")
        except Exception as e:
            print(f"开始动画失败: {e}")
            self.status_label.setText(f"开始动画失败: {str(e)}")
    
    def pause_animation(self):
        """暂停动画"""
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'pause_animation'):
                    self.dynamic_preview_area.pause_animation()
                self.status_label.setText("Live2D动画已暂停")
            else:
                self.status_label.setText("请切换到动态预览模式")
        except Exception as e:
            print(f"暂停动画失败: {e}")
            self.status_label.setText(f"暂停动画失败: {str(e)}")
    
    def reset_pose(self):
        """重置姿态"""
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'reset_pose'):
                    self.dynamic_preview_area.reset_pose()
                self.status_label.setText("Live2D姿态已重置")
            else:
                self.status_label.setText("请切换到动态预览模式")
        except Exception as e:
            print(f"重置姿态失败: {e}")
            self.status_label.setText(f"重置姿态失败: {str(e)}")
    
    def on_zoom_changed(self, value):
        """缩放变化处理"""
        self.zoom_label.setText(f"{value}%")
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'set_zoom'):
                    self.dynamic_preview_area.set_zoom(value / 100.0)
        except Exception as e:
            print(f"设置缩放失败: {e}")
    
    def load_model_preview(self):
        """加载模型预览数据"""
        try:
            self.status_label.setText("正在加载模型数据...")
            
            # 加载模型数据
            if os.path.exists(self.model_path):
                self.model_data = self.load_model_details_fallback(self.model_path)
                
                if self.model_data:
                    # 更新模型信息
                    self.update_model_info()
                    
                    # 更新表情列表
                    self.update_expression_list()
                    
                    # 更新动作列表
                    self.update_motion_list()
                    
                    # 尝试加载预览图
                    self.load_preview_image_enhanced()
                    
                    self.status_label.setText(f"模型加载完成 - {self.model_name}")
                else:
                    self.status_label.setText("模型数据加载失败")
                    self.info_browser.setText("❌ 模型数据加载失败\n\n请检查模型文件是否完整")
            else:
                self.status_label.setText("模型文件不存在")
                self.info_browser.setText("❌ 模型文件不存在\n\n请检查模型路径是否正确")
                
        except Exception as e:
            print(f"加载模型预览失败: {e}")
            self.status_label.setText(f"加载失败: {str(e)}")
            self.info_browser.setText(f"❌ 加载模型预览失败\n\n错误信息: {str(e)}")
    
    def load_model_details_fallback(self, model_path):
        """加载模型详细信息的回退方法"""
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"回退加载模型失败: {e}")
            return None
    
    def update_model_info(self):
        """更新模型信息显示"""
        try:
            if not self.model_data:
                return
                
            info_html = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h3 style="color: #2c3e50; margin: 0 0 10px 0;">🎭 {self.model_name}</h3>
                
                <p><strong>📁 文件路径:</strong><br>
                <span style="font-size: 10px; color: #7f8c8d;">{self.model_path}</span></p>
                
                <p><strong>📋 基本信息:</strong><br>
                • 版本: {self.model_data.get('Version', 'Unknown')}<br>
                • 物理文件: {self.model_data.get('PhysicsFileName', 'None')}<br>
                • 姿态文件: {self.model_data.get('PoseFileName', 'None')}</p>
                
                <p><strong>🎨 纹理信息:</strong><br>
                • 纹理数量: {len(self.model_data.get('FileReferences', {}).get('Textures', []))}<br>
                • 模型文件: {len(self.model_data.get('FileReferences', {}).get('Moc', []))}</p>
                
                <p><strong>🎭 动画资源:</strong><br>
                • 表情数量: {len(self.model_data.get('FileReferences', {}).get('Expressions', []))}<br>
                • 动作数量: {sum(len(motions) for motions in self.model_data.get('FileReferences', {}).get('Motions', {}).values())}</p>
            </div>
            """
            
            self.info_browser.setHtml(info_html)
            
        except Exception as e:
            print(f"更新模型信息失败: {e}")
            self.info_browser.setText(f"更新模型信息失败: {str(e)}")
    
    def update_expression_list(self):
        """更新表情列表"""
        try:
            self.expr_list.clear()
            
            if not self.model_data:
                return
                
            expressions = self.model_data.get('FileReferences', {}).get('Expressions', [])
            
            if expressions:
                for expr in expressions:
                    if isinstance(expr, dict):
                        name = expr.get('Name', '未知表情')
                        file_path = expr.get('File', '')
                        item_text = f"😊 {name}"
                        if file_path:
                            item_text += f" ({os.path.basename(file_path)})"
                    else:
                        item_text = f"😊 {str(expr)}"
                    
                    item = QListWidgetItem(item_text)
                    item.setToolTip(f"双击应用表情: {name if isinstance(expr, dict) else str(expr)}")
                    self.expr_list.addItem(item)
            else:
                item = QListWidgetItem("😔 无可用表情")
                item.setFlags(Qt.NoItemFlags)
                self.expr_list.addItem(item)
                
        except Exception as e:
            print(f"更新表情列表失败: {e}")
            item = QListWidgetItem(f"❌ 加载表情失败: {str(e)}")
            item.setFlags(Qt.NoItemFlags)
            self.expr_list.addItem(item)
    
    def update_motion_list(self):
        """更新动作列表"""
        try:
            self.motion_list.clear()
            
            if not self.model_data:
                return
                
            motions = self.model_data.get('FileReferences', {}).get('Motions', {})
            
            if motions:
                for category, motion_list in motions.items():
                    # 添加分类标题
                    category_item = QListWidgetItem(f"📁 {category}")
                    category_item.setFlags(Qt.NoItemFlags)
                    category_item.setBackground(QColor("#f0f0f0"))
                    self.motion_list.addItem(category_item)
                    
                    # 添加该分类下的动作
                    for motion in motion_list:
                        if isinstance(motion, dict):
                            name = motion.get('File', '未知动作')
                            name = os.path.splitext(os.path.basename(name))[0]  # 移除扩展名
                            item_text = f"  🎬 {name}"
                            if 'FadeInTime' in motion or 'FadeOutTime' in motion:
                                fade_in = motion.get('FadeInTime', 0)
                                fade_out = motion.get('FadeOutTime', 0)
                                item_text += f" (淡入:{fade_in}s 淡出:{fade_out}s)"
                        else:
                            item_text = f"  🎬 {str(motion)}"
                        
                        item = QListWidgetItem(item_text)
                        item.setToolTip(f"双击播放动作: {name if isinstance(motion, dict) else str(motion)}")
                        self.motion_list.addItem(item)
            else:
                item = QListWidgetItem("😔 无可用动作")
                item.setFlags(Qt.NoItemFlags)
                self.motion_list.addItem(item)
                
        except Exception as e:
            print(f"更新动作列表失败: {e}")
            item = QListWidgetItem(f"❌ 加载动作失败: {str(e)}")
            item.setFlags(Qt.NoItemFlags)
            self.motion_list.addItem(item)
    
    def load_preview_image_enhanced(self):
        """加载预览图像 - 增强版本"""
        try:
            model_dir = os.path.dirname(self.model_path)
            
            # 查找可能的预览图片
            preview_files = ['preview.png', 'preview.jpg', 'thumbnail.png', 'icon.png']
            
            # 首先检查纹理文件
            if self.model_data:
                texture_files = self.model_data.get('FileReferences', {}).get('Textures', [])
                if texture_files:
                    # 使用第一个纹理作为预览
                    texture_path = os.path.join(model_dir, texture_files[0])
                    if os.path.exists(texture_path):
                        self.display_preview_image_enhanced(texture_path, "纹理预览")
                        return
            
            # 查找预览图片
            for preview_file in preview_files:
                preview_path = os.path.join(model_dir, preview_file)
                if os.path.exists(preview_path):
                    self.display_preview_image_enhanced(preview_path, "模型预览")
                    return
            
            # 没找到预览图，显示默认内容
            self.update_static_preview_text()
            
        except Exception as e:
            print(f"加载预览图像失败: {e}")
            self.update_static_preview_text()
    
    def display_preview_image_enhanced(self, image_path, image_type):
        """显示预览图像 - 增强版本"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放图像以适应预览区域
                scaled_pixmap = pixmap.scaled(
                    self.static_preview_area.size() * 0.8,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.static_preview_area.setPixmap(scaled_pixmap)
                self.status_label.setText(f"✅ {image_type}加载成功 - {os.path.basename(image_path)}")
            else:
                self.update_static_preview_text()
                self.status_label.setText(f"❌ {image_type}加载失败")
        except Exception as e:
            print(f"显示预览图像失败: {e}")
            self.update_static_preview_text()
            self.status_label.setText(f"❌ 图像显示错误: {str(e)}")
    
    def update_static_preview_text(self):
        """更新静态预览文本"""
        try:
            if hasattr(self, 'model_data') and self.model_data:
                expressions = self.model_data.get('FileReferences', {}).get('Expressions', [])
                motions = self.model_data.get('FileReferences', {}).get('Motions', {})
                motion_count = sum(len(motion_list) for motion_list in motions.values())
                
                preview_text = f"🎭\n\n{self.model_name}\n\nLive2D模型预览\n\n📊 表情: {len(expressions)} 个\n🎬 动作: {motion_count} 个\n\n双击左侧列表体验功能\n\n切换到'动态预览'模式\n查看Live2D实时渲染"
            else:
                preview_text = "🎭\n\nLive2D模型预览\n\n选择上方'动态预览'模式\n体验真实Live2D动画"
            
            self.static_preview_area.setText(preview_text)
        except Exception as e:
            print(f"更新静态预览文本失败: {e}")
            self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n加载中...")
    
    
class Live2DPreviewWidget(QWidget):
    """Live2D动态预览组件"""
    
    # 定义信号
    expression_changed = pyqtSignal(str)
    motion_changed = pyqtSignal(str)
    
    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model_data = None
        self.current_expression = None
        self.current_motion = None
        self.animation_timer = None
        self.zoom_factor = 1.0
        self.init_widget()
        
    def init_widget(self):
        """初始化组件"""
        self.setStyleSheet("""
            Live2DPreviewWidget {
                border: 2px solid #3498db;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 状态标签
        self.status_label = QLabel("Live2D预览组件初始化中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: rgba(52, 152, 219, 0.1);
                color: #2c3e50;
                font-size: 12px;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 预览区域 - 使用QLabel显示图像
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("🎭\n\nLive2D动态预览\n\n等待模型加载...")
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 1px dashed #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
                color: #34495e;
                font-size: 14px;
                min-height: 300px;
            }
        """)
        layout.addWidget(self.preview_label)
        
        # 创建动画定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        
        # 动画相关变量
        self.texture_frames = []  # 纹理图像列表
        self.current_frame_index = 0
        self.is_animating = False
        
    def load_model(self, model_path):
        """加载Live2D模型"""
        try:
            self.model_path = model_path
            self.status_label.setText(f"正在加载模型: {os.path.basename(model_path)}")
            
            # 加载纹理图像
            self.texture_frames = []
            
            # 查找纹理文件 - 可能在子文件夹中
            def find_texture_files(root_path):
                textures = []
                for root, dirs, files in os.walk(root_path):
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                            textures.append(os.path.join(root, file))
                return sorted(textures)
            
            self.texture_frames = find_texture_files(model_path)
            
            if self.texture_frames:
                self.status_label.setText(f"找到 {len(self.texture_frames)} 个纹理文件")
                self.display_frame(0)
                self.start_animation()
            else:
                # 如果没有纹理文件，使用模拟
                self.simulate_model_loading()
            
        except Exception as e:
            print(f"加载Live2D模型失败: {e}")
            self.status_label.setText(f"模型加载失败: {str(e)}")
            self.preview_label.setText("❌\n\nLive2D模型加载失败\n\n请检查模型文件")
    
    def simulate_model_loading(self):
        """模拟模型加载过程"""
        try:
            # 模拟加载延迟
            QTimer.singleShot(1000, self.on_model_loaded)
            self.preview_label.setText("⏳\n\nLive2D模型加载中...\n\n请稍等")
            
        except Exception as e:
            print(f"模拟模型加载失败: {e}")
    
    def display_frame(self, frame_index):
        """显示指定帧的图像"""
        try:
            if 0 <= frame_index < len(self.texture_frames):
                image_path = self.texture_frames[frame_index]
                pixmap = QPixmap(image_path)
                
                if not pixmap.isNull():
                    # 应用缩放
                    scaled_pixmap = pixmap.scaled(
                        pixmap.size() * self.zoom_factor,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                    self.preview_label.setText("")  # 清除文本，只显示图像
                else:
                    self.preview_label.setText(f"❌\n\n无法加载图像:\n{os.path.basename(image_path)}")
            else:
                self.preview_label.setText("🎭\n\nLive2D动态预览\n\n无可用帧")
                
        except Exception as e:
            print(f"显示帧失败: {e}")
            self.preview_label.setText(f"❌\n\n显示帧失败:\n{str(e)}")
    
    def on_model_loaded(self):
        """模型加载完成回调"""
        if self.texture_frames:
            self.status_label.setText("Live2D模型加载完成")
            # 图像已在load_model中显示
        else:
            self.status_label.setText("Live2D模型加载完成")
            self.preview_label.setText("🎭\n\nLive2D模型已加载\n\n准备就绪，可以应用表情和播放动作\n\n(这是模拟预览)")
            
            # 启动基础动画
            self.start_animation()
    
    def set_expression(self, expression_name):
        """设置表情"""
        try:
            self.current_expression = expression_name
            self.status_label.setText(f"应用表情: {expression_name}")
            
            # 根据表情名选择帧子集（模拟）
            if self.texture_frames:
                # 简单模拟：根据表情名哈希选择起始帧
                start_index = hash(expression_name) % len(self.texture_frames)
                self.current_frame_index = start_index
                self.display_frame(self.current_frame_index)
            else:
                self.preview_label.setText(f"🎭\n\nLive2D动态预览\n\n当前表情: {expression_name}\n\n表情动画播放中...")
                # 模拟表情动画
                QTimer.singleShot(2000, lambda: self.preview_label.setText(f"🎭\n\nLive2D动态预览\n\n表情: {expression_name}\n\n表情动画完成"))
            
            # 发送表情变化信号
            self.expression_changed.emit(expression_name)
            
        except Exception as e:
            print(f"设置表情失败: {e}")
            self.status_label.setText(f"设置表情失败: {str(e)}")
    
    def play_motion(self, motion_name, loop=False):
        """播放动作"""
        try:
            self.current_motion = motion_name
            motion_info = f"动作: {motion_name}"
            if loop:
                motion_info += " (循环播放)"
            
            self.status_label.setText(f"播放{motion_info}")
            
            if self.texture_frames:
                self.is_animating = True
                if not self.animation_timer.isActive():
                    self.animation_timer.start(150)  # 稍微快一点的动作动画
                self.preview_label.setText("")  # 清除文本，开始显示图像
            else:
                self.preview_label.setText(f"🎬\n\nLive2D动态预览\n\n正在播放动作: {motion_name}\n\n{'循环播放模式' if loop else '单次播放模式'}")
                # 模拟动作播放时间
                duration = 3000 if not loop else -1  # 循环播放不自动停止
                if duration > 0:
                    QTimer.singleShot(duration, self.on_motion_finished)
            
            # 发送动作变化信号
            self.motion_changed.emit(motion_name)
            
        except Exception as e:
            print(f"播放动作失败: {e}")
            self.status_label.setText(f"播放动作失败: {str(e)}")
    
    def on_motion_finished(self):
        """动作播放完成"""
        self.status_label.setText("动作播放完成")
        self.preview_label.setText("🎭\n\nLive2D动态预览\n\n动作播放完成\n\n等待下一个指令")
        self.current_motion = None
    
    def stop_motion(self):
        """停止动作播放"""
        try:
            self.current_motion = None
            self.status_label.setText("动作播放已停止")
            self.preview_label.setText("🎭\n\nLive2D动态预览\n\n动作播放已停止\n\n等待下一个指令")
            
        except Exception as e:
            print(f"停止动作失败: {e}")
    
    def reset_expression(self):
        """重置表情"""
        try:
            self.current_expression = None
            self.status_label.setText("表情已重置")
            self.preview_label.setText("🎭\n\nLive2D动态预览\n\n表情已重置为默认状态\n\n等待下一个指令")
            
        except Exception as e:
            print(f"重置表情失败: {e}")
    
    def reset_pose(self):
        """重置姿态"""
        try:
            self.current_expression = None
            self.current_motion = None
            self.status_label.setText("姿态已重置")
            self.preview_label.setText("🎭\n\nLive2D动态预览\n\n所有姿态已重置\n\n等待下一个指令")
            
        except Exception as e:
            print(f"重置姿态失败: {e}")
    
    def start_animation(self):
        """开始动画"""
        try:
            self.is_animating = True
            if not self.animation_timer.isActive():
                self.animation_timer.start(200)  # 200ms per frame
                self.status_label.setText("Live2D动画已开始")
                
        except Exception as e:
            print(f"开始动画失败: {e}")
    
    def pause_animation(self):
        """暂停动画"""
        try:
            self.is_animating = False
            if self.animation_timer.isActive():
                self.animation_timer.stop()
                self.status_label.setText("Live2D动画已暂停")
                
        except Exception as e:
            print(f"暂停动画失败: {e}")
    
    def update_animation(self):
        """更新动画帧"""
        try:
            if self.is_animating and self.texture_frames:
                self.current_frame_index = (self.current_frame_index + 1) % len(self.texture_frames)
                self.display_frame(self.current_frame_index)
            # 如果没有纹理，使用简单的文本动画
            elif not self.texture_frames:
                # 简单的文本闪烁效果
                current_text = self.preview_label.text()
                if "🎭" in current_text:
                    self.preview_label.setText(current_text.replace("🎭", "😊"))
                elif "😊" in current_text:
                    self.preview_label.setText(current_text.replace("😊", "🎭"))
                    
        except Exception as e:
            print(f"更新动画失败: {e}")
    
    def set_zoom(self, zoom_factor):
        """设置缩放"""
        try:
            self.zoom_factor = zoom_factor
            # 重新显示当前帧以应用缩放
            if self.texture_frames:
                self.display_frame(self.current_frame_index)
            self.status_label.setText(f"缩放设置为: {int(zoom_factor * 100)}%")
            
        except Exception as e:
            print(f"设置缩放失败: {e}")


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()
