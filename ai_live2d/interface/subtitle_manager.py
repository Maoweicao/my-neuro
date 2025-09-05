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
        self.outline_size = subtitle_config.get("outline_size", 2)
        
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
        
        # 设置窗口位置（支持多显示器）
        self._set_window_position()
    
    def _set_window_position(self):
        """设置窗口位置，支持多显示器选择和精确坐标定位"""
        try:
            from PyQt5.QtWidgets import QDesktopWidget
            
            # 获取字幕配置
            subtitle_config = self.config.get("subtitle", {})
            
            # 获取显示器配置
            monitor_index = subtitle_config.get("display_monitor", 0)
            position_mode = subtitle_config.get("display_position", "bottom")
            
            # 获取精确坐标（新功能：直接使用X,Y坐标）
            direct_x = subtitle_config.get("position_x", None)
            direct_y = subtitle_config.get("position_y", None)
            
            # 获取偏移量
            offset_x = subtitle_config.get("display_offset_x", 0)
            offset_y = subtitle_config.get("display_offset_y", 0)
            
            # 获取桌面和屏幕信息
            desktop = QDesktopWidget()
            screen_count = desktop.screenCount()
            
            # 确保显示器索引有效
            if monitor_index >= screen_count:
                logger.warning(f"指定的显示器 {monitor_index} 不存在，使用主显示器")
                monitor_index = desktop.primaryScreen()
            
            # 获取目标显示器的几何信息
            screen_geometry = desktop.screenGeometry(monitor_index)
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            screen_x = screen_geometry.x()
            screen_y = screen_geometry.y()
            
            # 获取窗口尺寸
            window_width = self.width()
            window_height = self.height()
            
            # 如果设置了直接坐标，优先使用直接坐标
            if direct_x is not None and direct_y is not None:
                # 直接坐标模式：相对于目标显示器的坐标
                x = screen_x + direct_x
                y = screen_y + direct_y
                logger.debug(f"使用直接坐标模式: 显示器{monitor_index}, 坐标({direct_x}, {direct_y})")
            else:
                # 预设位置模式：根据位置名称计算坐标
                x, y = self._calculate_preset_position(
                    position_mode, screen_x, screen_y, screen_width, screen_height, 
                    window_width, window_height
                )
                logger.debug(f"使用预设位置模式: 显示器{monitor_index}, 位置{position_mode}")
            
            # 应用偏移量
            x += offset_x
            y += offset_y
            
            # 确保窗口在屏幕范围内
            x = max(screen_x, min(x, screen_x + screen_width - window_width))
            y = max(screen_y, min(y, screen_y + screen_height - window_height))
            
            # 设置窗口位置
            self.move(x, y)
            
            logger.info(f"字幕窗口位置: 显示器{monitor_index} ({screen_width}x{screen_height}), 最终坐标({x}, {y})")
            
        except Exception as e:
            logger.error(f"设置窗口位置失败: {e}")
            # 回退到默认位置设置
            try:
                screen_rect = QApplication.desktop().screenGeometry()
                x = (screen_rect.width() - self.width()) // 2
                y = screen_rect.height() - self.height() - 100
                self.move(x, y)
                logger.info(f"回退到默认位置: ({x}, {y})")
            except Exception as fallback_e:
                logger.error(f"设置默认位置也失败: {fallback_e}")
    
    def _calculate_preset_position(self, position_mode, screen_x, screen_y, screen_width, screen_height, window_width, window_height):
        """根据预设位置模式计算坐标"""
        # 计算安全边距
        margin = 50
        
        if position_mode == "center":
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + (screen_height - window_height) // 2
        elif position_mode == "top":
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + margin
        elif position_mode == "bottom":
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + screen_height - window_height - margin
        elif position_mode == "left":
            x = screen_x + margin
            y = screen_y + (screen_height - window_height) // 2
        elif position_mode == "right":
            x = screen_x + screen_width - window_width - margin
            y = screen_y + (screen_height - window_height) // 2
        elif position_mode == "top_left":
            x = screen_x + margin
            y = screen_y + margin
        elif position_mode == "top_right":
            x = screen_x + screen_width - window_width - margin
            y = screen_y + margin
        elif position_mode == "bottom_left":
            x = screen_x + margin
            y = screen_y + screen_height - window_height - margin
        elif position_mode == "bottom_right":
            x = screen_x + screen_width - window_width - margin
            y = screen_y + screen_height - window_height - margin
        elif position_mode == "top_left_center":
            x = screen_x + screen_width // 4 - window_width // 2
            y = screen_y + margin
        elif position_mode == "top_right_center":
            x = screen_x + screen_width * 3 // 4 - window_width // 2
            y = screen_y + margin
        elif position_mode == "bottom_left_center":
            x = screen_x + screen_width // 4 - window_width // 2
            y = screen_y + screen_height - window_height - margin
        elif position_mode == "bottom_right_center":
            x = screen_x + screen_width * 3 // 4 - window_width // 2
            y = screen_y + screen_height - window_height - margin
        elif position_mode == "left_center":
            x = screen_x + margin
            y = screen_y + (screen_height - window_height) // 2
        elif position_mode == "right_center":
            x = screen_x + screen_width - window_width - margin
            y = screen_y + (screen_height - window_height) // 2
        elif position_mode == "top_center":
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + margin
        elif position_mode == "bottom_center":
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + screen_height - window_height - margin
        else:
            # 默认：底部居中
            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + screen_height - window_height - margin
        
        return x, y
    
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
            elif self.opacity == 1.0:
                self.subtitle_hidden_event.clear()
        else:
            step = 0.05 if self.opacity < self.target_opacity else -0.05
            self.opacity += step
            
        self.update()

    def paintEvent(self, event):
        """绘制字幕"""
        if not self.display_text or self.opacity <= 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置不透明度
        painter.setOpacity(self.opacity)
        
        # 绘制背景
        if hasattr(self, 'bg_color') and self.bg_color:
            bg_color = QColor(self.bg_color)
            painter.setBrush(bg_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 5, 5)
        
        # 设置字体
        painter.setFont(self.font)
        
        # 绘制文本轮廓
        if hasattr(self, 'outline_color') and hasattr(self, 'outline_size'):
            outline_color = QColor(self.outline_color)
            painter.setPen(QPen(outline_color, self.outline_size))
            
            # 绘制轮廓（在四个方向添加偏移）
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    text_rect = self.rect().adjusted(dx, dy, dx, dy)
                    painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.display_text)
        
        # 绘制主文本
        text_color = QColor(self.text_color) if hasattr(self, 'text_color') else QColor(255, 255, 255)
        painter.setPen(text_color)
        painter.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self.display_text)
    
    def update_display_settings(self, monitor_index=None, position=None, position_x=None, position_y=None, offset_x=None, offset_y=None):
        """更新显示设置并重新定位窗口
        
        Args:
            monitor_index: 目标显示器索引
            position: 显示位置 (center, top, bottom, top_left, top_right, bottom_left, bottom_right)
            position_x: X坐标
            position_y: Y坐标
            offset_x: X轴偏移量
            offset_y: Y轴偏移量
        """
        try:
            # 更新配置
            subtitle_config = self.config.setdefault("subtitle", {})
            
            if monitor_index is not None:
                subtitle_config["display_monitor"] = monitor_index
                logger.info(f"字幕显示器已更改为: {monitor_index}")
            
            if position is not None:
                subtitle_config["display_position"] = position
                logger.info(f"字幕显示位置已更改为: {position}")
                
            if position_x is not None:
                subtitle_config["position_x"] = position_x
                logger.info(f"字幕X坐标已更改为: {position_x}")
                
            if position_y is not None:
                subtitle_config["position_y"] = position_y
                logger.info(f"字幕Y坐标已更改为: {position_y}")
            
            if offset_x is not None:
                subtitle_config["display_offset_x"] = offset_x
                logger.info(f"字幕X偏移已更改为: {offset_x}")
            
            if offset_y is not None:
                subtitle_config["display_offset_y"] = offset_y
                logger.info(f"字幕Y偏移已更改为: {offset_y}")
            
            # 如果字幕正在显示，重新定位窗口
            if self.is_visible and self.display_text:
                self._set_window_position()
                logger.debug("字幕窗口位置已更新")
                
        except Exception as e:
            logger.error(f"更新显示设置失败: {e}")
    
    def get_monitor_info(self):
        """获取所有显示器信息
        
        Returns:
            list: 显示器信息列表，每个元素包含 {index, name, width, height, x, y, is_primary}
        """
        try:
            from PyQt5.QtWidgets import QDesktopWidget
            from PyQt5.QtGui import QGuiApplication
            
            monitors = []
            desktop = QDesktopWidget()
            screen_count = desktop.screenCount()
            
            # 尝试获取详细的屏幕信息
            app = QGuiApplication.instance()
            if app:
                screens = app.screens()
                
                for i, screen in enumerate(screens):
                    geometry = screen.geometry()
                    screen_name = screen.name() if hasattr(screen, 'name') else f"显示器 {i+1}"
                    is_primary = screen == app.primaryScreen()
                    
                    monitor_info = {
                        'index': i,
                        'name': screen_name,
                        'width': geometry.width(),
                        'height': geometry.height(),
                        'x': geometry.x(),
                        'y': geometry.y(),
                        'is_primary': is_primary
                    }
                    monitors.append(monitor_info)
            else:
                # 回退到基础方法
                for i in range(screen_count):
                    geometry = desktop.screenGeometry(i)
                    is_primary = i == desktop.primaryScreen()
                    
                    monitor_info = {
                        'index': i,
                        'name': f"显示器 {i+1}",
                        'width': geometry.width(),
                        'height': geometry.height(),
                        'x': geometry.x(),
                        'y': geometry.y(),
                        'is_primary': is_primary
                    }
                    monitors.append(monitor_info)
            
            logger.debug(f"检测到 {len(monitors)} 个显示器")
            return monitors
            
        except Exception as e:
            logger.error(f"获取显示器信息失败: {e}")
            return [{'index': 0, 'name': '主显示器', 'width': 1920, 'height': 1080, 'x': 0, 'y': 0, 'is_primary': True}]