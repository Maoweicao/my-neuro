"""
用户输入窗口 - 支持Alt隐藏和Ctrl键拖动模式
"""

import sys
import logging
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout, QApplication, QLabel

logger = logging.getLogger("user_input")

class UserInputWindow(QWidget):
    # 位置改变信号 (x, y)
    position_changed = pyqtSignal(int, int)
    
    def __init__(self, config=None, event_bus=None, parent=None):
        """初始化用户输入窗口"""
        super().__init__(parent)
        self.config = config.get("user_input", {}) if config else {}
        self.event_bus = event_bus
        self.drag_position = QPoint()
        self.drag_mode = False  # 拖动模式标志
        self.click_through = False  # 鼠标穿透状态标志
        self.normal_opacity = 1.0   # 正常状态不透明度
        self.ghost_opacity = 0.1    # 穿透状态不透明度
        
        # 初始化UI
        self.init_ui()
        # 应用样式
        self.apply_styles()
        # 注册快捷键
        self.register_shortcuts()
        
        logger.info("初始化用户输入窗口... [ 完成 ]")
    
    def init_ui(self):
        """设置UI组件"""
        # 窗口属性
        self.setWindowTitle("输入框")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 状态标签 (仅在拖动模式下显示)
        self.status_label = QLabel("拖动模式 (按 Ctrl 键结束)")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        main_layout.addWidget(self.status_label)
        
        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("输入消息后按回车发送...")
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self.send_message)
        main_layout.addWidget(self.input_field)
        
        # 初始大小
        self.resize(
            self.config.get("width", 500),
            self.config.get("height", 100)
        )
        
        # 初始位置（屏幕右下角）
        screen_rect = QApplication.desktop().availableGeometry()
        self.move(
            screen_rect.width() - self.width() - 50,
            screen_rect.height() - self.height() - 50
        )
    
    def apply_styles(self):
        """应用样式配置"""
        # 获取配置值，提供默认值
        bg_color = QColor(
            self.config.get("bg_color_r", 30),
            self.config.get("bg_color_g", 31),
            self.config.get("bg_color_b", 34),
            self.config.get("bg_color_a", 220)
        )
        
        text_color = QColor(
            self.config.get("text_color_r", 220),
            self.config.get("text_color_g", 220),
            self.config.get("text_color_b", 220)
        )
        
        border_color = QColor(
            self.config.get("border_color_r", 86),
            self.config.get("border_color_g", 182),
            self.config.get("border_color_b", 194)
        )
        
        status_bg_color = QColor(
            self.config.get("status_bg_color_r", 60),
            self.config.get("status_bg_color_g", 60),
            self.config.get("status_bg_color_b", 70),
            self.config.get("status_bg_color_a", 220)
        )
        
        # 应用样式表
        style_sheet = f"""
            #inputField {{
                background-color: rgba{bg_color.getRgb()};
                color: rgba{text_color.getRgb()};
                border: 2px solid rgba{border_color.getRgb()};
                border-radius: {self.config.get("border_radius", 10)}px;
                padding: 12px;
                font-size: {self.config.get("font_size", 16)}px;
                font-family: {self.config.get("font_family", "Segoe UI")};
            }}
            
            #statusLabel {{
                background-color: rgba{status_bg_color.getRgb()};
                color: rgba{text_color.getRgb()};
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                font-family: {self.config.get("font_family", "Segoe UI")};
            }}
        """
        
        self.setStyleSheet(style_sheet)
    
    def register_shortcuts(self):
        """注册快捷键"""
        # 安装事件过滤器
        QApplication.instance().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器处理快捷键"""
        if event.type() == QEvent.KeyPress:
            # 检查Alt键
            if event.key() == Qt.Key_Alt:
                self.toggle_click_through()
                return True  # 事件已处理
            
            # 检查M键
            elif event.key() == Qt.Key_Control and not self.click_through:
                self.toggle_drag_mode()
                return True  # 事件已处理
        
        return super().eventFilter(obj, event)
    
    def toggle_click_through(self):
        """切换鼠标穿透状态"""
        self.click_through = not self.click_through
        
        if self.click_through:
            # 进入穿透模式：降低透明度
            self.setWindowOpacity(self.ghost_opacity)
            logger.debug("进入穿透模式")
        else:
            # 退出穿透模式：恢复正常透明度
            self.setWindowOpacity(self.normal_opacity)
            logger.debug("退出穿透模式")
            
        # 强制重绘窗口
        self.repaint()
    
    def toggle_drag_mode(self):
        """切换拖动模式"""
        if self.click_through:
            return  # 窗口隐藏时不处理拖动模式
        
        self.drag_mode = not self.drag_mode
        
        if self.drag_mode:
            # 进入拖动模式：隐藏输入框，显示状态标签
            self.input_field.setVisible(False)
            self.status_label.setVisible(True)
            self.setWindowOpacity(0.7)  # 半透明以便查看后面内容
            logger.debug("进入拖动模式")
        else:
            # 退出拖动模式：显示输入框，隐藏状态标签
            self.input_field.setVisible(True)
            self.status_label.setVisible(False)
            self.setWindowOpacity(self.normal_opacity)
            logger.debug("退出拖动模式")
    
    def mousePressEvent(self, event):
        """鼠标按下事件（用于拖动）"""
        if event.button() == Qt.LeftButton and self.drag_mode:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件（用于拖动）"""
        if event.buttons() == Qt.LeftButton and self.drag_mode and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            self.position_changed.emit(self.x(), self.y())
            event.accept()
    
    def send_message(self):
        """发送消息到事件总线"""
        text = self.input_field.text().strip()
        if text:
            logger.info(f"发送用户输入: {text}")
            
            # 发布事件
            if self.event_bus:
                # 使用事件总线的同步发布方法
                self.event_bus.publish_sync("user_text_input", {"text": text})
            
            # 清空输入框
            self.input_field.clear()
    
    async def cleanup(self):
        """清理资源"""
        self.hide()
        logger.info("清理用户输入窗口... [ 完成 ]")