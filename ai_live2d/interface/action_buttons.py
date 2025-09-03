"""
动作按钮悬浮窗口 - 支持Ctrl键拖动模式
"""

import sys
import logging
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QApplication, QLabel, QVBoxLayout
from qfluentwidgets import ToolButton, PrimaryToolButton
from qfluentwidgets import FluentIcon as FIF

logger = logging.getLogger("action_buttons")

class ActionButtonsWindow(QWidget):
    # 位置改变信号 (x, y)
    position_changed = pyqtSignal(int, int)

    def __init__(self, config=None, event_bus=None, parent=None):
        """初始化动作按钮悬浮窗口"""
        super().__init__(parent)
        self.main_window = parent  # 保存主窗口引用
        self.config = config.get("action_buttons", {}) if config else {}
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

        logger.info("初始化动作按钮悬浮窗口... [ 完成 ]")

    def init_ui(self):
        """设置UI组件"""
        # 窗口属性
        self.setWindowTitle("动作按钮")
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

        # 按钮容器
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # 打断按钮
        self.interrupt_btn = ToolButton(FIF.CANCEL)
        self.interrupt_btn.setText("打断")
        self.interrupt_btn.setToolTip("打断当前AI输出和语音播放")
        self.interrupt_btn.clicked.connect(self.interrupt_current_operations)
        buttons_layout.addWidget(self.interrupt_btn)

        # 动作一按钮
        self.action_one_btn = ToolButton(FIF.PLAY)
        self.action_one_btn.setText("动作一")
        self.action_one_btn.setToolTip("播放绑定的动作一")
        self.action_one_btn.clicked.connect(lambda: self.trigger_custom_action(1))
        buttons_layout.addWidget(self.action_one_btn)

        # 动作二按钮
        self.action_two_btn = ToolButton(FIF.PLAY)
        self.action_two_btn.setText("动作二")
        self.action_two_btn.setToolTip("播放绑定的动作二")
        self.action_two_btn.clicked.connect(lambda: self.trigger_custom_action(2))
        buttons_layout.addWidget(self.action_two_btn)

        main_layout.addLayout(buttons_layout)

        # 初始大小
        self.resize(
            self.config.get("width", 300),
            self.config.get("height", 80)
        )

        # 初始位置（屏幕右下角，稍微靠上以避免与输入框重叠）
        screen_rect = QApplication.desktop().availableGeometry()
        self.move(
            screen_rect.width() - self.width() - 50,
            screen_rect.height() - self.height() - 150
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
            QWidget {{
                background-color: rgba{bg_color.getRgb()};
                border: 2px solid rgba{border_color.getRgb()};
                border-radius: {self.config.get("border_radius", 10)}px;
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

            # 检查Ctrl键
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
            # 进入拖动模式：隐藏按钮，显示状态标签
            self.interrupt_btn.setVisible(False)
            self.action_one_btn.setVisible(False)
            self.action_two_btn.setVisible(False)
            self.status_label.setVisible(True)
            self.setWindowOpacity(0.7)  # 半透明以便查看后面内容
            logger.debug("进入拖动模式")
        else:
            # 退出拖动模式：显示按钮，隐藏状态标签
            self.interrupt_btn.setVisible(True)
            self.action_one_btn.setVisible(True)
            self.action_two_btn.setVisible(True)
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

    def interrupt_current_operations(self):
        """打断当前AI输出和语音播放"""
        logger.info("用户点击打断按钮")
        if self.main_window and hasattr(self.main_window, 'interrupt_current_operations'):
            self.main_window.interrupt_current_operations()
        elif self.event_bus:
            self.event_bus.publish_sync("interrupt_operations", {})

    def trigger_custom_action(self, action_id):
        """触发自定义动作"""
        logger.info(f"用户点击动作{action_id}按钮")
        if self.main_window and hasattr(self.main_window, 'trigger_custom_action'):
            self.main_window.trigger_custom_action(action_id)
        elif self.event_bus:
            self.event_bus.publish_sync("custom_action", {"action_id": action_id})

    async def cleanup(self):
        """清理资源"""
        self.hide()
        logger.info("清理动作按钮悬浮窗口... [ 完成 ]")
