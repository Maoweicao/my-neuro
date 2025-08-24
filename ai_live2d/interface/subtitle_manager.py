"""
字幕显示管理器
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPoint, QMetaObject, Q_ARG, QObject
from PyQt5.QtGui import QPainter, QFont, QColor, QPainterPath, QPen, QFontMetrics
from PyQt5.QtWidgets import QWidget, QApplication

logger = logging.getLogger("subtitle_manager")

class SubtitleManager(QWidget):
    """字幕管理器"""
    
    # Qt信号，用于线程安全的通信
    text_received = pyqtSignal(str, bool)  # 文本
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None, config=None, event_bus=None):
        """初始化字幕管理器"""
        super().__init__(parent)
        self.config = config or {}
        self.event_bus = event_bus
        
        # 从配置中读取字幕设置
        subtitle_config = self.config.get("subtitle", {})
        
        # 初始状态
        self.stored_text = ""
        self.display_text = "" # 正在处理的文本
        self.is_visible = False
        self.subtitle_hidden_event = asyncio.Event()
        self.subtitle_hidden_event.set()  # 初始设置为字幕隐藏
        self.opacity = 0.0
        self.target_opacity = 0.0

        # 流式显示相关状态
        self.stream_text = ""  # 存储流式文本
        self.user_input = '' # 存储用户输入文本
        self.stream_timer = QTimer(self)  # 流式显示定时器
        self.stream_timer.timeout.connect(self._update_stream_display)
        self.stream_delay = 50  # 每个字符显示延迟(ms)
        
        # 定时器设置
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.update_opacity)

        self.auto_fade_timer = QTimer(self)
        self.auto_fade_timer.timeout.connect(self.start_fade_out)
        
        # 样式配置
        self.fade_duration = subtitle_config.get("fade_duration", 500)
        
        # 字体设置
        self.font_size = subtitle_config.get("font_size", 20)
        font_family = subtitle_config.get("font_family", "Microsoft YaHei")
        font_bold = subtitle_config.get("font_bold", True)
        self._set_font(self.font_size, font_family, font_bold)
        
        # 颜色设置
        self.text_color = QColor(
            subtitle_config.get("text_color_r", 255),
            subtitle_config.get("text_color_g", 255),
            subtitle_config.get("text_color_b", 255),
            subtitle_config.get("text_color_a", 255)
        )
        self.outline_color = QColor(
            subtitle_config.get("outline_color_r", 0),
            subtitle_config.get("outline_color_g", 0),
            subtitle_config.get("outline_color_b", 0),
            subtitle_config.get("outline_color_a", 200)
        )
        self.bg_color = QColor(
            subtitle_config.get("bg_color_r", 0),
            subtitle_config.get("bg_color_g", 0),
            subtitle_config.get("bg_color_b", 0),
            subtitle_config.get("bg_color_a", 100)
        )
        
        self.padding = subtitle_config.get("padding", 15)
        self.border_radius = subtitle_config.get("border_radius", 10)
        
        # 字幕框大小设置
        self.max_width = subtitle_config.get("box_width", 800)
        self.max_height = subtitle_config.get("box_height", 600)
        
        # 设置窗口属性
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        
        # 连接信号
        self.text_received.connect(self._handle_text_received)
        self.clear_requested.connect(self._handle_clear_requested)
        
        # 重要：独立显示
        if parent:
            self.setParent(None)
        
        # 初始隐藏
        self.hide()
        
        logger.info("初始化字幕管理器... [ 完成 ]")
    
    def add_text(self, text: str, stream: bool=False, user_input: str=''):
        """异步设置文本 - 线程安全的接口
        
        Args:
            text: 要显示的文本
            stream: 是否流式显示(逐字显示)
            user_input: 用户输入
        """
        if user_input:
            self.user_input = user_input
        self.text_received.emit(text, stream)
    
    def clear_text(self):
        """异步清空文本 - 线程安全的接口"""
        self.clear_requested.emit()

    def _handle_text_received(self, text: str, stream: bool):
        """处理接收到的文本（在主线程中执行）"""
        logger.debug(f"接收字幕文本: {text[:30]}... stream={stream}")
        
        if not text:
            self.start_fade_out()
            return
        
        if stream:
            # 流式显示处理
            self.stream_text += text
            
            # 如果当前没有在显示，开始显示
            if not self.is_visible:
                self.start_fade_in()
            # 启动流式显示定时器
            self.stream_timer.start(self.stream_delay)
        else:
            # 完整文本显示
            self.stream_timer.stop()  # 停止任何正在进行的流式显示
            self.display_text = self._text_assembler(text)
            self._update_size_and_position()
            
            # 确保窗口可见
            if not self.is_visible:
                self.start_fade_in()
            
            # 更新显示
            self.update()

    def _update_stream_display(self):
        """更新流式文本显示"""
        if self.stream_text:
            # 去除用户输入
            if self.user_input:
                self.display_text = ''
                self.user_input = ''
                return

            # 添加下一个字符
            self.display_text += self.stream_text[0]
            self.stream_text = self.stream_text[1:]
            
            # 组装文本（处理换行）
            self.display_text = self._text_assembler(self.display_text)
            
            # 更新窗口大小和位置
            self._update_size_and_position()
            
            # 重绘窗口
            self.update()
        else:
            # 文本显示完成，停止定时器
            self.stream_timer.stop()
    
    def _handle_clear_requested(self):
        """处理清空请求（在主线程中执行）"""
        self.auto_fade_timer.start(1500)
    
    def _update_size_and_position(self):
        """根据文本内容更新窗口大小和位置"""
        if not self.display_text:
            return
        
        # 计算文本尺寸
        text_lines = self.display_text.split('\n')
        text_width = max([self.font_metrics.horizontalAdvance(line) for line in text_lines]) + self.padding * 2

        text_height = self.font_metrics.height() * len(text_lines) + self.padding * 2
        
        # 处理尺寸限制
        while text_height >= self.max_height and self.font_size >= 10:
            self.font_size -= 1
            self._set_font(self.font_size)
            self.display_text = self._text_assembler(self.display_text)
            text_lines = self.display_text.split('\n')
            text_height = self.font_metrics.height() * len(text_lines) + self.padding * 2
        
        # 限制最小/最大尺寸
        text_width = max(100, min(text_width, self.max_width))
        text_height = max(50, min(text_height, self.max_height))
        
        # 更新窗口大小
        self.resize(int(text_width), int(text_height))
        
        # 居中显示在屏幕底部
        screen_rect = QApplication.desktop().screenGeometry()
        x = (screen_rect.width() - self.width()) // 2
        y = screen_rect.height() - self.height() - 100
        self.move(x, y)
    
    def _text_assembler(self, text: str) -> str:
        """将文本按宽度分行"""
        if not text:
            return ""
        
        processed_text = ""
        current_line = ""
        
        for char in text:
            if char == '\n':
                processed_text += current_line + '\n'
                current_line = ""
                continue
            
            text_line = current_line + char
            line_width = self.font_metrics.horizontalAdvance(text_line)
            
            if line_width + self.padding * 2 >= self.max_width and current_line:
                processed_text += current_line + '\n'
                current_line = char
            else:
                current_line = text_line
        
        if current_line:
            processed_text += current_line
        
        return processed_text
    
    def _set_font(self, font_size, font_family="Microsoft YaHei", font_bold=True):
        """设置字体"""
        self.font = QFont(font_family, font_size)
        self.font.setBold(font_bold)
        self.font_metrics = QFontMetrics(self.font)
    
    def start_fade_in(self):
        """开始淡入动画"""
        self.is_visible = True
        self.subtitle_hidden_event.clear()
        self.target_opacity = 1.0
        self.show()
        self.fade_timer.start(16)  # 约60fps
        logger.debug("字幕淡入")
    
    def start_fade_out(self):
        """开始淡出动画"""
        self.target_opacity = 0.0
        self.fade_timer.start(16)
        self.auto_fade_timer.stop()
        self.display_text = ""  # 清空显示文本
        self.stream_text = ""  # 清空流式文本
        logger.debug("字幕淡出")
    
    def update_opacity(self):
        """更新不透明度"""
        if abs(self.opacity - self.target_opacity) < 0.01:
            self.opacity = self.target_opacity
            self.fade_timer.stop()
            
            if self.opacity == 0.0:
                self.hide()
                self.is_visible = False
                self.subtitle_hidden_event.set()
                self.font_size = self.config.get("subtitle", {}).get("font_size", 20)
                self._set_font(self.font_size)
            
            self.update()
            return
        
        # 渐变调整
        fade_step = 0.05
        if self.opacity < self.target_opacity:
            self.opacity = min(self.opacity + fade_step, self.target_opacity)
        else:
            self.opacity = max(self.opacity - fade_step, self.target_opacity)
        
        self.setWindowOpacity(self.opacity)
        self.update()
    
    def paintEvent(self, event):
        """绘制字幕"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 
                           self.border_radius, self.border_radius)
        
        bg_color = QColor(self.bg_color)
        bg_color.setAlpha(int(bg_color.alpha() * self.opacity))
        painter.fillPath(path, bg_color)
        
        # 设置字体
        painter.setFont(self.font)
        
        # 准备文本
        if not self.display_text:
            return
        
        # 文本区域
        text_rect = QRectF(self.padding, self.padding, 
                          self.width() - 2 * self.padding, 
                          self.height() - 2 * self.padding)
        
        # 绘制文本描边
        outline_color = QColor(self.outline_color)
        outline_color.setAlpha(int(outline_color.alpha() * self.opacity))
        painter.setPen(QPen(outline_color, 2))
        
        # 4个方向的描边
        offsets = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dx, dy in offsets:
            painter.drawText(text_rect.translated(dx, dy), Qt.AlignCenter, self.display_text)
        
        # 绘制主文本
        text_color = QColor(self.text_color)
        text_color.setAlpha(int(text_color.alpha() * self.opacity))
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignCenter, self.display_text)
    
    async def cleanup(self):
        """清理资源"""
        # 停止所有定时器
        self.fade_timer.stop()
        self.auto_fade_timer.stop()
        self.stream_timer.stop()
        
        # 隐藏窗口
        self.hide()
        
        logger.info("清理字幕管理器... [ 完成 ]")