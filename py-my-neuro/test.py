import json
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic
import subprocess
import time
import os
import glob
import shutil
import re
import socket


# 在这里添加新函数（来自 live-2d/test.py 的新增能力）
def get_base_path():
    """获取程序基础路径，兼容开发环境和打包后的exe。
    - 打包后返回 exe 所在目录的上级目录
    - 开发环境返回当前文件所在目录的上级目录
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.dirname(exe_dir)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_app_path():
    """获取程序运行的主目录，无论是开发环境还是打包后的exe"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


class LogReader(QThread):
    """读取日志文件的线程，自动等待文件生成并兼容多种编码。"""
    log_signal = pyqtSignal(str)

    def __init__(self, log_file_path: str, poll_interval: float = 0.2):
        super().__init__()
        self.log_file_path = log_file_path
        self.running = True
        self.poll_interval = poll_interval

    def run(self):
        # 等待文件出现或被停止
        while not os.path.exists(self.log_file_path) and self.running:
            self.msleep(int(self.poll_interval * 1000))

        if not self.running:
            return

        encodings = ['utf-8', 'gbk', 'ansi', 'latin-1']
        file_handle = None

        # 尝试不同编码打开
        for encoding in encodings:
            try:
                file_handle = open(self.log_file_path, 'r', encoding=encoding, errors='replace')
                break
            except Exception:
                continue

        if not file_handle:
            # 最后退回到二进制读取
            try:
                file_handle = open(self.log_file_path, 'rb')
            except Exception as e:
                self.log_signal.emit(f"无法打开日志文件: {e}")
                return

        try:
            # 定位到末尾，开始追尾
            if 'b' not in getattr(file_handle, 'mode', ''):
                file_handle.seek(0, os.SEEK_END)
                while self.running:
                    line = file_handle.readline()
                    if line:
                        self.log_signal.emit(line.rstrip('\n'))
                    else:
                        self.msleep(int(self.poll_interval * 1000))
            else:
                # 二进制模式：按行读取并尽量解码
                file_handle.seek(0, os.SEEK_END)
                while self.running:
                    line = file_handle.readline()
                    if line:
                        text = None
                        for enc in encodings:
                            try:
                                text = line.decode(enc)
                                break
                            except Exception:
                                continue
                        if text is None:
                            text = line.decode('latin-1', errors='replace')
                        self.log_signal.emit(text.rstrip('\n'))
                    else:
                        self.msleep(int(self.poll_interval * 1000))
        except Exception:
            # 避免线程崩溃，静默退出
            pass
        finally:
            try:
                file_handle.close()
            except Exception:
                pass

    def stop(self):
        self.running = False


class ProcessReader(QThread):
    """读取子进程标准输出/错误的线程，按行发射到UI。"""
    line_signal = pyqtSignal(str)

    def __init__(self, process: subprocess.Popen, poll_interval: float = 0.05):
        super().__init__()
        self.process = process
        self.poll_interval = poll_interval
        self.running = True

    def run(self):
        try:
            encodings = ['utf-8', 'gbk', 'ansi', 'latin-1']
            stdout = self.process.stdout
            if stdout is None:
                return
            while self.running:
                line = stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    self.msleep(int(self.poll_interval * 1000))
                    continue
                text = None
                if isinstance(line, bytes):
                    for enc in encodings:
                        try:
                            text = line.decode(enc)
                            break
                        except Exception:
                            continue
                    if text is None:
                        text = line.decode('latin-1', errors='replace')
                else:
                    text = str(line)
                self.line_signal.emit(text.rstrip('\r\n'))
        except Exception:
            pass

    def stop(self):
        self.running = False


class ToastNotification(QLabel):
    """自定义Toast提示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 240), 
                    stop:1 rgba(248, 248, 248, 240));
                color: rgb(60, 60, 60);
                border: 1px solid rgba(200, 200, 200, 150);
                border-radius: 15px;
                padding: 18px 36px;
                font-size: 16px;
                font-family: "Microsoft YaHei";
                font-weight: normal;
            }
        """)
        self.hide()

        # 创建动画效果
        self.effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.effect)

        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.opacity_animation = QPropertyAnimation(self.effect, b"opacity")
        self.opacity_animation.setDuration(300)

    def show_message(self, message, duration=2000):
        """显示消息，duration为显示时长（毫秒）"""
        self.setText(message)
        self.adjustSize()

        # 计算位置
        parent = self.parent()
        if parent:
            x = (parent.width() - self.width()) // 2
            start_y = -self.height()  # 从顶部外面开始
            end_y = 20  # 最终位置距离顶部20像素

            # 设置起始位置
            self.move(x, start_y)
            self.show()
            self.raise_()

            # 滑入动画
            self.slide_animation.setStartValue(QPoint(x, start_y))
            self.slide_animation.setEndValue(QPoint(x, end_y))

            # 透明度渐入
            self.opacity_animation.setStartValue(0.0)
            self.opacity_animation.setEndValue(1.0)

            # 开始动画
            self.slide_animation.start()
            self.opacity_animation.start()

            # 延迟后滑出
            QTimer.singleShot(duration, self.hide_with_animation)

    def hide_with_animation(self):
        """带动画的隐藏"""
        parent = self.parent()
        if parent:
            current_pos = self.pos()
            end_y = -self.height()

            # 滑出动画
            self.slide_animation.setStartValue(current_pos)
            self.slide_animation.setEndValue(QPoint(current_pos.x(), end_y))

            # 透明度渐出
            self.opacity_animation.setStartValue(1.0)
            self.opacity_animation.setEndValue(0.0)

            # 动画完成后隐藏
            self.slide_animation.finished.connect(self.hide)

            # 开始动画
            self.slide_animation.start()
            self.opacity_animation.start()


class CustomTitleBar(QWidget):
    """自定义标题栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(55)
        self.setStyleSheet("""
           CustomTitleBar {
               background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(235, 233, 225, 255), stop:1 rgba(230, 228, 220, 255)) !important;
               border: none;
               border-radius: 25px 25px 0px 0px;
           }
       """)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 5, 0)
        layout.setSpacing(0)

        # 标题
        self.title_label = QLabel("肥牛py版5.0")
        self.title_label.setStyleSheet("""
           QLabel {
               color: rgb(114, 95, 77) !important;
               font-size: 14px !important;
               font-family: "Microsoft YaHei" !important;
               font-weight: bold !important;
               background-color: transparent !important;
           }
       """)

        layout.addWidget(self.title_label)
        layout.addStretch()

        # 窗口控制按钮
        button_style = """
           QPushButton {
               background-color: transparent !important;
               border: none !important;
               width: 45px;
               height: 40px;
               font-size: 14px !important;
               font-weight: bold !important;
               color: rgb(114, 95, 77) !important;
           }
           QPushButton:hover {
               background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(200, 195, 185, 255), stop:1 rgba(180, 175, 165, 255)) !important;
               color: rgb(40, 35, 25) !important;
               border-radius: 5px !important;
           }
       """

        close_style = """
           QPushButton {
               background-color: transparent !important;
               border: none !important;
               width: 45px;
               height: 40px;
               font-size: 14px !important;
               font-weight: bold !important;
               color: rgb(114, 95, 77) !important;
           }
           QPushButton:hover {
               background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 182, 193, 255), stop:1 rgba(255, 160, 122, 255)) !important;
               color: rgb(139, 69, 19) !important;
               border-radius: 5px !important;
           }
       """

        # 最小化按钮
        self.min_btn = QPushButton("−")
        self.min_btn.setStyleSheet(button_style)
        self.min_btn.clicked.connect(self.parent.showMinimized)

        # 最大化/还原按钮
        self.max_btn = QPushButton("□")
        self.max_btn.setStyleSheet(button_style)
        self.max_btn.clicked.connect(self.toggle_maximize)

        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setStyleSheet(close_style)
        self.close_btn.clicked.connect(self.parent.close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    def toggle_maximize(self):
        """切换最大化状态"""
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.max_btn.setText("◱")

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖拽窗口"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.parent.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """双击标题栏最大化/还原"""
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()


class set_pyqt(QWidget):
    # 添加信号用于线程安全的日志更新
    log_signal = pyqtSignal(str)
    mcp_log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.live2d_process = None
        self.mcp_process = None
        # 新增：后台终端与服务进程
        self.terminal_process = None  # TTS服务
        self.asr_process = None
        self.bert_process = None
        self.rag_process = None
        # 新增：声音克隆状态
        self.voice_clone_process = None
        self.selected_model_path = None
        self.selected_audio_path = None
        self.config_path = 'config_mod\config.json'
        self.config = self.load_config()

        # 新增：日志读取器与日志路径
        self.log_readers = {}
        self.proc_readers = {}
        self.log_file_paths = {
            'asr': os.path.join('..', 'logs', 'asr.log'),
            'tts': os.path.join('..', 'logs', 'tts.log'),
            'bert': os.path.join('..', 'logs', 'bert.log'),
            'rag': os.path.join('..', 'logs', 'rag.log'),
        }

        # 调整大小相关变量
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.edge_margin = 10

        self.init_ui()

    def init_ui(self):
        # 设置无边框
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 重新启用透明背景（这样CSS圆角才能生效）
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 启用鼠标跟踪
        self.setMouseTracking(True)

        # 为整个应用安装事件过滤器
        app = QApplication.instance()
        app.installEventFilter(self)

        # 加载主窗口框架
        self.ui = uic.loadUi('main.ui')

        # 隐藏状态栏
        if hasattr(self.ui, 'statusbar'):
            self.ui.statusbar.hide()

        # 创建一个容器来装标题栏和原UI
        container = QWidget()
        # 给容器设置背景色和圆角
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(250, 249, 245, 255),
                    stop:0.5 rgba(245, 243, 235, 255),
                    stop:1 rgba(240, 238, 230, 255));
                border-radius: 25px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 添加自定义标题栏
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)

        # 在嵌入前放宽 main.ui 的尺寸限制，避免 .ui 文件中的固定大小影响自适应
        self.relax_size_constraints(self.ui)

        # 添加原始UI
        container_layout.addWidget(self.ui)

        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        # 加载样式文件
        self.load_styles()

        # 加载页面内容
        self.load_pages()

        # 设置窗口初始大小：按可用屏幕的比例显示（例如 82%），并居中
        try:
            screen_geo = QGuiApplication.primaryScreen().availableGeometry()
            target_w = int(screen_geo.width() * 0.82)
            target_h = int(screen_geo.height() * 0.82)
            target_size = QSize(target_w, target_h)
            # 居中到可用区域
            aligned_rect = QStyle.alignedRect(Qt.LeftToRight, Qt.AlignCenter, target_size, screen_geo)
            self.setGeometry(aligned_rect)
        except Exception:
            # 回退：如果获取屏幕信息失败，则使用一个合理默认值
            self.resize(1280, 800)

        # 设置最小尺寸为1x1，允许任意缩小
        self.setMinimumSize(1, 1)

        # 调整侧边栏占比：将 sidebar 宽度设为总宽度的 0.33，并让内容区获得更多空间
        self.adjust_sidebar_ratio(0.33)

        # 保持原来的功能
        self.set_btu()
        self.set_config()

        # 创建Toast提示
        self.toast = ToastNotification(self)

        # 连接日志信号
        self.log_signal.connect(self.update_log)
        self.mcp_log_signal.connect(self.update_mcp_log)

        # 设置动画控制按钮
        self.setup_motion_buttons()
        # 初始化 Live2D 模型列表（若UI存在）
        self.init_live2d_models()
        # 启动时检查服务状态（若UI存在）
        self.check_all_service_status()
        # 绑定拖拽上传目标
        self.setup_drag_drop_targets()


    def relax_size_constraints(self, root_widget: QWidget):
        """放宽从 .ui 加载的控件的尺寸限制，忽略固定大小设置并启用可伸缩策略。
        - 清除 fixedSize：重置 min/max
        - 布局改为无限制（NoConstraint）
        - 尺寸策略改为 Expanding（尽量填充容器）
        """
        try:
            # 自身
            root_widget.setMinimumSize(0, 0)
            root_widget.setMaximumSize(16777215, 16777215)
            if hasattr(root_widget, 'setSizePolicy'):
                root_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # 根布局
            layout = root_widget.layout()
            if layout:
                layout.setSizeConstraint(QLayout.SetNoConstraint)

            # 所有子部件与子布局
            for child in root_widget.findChildren(QWidget):
                try:
                    # 保留 sidebar 的原始尺寸约束，避免被放宽后过度变宽
                    if getattr(child, 'objectName', lambda: '')() == 'sidebar':
                        continue

                    child.setMinimumSize(0, 0)
                    child.setMaximumSize(16777215, 16777215)
                    if hasattr(child, 'setSizePolicy'):
                        # 对按钮/输入框等使用 Preferred 垂直策略，避免过度拉伸
                        vertical_policy = QSizePolicy.Preferred
                        if isinstance(child, (QFrame, QStackedWidget, QScrollArea, QGroupBox, QTabWidget)):
                            vertical_policy = QSizePolicy.Expanding
                        child.setSizePolicy(QSizePolicy.Expanding, vertical_policy)
                except Exception:
                    pass

            for lay in root_widget.findChildren(QLayout):
                try:
                    lay.setSizeConstraint(QLayout.SetNoConstraint)
                except Exception:
                    pass
        except Exception:
            # 放宽失败时静默忽略，不影响主流程
            pass

    def adjust_sidebar_ratio(self, ratio: float = 0.33):
        """按比例设置侧边栏宽度，并为布局设置伸缩比。
        - ratio: 侧边栏占总宽度比例，例如 0.33
        - 为水平布局设置 sidebar:content = 0:1，使内容区优先生长。
        """
        try:
            sidebar = getattr(self.ui, 'sidebar', None)
            # 估算总宽度（优先使用 centralwidget 宽度，其次窗口宽度，最后屏幕可用宽度 * 0.82）
            central = getattr(self.ui, 'centralwidget', None)
            total_w = 0
            if central is not None and central.width() > 0:
                total_w = central.width()
            elif self.width() > 0:
                total_w = self.width()
            else:
                try:
                    total_w = int(QGuiApplication.primaryScreen().availableGeometry().width() * 0.82)
                except Exception:
                    total_w = 1280

            # 设置侧边栏宽度
            if sidebar is not None and total_w > 0:
                target_w = max(240, int(total_w * ratio))  # 至少保留 120px 可用空间
                print(f"Setting sidebar width: {target_w}")
                sidebar.setMinimumWidth(target_w)
                sidebar.setMaximumWidth(target_w)
                sidebar.setFixedWidth(target_w)

            # 设置水平布局伸缩策略：sidebar 尽量保持最小，content 占据其余空间
            layout = central.layout() if central is not None else None
            if isinstance(layout, QHBoxLayout):
                layout.setStretch(0, 0)  # sidebar
                layout.setStretch(1, 1)  # content
        except Exception:
            pass

    def resizeEvent(self, event):
        """在窗口尺寸变化时保持侧边栏为 33% 宽度。"""
        try:
            self.adjust_sidebar_ratio(0.33)
        except Exception:
            pass
        super().resizeEvent(event)

    def load_styles(self):
        """加载样式文件"""
        try:
            with open('styles.qss', 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("样式文件 styles.qss 未找到")

    def load_pages(self):
        """加载页面内容"""
        # 加载页面UI文件
        pages_widget = uic.loadUi('pages.ui')

        # 提取各个页面并添加到stackedWidget
        page_names = [
            'page', 'page_2', 'page_3', 'page_dialog', 'page_5', 'page_6',
            'page_4', 'page_voice_clone', 'page_terminal_room'
        ]

        for page_name in page_names:
            page = getattr(pages_widget, page_name)
            self.ui.stackedWidget.addWidget(page)
            # 将页面控件绑定到主UI对象，方便后续访问
            setattr(self.ui, page_name, page)

        # 绑定页面中的控件
        self.bind_page_widgets()
        try:
            self.log_signal.emit(f"[Live2D] load_pages: stackedWidget 页数={self.ui.stackedWidget.count()}")
        except Exception:
            pass

    def bind_page_widgets(self):
        """绑定页面中的控件到主UI对象"""
        # 需要绑定的控件列表
        widget_names = [
            'pushButton_8', 'pushButton_7', 'pushButton_clearLog',
            'checkBox_mcp', 'checkBox_5', 'textEdit_2', 'textEdit',
            'lineEdit', 'lineEdit_2', 'lineEdit_3', 'textEdit_3',
            'lineEdit_4', 'checkBox_3', 'lineEdit_5', 'checkBox_4',
            'checkBox', 'lineEdit_interval',
            'start_singing_btn', 'stop_singing_btn',
            'checkBox_2', 'lineEdit_6',
            'checkBox_asr', 'checkBox_tts', 'checkBox_subtitle', 'checkBox_live2d',
            # 新增：Live2D模型选择与服务/终端控制相关控件（若存在则绑定）
            'comboBox_live2d_models',
            'pushButton_start_terminal', 'pushButton_stop_terminal',
            'pushButton_start_asr', 'pushButton_stop_asr',
            'pushButton_start_bert', 'pushButton_stop_bert',
            'pushButton_start_rag', 'pushButton_stop_rag',
            'textEdit_tts_log', 'textEdit_asr_log', 'textEdit_bert_log', 'textEdit_rag_log',
            'label_terminal_status', 'label_asr_status', 'label_bert_status', 'label_rag_status',
            # 声音克隆页常用控件
            'textEdit_voice_text', 'lineEdit_character_name', 'comboBox_language',
            'pushButton_generate_bat', 'pushButton_select_model', 'pushButton_select_audio',
            'label_model_status', 'label_audio_status', 'label_bat_status'
        ]

        # 在所有页面中查找并绑定控件
        combo_found = False
        for i in range(self.ui.stackedWidget.count()):
            page = self.ui.stackedWidget.widget(i)
            for widget_name in widget_names:
                widget = page.findChild(QWidget, widget_name)
                if widget:
                    setattr(self.ui, widget_name, widget)
                    if widget_name == 'comboBox_live2d_models':
                        combo_found = True
        if combo_found:
            try:
                self.log_signal.emit('[Live2D] bind_page_widgets: 已找到 comboBox_live2d_models 并绑定')
            except Exception:
                pass
        else:
            try:
                self.log_signal.emit('[Live2D] bind_page_widgets: 未发现 comboBox_live2d_models')
            except Exception:
                pass

    def setup_drag_drop_targets(self):
        """为声音克隆上传按钮安装事件过滤器以支持拖拽。"""
        btn_model = getattr(self.ui, 'pushButton_select_model', None)
        btn_audio = getattr(self.ui, 'pushButton_select_audio', None)
        for btn in (btn_model, btn_audio):
            if isinstance(btn, QWidget):
                try:
                    btn.setAcceptDrops(True)
                    btn.installEventFilter(self)
                except Exception:
                    pass

    def setup_motion_buttons(self):
        """设置动画控制按钮"""
        # 只绑定开始唱歌和停止唱歌按钮
        if hasattr(self.ui, 'start_singing_btn'):
            self.ui.start_singing_btn.clicked.connect(lambda: self.trigger_motion(5))  # 开始唱歌
        if hasattr(self.ui, 'stop_singing_btn'):
            self.ui.stop_singing_btn.clicked.connect(lambda: self.trigger_motion(7))  # 停止唱歌
        # 终端/服务按钮（若存在则绑定）
        if hasattr(self.ui, 'pushButton_start_terminal'):
            self.ui.pushButton_start_terminal.clicked.connect(self.start_terminal)
        if hasattr(self.ui, 'pushButton_stop_terminal'):
            self.ui.pushButton_stop_terminal.clicked.connect(self.stop_terminal)
        if hasattr(self.ui, 'pushButton_start_asr'):
            self.ui.pushButton_start_asr.clicked.connect(self.start_asr)
        if hasattr(self.ui, 'pushButton_stop_asr'):
            self.ui.pushButton_stop_asr.clicked.connect(self.stop_asr)
        if hasattr(self.ui, 'pushButton_start_bert'):
            self.ui.pushButton_start_bert.clicked.connect(self.start_bert)
        if hasattr(self.ui, 'pushButton_stop_bert'):
            self.ui.pushButton_stop_bert.clicked.connect(self.stop_bert)
        if hasattr(self.ui, 'pushButton_start_rag'):
            self.ui.pushButton_start_rag.clicked.connect(self.start_rag)
        if hasattr(self.ui, 'pushButton_stop_rag'):
            self.ui.pushButton_stop_rag.clicked.connect(self.stop_rag)
        # 声音克隆按钮（若存在则绑定）
        if hasattr(self.ui, 'pushButton_generate_bat'):
            self.ui.pushButton_generate_bat.clicked.connect(self.generate_voice_clone_bat)
        if hasattr(self.ui, 'pushButton_select_model'):
            self.ui.pushButton_select_model.clicked.connect(self.select_model_file)
        if hasattr(self.ui, 'pushButton_select_audio'):
            self.ui.pushButton_select_audio.clicked.connect(self.select_audio_file)

    def trigger_motion(self, motion_index):
        """触发指定动作"""
        if self.live2d_process and self.live2d_process.poll() is None:
            try:
                # 通过HTTP请求触发动作
                import urllib.request
                import urllib.error

                # 构造请求数据
                data = json.dumps({"action": "trigger_motion", "motion_index": motion_index}).encode('utf-8')

                # 发送HTTP请求到桌宠应用
                req = urllib.request.Request(
                    'http://localhost:3002/control-motion',
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )

                try:
                    response = urllib.request.urlopen(req, timeout=1)
                    result = json.loads(response.read().decode('utf-8'))
                    if result.get('success'):
                        self.toast.show_message(f"已触发动作 {motion_index + 1}", 1500)
                    else:
                        self.toast.show_message(f"动作触发失败: {result.get('message', '未知错误')}", 2000)
                except urllib.error.URLError:
                    # 如果HTTP请求失败，尝试使用subprocess发送按键
                    self.send_motion_hotkey(motion_index + 1)
                    self.toast.show_message(f"已发送动作快捷键 {motion_index + 1}", 1500)

            except Exception as e:
                print(f"触发动作失败: {e}")
                self.toast.show_message(f"动作触发失败: {str(e)}", 2000)
        else:
            self.toast.show_message("桌宠未启动，无法触发动作", 2000)

    def stop_all_motions(self):
        """停止所有动作"""
        if self.live2d_process and self.live2d_process.poll() is None:
            try:
                import urllib.request
                import urllib.error

                # 构造请求数据
                data = json.dumps({"action": "stop_all_motions"}).encode('utf-8')

                # 发送HTTP请求
                req = urllib.request.Request(
                    'http://localhost:3002/control-motion',
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )

                try:
                    response = urllib.request.urlopen(req, timeout=1)
                    result = json.loads(response.read().decode('utf-8'))
                    if result.get('success'):
                        self.toast.show_message("已停止所有动作", 1500)
                    else:
                        self.toast.show_message(f"停止动作失败: {result.get('message', '未知错误')}", 2000)
                except urllib.error.URLError:
                    # 如果HTTP请求失败，尝试使用subprocess发送按键
                    self.send_motion_hotkey(0)
                    self.toast.show_message("已发送停止动作快捷键", 1500)

            except Exception as e:
                print(f"停止动作失败: {e}")
                self.toast.show_message(f"停止动作失败: {str(e)}", 2000)
        else:
            self.toast.show_message("桌宠未启动，无法停止动作", 2000)

    def send_motion_hotkey(self, motion_number):
        """发送动作快捷键"""
        try:
            # 使用Windows API发送按键组合
            import ctypes
            from ctypes import wintypes

            # 定义常量
            KEYEVENTF_KEYUP = 0x0002
            VK_CONTROL = 0x11
            VK_SHIFT = 0x10

            # 数字键的虚拟键码
            number_keys = {
                0: 0x30, 1: 0x31, 2: 0x32, 3: 0x33, 4: 0x34,
                5: 0x35, 6: 0x36, 7: 0x37, 8: 0x38, 9: 0x39
            }

            if motion_number in number_keys:
                # 按下 Ctrl+Shift+数字
                ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
                ctypes.windll.user32.keybd_event(number_keys[motion_number], 0, 0, 0)

                # 释放按键
                ctypes.windll.user32.keybd_event(number_keys[motion_number], 0, KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        except Exception as e:
            print(f"发送快捷键失败: {e}")

    # ===== 服务与日志 =====
    def update_service_log(self, service_name: str, text: str):
        """更新指定服务的日志显示（如果对应的文本框存在）"""
        log_widgets = {
            'asr': getattr(self.ui, 'textEdit_asr_log', None),
            'tts': getattr(self.ui, 'textEdit_tts_log', None),
            'bert': getattr(self.ui, 'textEdit_bert_log', None),
            'rag': getattr(self.ui, 'textEdit_rag_log', None),
        }
        widget = log_widgets.get(service_name)
        if widget:
            widget.append(text)
            sb = widget.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def read_live2d_logs(self):
        """读取桌宠进程的标准输出"""
        if not self.live2d_process:
            return

        # 持续读取直到进程结束
        for line in iter(self.live2d_process.stdout.readline, ''):
            if line:
                self.log_signal.emit(line.strip())
            if self.live2d_process.poll() is not None:
                break

    def tail_log_file(self):
        """实时读取runtime.log文件"""
        log_file = "runtime.log"

        # 如果文件存在，先清空
        if os.path.exists(log_file):
            open(log_file, 'w').close()

        # 等待文件创建
        while not os.path.exists(log_file):
            time.sleep(0.1)
            # 如果进程已经结束，停止等待
            if self.live2d_process and self.live2d_process.poll() is not None:
                return

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(0, 2)  # 移到文件末尾
                while True:
                    line = f.readline()
                    if line:
                        self.log_signal.emit(line.strip())
                    else:
                        time.sleep(0.1)

                    # 如果进程已经结束，停止读取
                    if self.live2d_process and self.live2d_process.poll() is not None:
                        break
        except Exception as e:
            self.log_signal.emit(f"读取日志文件出错: {str(e)}")

    def update_log(self, text):
        """更新日志到UI（在主线程中执行）"""
        self.ui.textEdit_2.append(text)

    def update_mcp_log(self, text):
        """更新MCP日志到UI（在主线程中执行）"""
        self.ui.textEdit.append(text)

    def eventFilter(self, obj, event):
        """全局事件过滤器 - 捕获所有鼠标事件"""
        if event.type() == QEvent.MouseMove:
            # 将全局坐标转换为窗口本地坐标
            if self.isVisible():
                local_pos = self.mapFromGlobal(QCursor.pos())

                if self.resizing and self.resize_edge:
                    self.do_resize(QCursor.pos())
                    return True
                else:
                    # 更新光标
                    edge = self.get_resize_edge(local_pos)
                    if edge and self.rect().contains(local_pos):
                        self.setCursor(self.get_resize_cursor(edge))
                    else:
                        self.setCursor(Qt.ArrowCursor)

        elif event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self.isVisible():
                local_pos = self.mapFromGlobal(QCursor.pos())
                if self.rect().contains(local_pos):
                    self.resize_edge = self.get_resize_edge(local_pos)
                    if self.resize_edge:
                        self.resizing = True
                        self.resize_start_pos = QCursor.pos()
                        self.resize_start_geometry = self.geometry()
                        return True

        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton and self.resizing:
                self.resizing = False
                self.resize_edge = None
                self.setCursor(Qt.ArrowCursor)
                return True

        # 声音克隆页拖拽处理（按钮级）
        try:
            if event.type() == QEvent.DragEnter:
                if obj is getattr(self.ui, 'pushButton_select_model', None) or obj is getattr(self.ui, 'pushButton_select_audio', None):
                    md = event.mimeData()
                    if md and md.hasUrls():
                        # 简单校验扩展名
                        url = md.urls()[0]
                        if url.isLocalFile():
                            fp = url.toLocalFile().lower()
                            if fp.endswith(('.pth', '.wav')):
                                event.acceptProposedAction()
                                return True
            elif event.type() == QEvent.Drop:
                if obj is getattr(self.ui, 'pushButton_select_model', None) or obj is getattr(self.ui, 'pushButton_select_audio', None):
                    self.voice_clone_dropEvent(event)
                    return True
        except Exception:
            pass

        return super().eventFilter(obj, event)

    def get_resize_edge(self, pos):
        """判断鼠标是否在边缘 - 只检测四个角"""
        rect = self.rect()
        x, y = pos.x(), pos.y()

        # 检查是否在边缘
        left = x <= self.edge_margin
        right = x >= rect.width() - self.edge_margin
        top = y <= self.edge_margin
        bottom = y >= rect.height() - self.edge_margin

        # 只返回四个角的情况
        if top and left:
            return 'top-left'
        elif top and right:
            return 'top-right'
        elif bottom and left:
            return 'bottom-left'
        elif bottom and right:
            return 'bottom-right'
        return None

    def get_resize_cursor(self, edge):
        """根据边缘返回光标样式"""
        cursor_map = {
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top-left': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
        }
        return cursor_map.get(edge, Qt.ArrowCursor)

    def mousePressEvent(self, event):
        # 这些方法保留，但主要逻辑在eventFilter中
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 这些方法保留，但主要逻辑在eventFilter中
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 这些方法保留，但主要逻辑在eventFilter中
        super().mouseReleaseEvent(event)

    def do_resize(self, global_pos):
        """执行窗口调整大小"""
        if not self.resize_start_pos or not self.resize_start_geometry:
            return

        delta = global_pos - self.resize_start_pos
        geo = QRect(self.resize_start_geometry)

        # 处理水平调整
        if 'left' in self.resize_edge:
            geo.setLeft(geo.left() + delta.x())
            geo.setWidth(geo.width() - delta.x())
        elif 'right' in self.resize_edge:
            geo.setWidth(geo.width() + delta.x())

        # 处理垂直调整
        if 'top' in self.resize_edge:
            geo.setTop(geo.top() + delta.y())
            geo.setHeight(geo.height() - delta.y())
        elif 'bottom' in self.resize_edge:
            geo.setHeight(geo.height() + delta.y())

        self.setGeometry(geo)

    def set_btu(self):
        self.ui.pushButton.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(1))
        self.ui.pushButton_3.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(0))
        self.ui.pushButton_ui.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(2))  # UI设置 (page_3)
        self.ui.pushButton_5.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(3))  # 对话设置 (page_dialog)
        self.ui.pushButton_6.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(4))  # 主动对话 (page_5)
        self.ui.pushButton_animation.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(5))  # 动画 (page_6)
        self.ui.pushButton_2.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(6))  # 直播 (page_4)
        self.ui.saveConfigButton.clicked.connect(self.save_config)
        self.ui.pushButton_8.clicked.connect(self.start_live_2d)
        self.ui.pushButton_7.clicked.connect(self.close_live_2d)
        self.ui.pushButton_clearLog.clicked.connect(self.clear_logs)
        # 新增：声音克隆按钮跳转
        if hasattr(self.ui, 'pushButton_voice_clone'):
            # 尝试根据对象名跳转，否则回退索引查找
            def goto_voice_clone():
                # 优先通过对象直接切换
                page = getattr(self.ui, 'page_voice_clone', None)
                if page:
                    self.ui.stackedWidget.setCurrentWidget(page)
                    return
                # 回退：按名查找
                for i in range(self.ui.stackedWidget.count()):
                    w = self.ui.stackedWidget.widget(i)
                    if w.objectName() == 'page_voice_clone':
                        self.ui.stackedWidget.setCurrentIndex(i)
                        return
            self.ui.pushButton_voice_clone.clicked.connect(goto_voice_clone)
        # 新增：终端控制室跳转
        if hasattr(self.ui, 'pushButton_terminal_room'):
            def goto_terminal_room():
                page = getattr(self.ui, 'page_terminal_room', None)
                if page:
                    self.ui.stackedWidget.setCurrentWidget(page)
                    return
                for i in range(self.ui.stackedWidget.count()):
                    w = self.ui.stackedWidget.widget(i)
                    if w.objectName() == 'page_terminal_room':
                        self.ui.stackedWidget.setCurrentIndex(i)
                        return
            self.ui.pushButton_terminal_room.clicked.connect(goto_terminal_room)

    def clear_logs(self):
        """清空日志功能"""
        # 清空桌宠日志
        self.ui.textEdit_2.clear()
        # 清空MCP日志
        self.ui.textEdit.clear()
        # 显示提示
        self.toast.show_message("日志已清空", 1500)

    # ===== 声音克隆（Voice Clone） =====
    def voice_clone_dragEnterEvent(self, event: QDragEnterEvent):
        """拖放进入（仅当目标控件绑定了该事件时生效）"""
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                fp = url.toLocalFile().lower()
                if fp.endswith('.pth') or fp.endswith('.wav'):
                    event.acceptProposedAction()

    def voice_clone_dropEvent(self, event: QDropEvent):
        """处理声音克隆区域的文件拖放"""
        try:
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    filename = os.path.basename(file_path)
                    # 目标1：py-my-neuro/Voice_Model_Factory
                    vm_dir = os.path.join(get_app_path(), 'Voice_Model_Factory')
                    os.makedirs(vm_dir, exist_ok=True)
                    dest_path = os.path.join(vm_dir, filename)
                    shutil.copy2(file_path, dest_path)
                    # 目标2：live-2d/Voice_Model_Factory（同级目录下）
                    root_dir = os.path.dirname(get_app_path())
                    live2d_vm_dir = os.path.join(root_dir, 'live-2d', 'Voice_Model_Factory')
                    try:
                        os.makedirs(live2d_vm_dir, exist_ok=True)
                        dest_live2d = os.path.join(live2d_vm_dir, filename)
                        shutil.copy2(file_path, dest_live2d)
                    except Exception:
                        dest_live2d = None
                    if filename.lower().endswith('.pth'):
                        # 优先使用 live-2d 中的路径（若拷贝成功）
                        self.selected_model_path = dest_live2d or dest_path
                        if hasattr(self.ui, 'label_model_status'):
                            self.ui.label_model_status.setText(f"已上传：{filename}")
                    if filename.lower().endswith('.wav'):
                        self.selected_audio_path = dest_live2d or dest_path
                        if hasattr(self.ui, 'label_audio_status'):
                            self.ui.label_audio_status.setText(f"已上传：{filename}")
            self.toast.show_message('文件已导入到 Voice_Model_Factory', 1500)
        except Exception as e:
            self.toast.show_message(f'拖拽处理失败：{e}', 3000)

    def select_model_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, '选择模型文件', '', 'PyTorch模型文件 (*.pth);;所有文件 (*)')
            if not file_path:
                return
            # 目标1：py-my-neuro/Voice_Model_Factory
            vm_dir = os.path.join(get_app_path(), 'Voice_Model_Factory')
            os.makedirs(vm_dir, exist_ok=True)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(vm_dir, filename)
            shutil.copy2(file_path, dest_path)
            # 目标2：live-2d/Voice_Model_Factory
            root_dir = os.path.dirname(get_app_path())
            live2d_vm_dir = os.path.join(root_dir, 'live-2d', 'Voice_Model_Factory')
            try:
                os.makedirs(live2d_vm_dir, exist_ok=True)
                dest_live2d = os.path.join(live2d_vm_dir, filename)
                shutil.copy2(file_path, dest_live2d)
            except Exception:
                dest_live2d = None
            self.selected_model_path = dest_live2d or dest_path
            if hasattr(self.ui, 'label_model_status'):
                self.ui.label_model_status.setText(f"已上传：{filename}")
            self.toast.show_message('模型文件已保存到 Voice_Model_Factory', 1500)
        except Exception as e:
            self.toast.show_message(f"选择模型文件失败：{e}", 3000)

    def select_audio_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, '选择音频文件', '', '音频文件 (*.wav);;所有文件 (*)')
            if not file_path:
                return
            # 目标1：py-my-neuro/Voice_Model_Factory
            vm_dir = os.path.join(get_app_path(), 'Voice_Model_Factory')
            os.makedirs(vm_dir, exist_ok=True)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(vm_dir, filename)
            shutil.copy2(file_path, dest_path)
            # 目标2：live-2d/Voice_Model_Factory
            root_dir = os.path.dirname(get_app_path())
            live2d_vm_dir = os.path.join(root_dir, 'live-2d', 'Voice_Model_Factory')
            try:
                os.makedirs(live2d_vm_dir, exist_ok=True)
                dest_live2d = os.path.join(live2d_vm_dir, filename)
                shutil.copy2(file_path, dest_live2d)
            except Exception:
                dest_live2d = None
            self.selected_audio_path = dest_live2d or dest_path
            if hasattr(self.ui, 'label_audio_status'):
                self.ui.label_audio_status.setText(f"已上传：{filename}")
        except Exception as e:
            self.toast.show_message(f"选择音频文件失败：{e}", 3000)

    def generate_voice_clone_bat(self):
        try:
            text = getattr(self.ui, 'textEdit_voice_text', None).toPlainText().strip() if hasattr(self.ui, 'textEdit_voice_text') else ''
            character_name = getattr(self.ui, 'lineEdit_character_name', None).text().strip() if hasattr(self.ui, 'lineEdit_character_name') else ''
            if not text or not character_name or not self.selected_model_path or not self.selected_audio_path:
                self.toast.show_message('请先完善文本/角色名并上传模型与参考音频', 2000)
                return
            language_widget = getattr(self.ui, 'comboBox_language', None)
            language = language_widget.currentText().split(' - ')[0] if language_widget and language_widget.currentText() else 'zh'
            # 生成到 py-my-neuro/Voice_Model_Factory 目录
            vm_dir = os.path.join(get_app_path(), 'Voice_Model_Factory')
            os.makedirs(vm_dir, exist_ok=True)
            bat_path = os.path.join(vm_dir, f"{character_name}_TTS.bat")
            # 优先定位到 live-2d 下的路径（便于与预期脚本一致）
            root_dir = os.path.dirname(get_app_path())
            live2d_vm_dir = os.path.join(root_dir, 'live-2d', 'Voice_Model_Factory')
            model_name = os.path.basename(self.selected_model_path)
            audio_name = os.path.basename(self.selected_audio_path)
            model_path_for_cmd = os.path.join(live2d_vm_dir, model_name)
            audio_path_for_cmd = os.path.join(live2d_vm_dir, audio_name)
            if not os.path.exists(model_path_for_cmd):
                model_path_for_cmd = self.selected_model_path
            if not os.path.exists(audio_path_for_cmd):
                audio_path_for_cmd = self.selected_audio_path
            # 组装命令（与期望尽量一致，不加引号）
            cmd = (
                f"python tts_api.py -p 5000 -d cuda -s {model_path_for_cmd} "
                f"-dr {audio_path_for_cmd} -dt \"{text}\" -dl {language}\n"
            )
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write('@echo off\n')
                f.write('call conda activate my-neuro\n')
                f.write('cd ..\\..\\tts-studio\n')
                f.write(cmd)
                f.write('pause\n')
            if hasattr(self.ui, 'label_bat_status'):
                self.ui.label_bat_status.setText(f"已生成：Voice_Model_Factory/{character_name}_TTS.bat")
            self.toast.show_message(f"生成成功：{character_name}_TTS.bat", 1500)
        except Exception as e:
            self.toast.show_message(f"生成失败：{e}", 3000)

    def start_voice_tts(self):
        try:
            character_name = getattr(self.ui, 'lineEdit_character_name', None).text().strip() if hasattr(self.ui, 'lineEdit_character_name') else ''
            if not character_name:
                self.toast.show_message('请填写角色名', 1500)
                return
            # 生成位置在 py-my-neuro/Voice_Model_Factory
            bat_path = os.path.join(get_app_path(), 'Voice_Model_Factory', f"{character_name}_TTS.bat")
            if not os.path.exists(bat_path):
                self.toast.show_message('未找到bat文件，请先生成', 1500)
                return
            if self.voice_clone_process and self.voice_clone_process.poll() is None:
                self.toast.show_message('声音克隆已在运行', 1500)
                return
            self.voice_clone_process = subprocess.Popen(bat_path, shell=True, cwd=os.path.dirname(bat_path), creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            if hasattr(self.ui, 'label_voice_tts_status'):
                self.ui.label_voice_tts_status.setText('状态：声音克隆服务正在运行')
            self.toast.show_message('声音克隆服务启动成功', 1500)
        except Exception as e:
            self.toast.show_message(f"启动声音克隆失败：{e}", 3000)

    def stop_voice_tts(self):
        try:
            subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%tts_api%\'" delete', shell=True, capture_output=True)
            self.voice_clone_process = None
            if hasattr(self.ui, 'label_voice_tts_status'):
                self.ui.label_voice_tts_status.setText('状态：声音克隆服务未启动')
            self.toast.show_message('声音克隆服务已关闭', 1500)
        except Exception as e:
            self.toast.show_message(f"关闭声音克隆失败：{e}", 3000)

    # ===== 终端控制室：TTS/ASR/BERT/RAG =====
    def _ensure_log_file(self, key: str):
        log_file = self.log_file_paths.get(key)
        if not log_file:
            return None
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'w', encoding='utf-8'):
            pass
        return log_file

    def start_terminal(self):
        try:
            if self.terminal_process and self.terminal_process.poll() is None:
                self.toast.show_message('TTS服务已在运行', 1500)
                return
            base_path = get_base_path()
            bat_file = os.path.join(base_path, 'TTS.bat')
            if not os.path.exists(bat_file):
                self.toast.show_message('未找到 TTS.bat', 1500)
                return
            # 启动进程并捕获控制台输出
            if 'tts' in self.proc_readers:
                try:
                    self.proc_readers['tts'].stop()
                except Exception:
                    pass
            self.terminal_process = subprocess.Popen(
                bat_file,
                shell=True,
                cwd=base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.proc_readers['tts'] = ProcessReader(self.terminal_process)
            self.proc_readers['tts'].line_signal.connect(lambda t: self.update_service_log('tts', t))
            self.proc_readers['tts'].start()
            if hasattr(self.ui, 'label_terminal_status'):
                self.ui.label_terminal_status.setText('状态：TTS服务正在运行')
            self.toast.show_message('TTS服务启动成功', 1500)
        except Exception as e:
            self.toast.show_message(f"启动TTS失败：{e}", 3000)

    def stop_terminal(self):
        try:
            if 'tts' in self.proc_readers:
                try:
                    self.proc_readers['tts'].stop()
                except Exception:
                    pass
            subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%TTS%\'" delete', shell=True, capture_output=True)
            self.terminal_process = None
            if hasattr(self.ui, 'label_terminal_status'):
                self.ui.label_terminal_status.setText('状态：TTS服务未启动')
            self.toast.show_message('TTS服务已关闭', 1500)
        except Exception as e:
            self.toast.show_message(f"关闭TTS失败：{e}", 3000)

    def start_asr(self):
        try:
            if self.asr_process and self.asr_process.poll() is None:
                self.toast.show_message('ASR已在运行', 1500)
                return
            base_path = get_base_path()
            bat_file = os.path.join(base_path, 'ASR.bat')
            if not os.path.exists(bat_file):
                self.toast.show_message('未找到 ASR.bat', 1500)
                return
            if 'asr' in self.proc_readers:
                try:
                    self.proc_readers['asr'].stop()
                except Exception:
                    pass
            self.asr_process = subprocess.Popen(
                bat_file,
                shell=True,
                cwd=base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.proc_readers['asr'] = ProcessReader(self.asr_process)
            self.proc_readers['asr'].line_signal.connect(lambda t: self.update_service_log('asr', t))
            self.proc_readers['asr'].start()
            if hasattr(self.ui, 'label_asr_status'):
                self.ui.label_asr_status.setText('状态：ASR服务正在运行')
            self.toast.show_message('ASR服务启动成功', 1500)
        except Exception as e:
            self.toast.show_message(f"启动ASR失败：{e}", 3000)

    def stop_asr(self):
        try:
            if 'asr' in self.proc_readers:
                try:
                    self.proc_readers['asr'].stop()
                except Exception:
                    pass
            subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%ASR%\'" delete', shell=True, capture_output=True)
            self.asr_process = None
            if hasattr(self.ui, 'label_asr_status'):
                self.ui.label_asr_status.setText('状态：ASR服务未启动')
            self.toast.show_message('ASR服务已关闭', 1500)
        except Exception as e:
            self.toast.show_message(f"关闭ASR失败：{e}", 3000)

    def start_bert(self):
        try:
            if self.bert_process and self.bert_process.poll() is None:
                self.toast.show_message('BERT已在运行', 1500)
                return
            base_path = get_base_path()
            bat_file = os.path.join(base_path, 'bert.bat')
            if not os.path.exists(bat_file):
                self.toast.show_message('未找到 bert.bat', 1500)
                return
            if 'bert' in self.proc_readers:
                try:
                    self.proc_readers['bert'].stop()
                except Exception:
                    pass
            self.bert_process = subprocess.Popen(
                bat_file,
                shell=True,
                cwd=base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.proc_readers['bert'] = ProcessReader(self.bert_process)
            self.proc_readers['bert'].line_signal.connect(lambda t: self.update_service_log('bert', t))
            self.proc_readers['bert'].start()
            if hasattr(self.ui, 'label_bert_status'):
                self.ui.label_bert_status.setText('状态：BERT服务正在运行')
            self.toast.show_message('BERT服务启动成功', 1500)
        except Exception as e:
            self.toast.show_message(f"启动BERT失败：{e}", 3000)

    def stop_bert(self):
        try:
            if 'bert' in self.proc_readers:
                try:
                    self.proc_readers['bert'].stop()
                except Exception:
                    pass
            subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%bert%\'" delete', shell=True, capture_output=True)
            self.bert_process = None
            if hasattr(self.ui, 'label_bert_status'):
                self.ui.label_bert_status.setText('状态：BERT服务未启动')
            self.toast.show_message('BERT服务已关闭', 1500)
        except Exception as e:
            self.toast.show_message(f"关闭BERT失败：{e}", 3000)

    def start_rag(self):
        try:
            if self.rag_process and self.rag_process.poll() is None:
                self.toast.show_message('RAG已在运行', 1500)
                return
            base_path = get_base_path()
            bat_file = os.path.join(base_path, 'RAG.bat')
            if not os.path.exists(bat_file):
                self.toast.show_message('未找到 RAG.bat', 1500)
                return
            if 'rag' in self.proc_readers:
                try:
                    self.proc_readers['rag'].stop()
                except Exception:
                    pass
            self.rag_process = subprocess.Popen(
                bat_file,
                shell=True,
                cwd=base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.proc_readers['rag'] = ProcessReader(self.rag_process)
            self.proc_readers['rag'].line_signal.connect(lambda t: self.update_service_log('rag', t))
            self.proc_readers['rag'].start()
            if hasattr(self.ui, 'label_rag_status'):
                self.ui.label_rag_status.setText('状态：RAG服务正在运行')
            self.toast.show_message('RAG服务启动成功', 1500)
        except Exception as e:
            self.toast.show_message(f"启动RAG失败：{e}", 3000)

    def stop_rag(self):
        try:
            if 'rag' in self.proc_readers:
                try:
                    self.proc_readers['rag'].stop()
                except Exception:
                    pass
            subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%RAG%\'" delete', shell=True, capture_output=True)
            self.rag_process = None
            if hasattr(self.ui, 'label_rag_status'):
                self.ui.label_rag_status.setText('状态：RAG服务未启动')
            self.toast.show_message('RAG服务已关闭', 1500)
        except Exception as e:
            self.toast.show_message(f"关闭RAG失败：{e}", 3000)

    # ===== Live2D 模型选择（启动页） =====
    def init_live2d_models(self):
        try:
            self.log_signal.emit('[Live2D] 初始化模型下拉...')
        except Exception:
            pass
        self.refresh_model_list()
        combo = self.get_live2d_combo()
        if combo:
            try:
                combo.currentTextChanged.connect(self.on_live2d_model_changed)
                self.log_signal.emit('[Live2D] 下拉框信号绑定完成')
            except Exception as e:
                try:
                    self.log_signal.emit(f'[Live2D] 绑定信号失败: {e}')
                except Exception:
                    pass
        else:
            try:
                self.log_signal.emit('[Live2D] 未找到下拉框控件 comboBox_live2d_models')
            except Exception:
                pass

    def scan_live2d_models(self):
        models = []
        # 首选 live-2d/2D 目录（位于工作区根目录下）
        candidates = [
            os.path.join(get_base_path(), 'live-2d', '2D'),
            # 兜底：当前应用目录下的 2D（如果有人放在这里）
            os.path.join(get_app_path(), '2D'),
            # 兜底：工作区根目录直接存在 2D 目录
            os.path.join(get_base_path(), '2D'),
        ]
        seen = set()
        try:
            self.log_signal.emit('[Live2D] 扫描模型目录:')
            for d in candidates:
                self.log_signal.emit(f'  - {d}  exists={os.path.exists(d)}')
        except Exception:
            pass
        for models_dir in candidates:
            if os.path.exists(models_dir):
                try:
                    for folder in os.listdir(models_dir):
                        full = os.path.join(models_dir, folder)
                        if os.path.isdir(full) and folder not in seen:
                            seen.add(folder)
                            models.append(folder)
                except Exception as e:
                    try:
                        self.log_signal.emit(f'[Live2D] 列表目录失败 {models_dir}: {e}')
                    except Exception:
                        pass
        try:
            self.log_signal.emit(f'[Live2D] 共发现模型: {len(models)} -> {models}')
        except Exception:
            pass
        return models

    def refresh_model_list(self):
        combo = self.get_live2d_combo()
        if not combo:
            try:
                self.log_signal.emit('[Live2D] refresh_model_list: 未找到下拉框，跳过')
            except Exception:
                pass
            return
        models = self.scan_live2d_models()
        combo.clear()
        if not models:
            combo.addItem('未找到任何模型')
            try:
                self.log_signal.emit('[Live2D] 未找到任何模型，已填充占位项')
            except Exception:
                pass
        else:
            combo.addItems(models)
            try:
                self.log_signal.emit(f'[Live2D] 已填充 {len(models)} 个模型到下拉框')
            except Exception:
                pass
        # 读取 main.js 中 priorityFolders 提示当前设置
        try:
            # 读取 live-2d/main.js（优先）
            main_js_path = os.path.join(get_base_path(), 'live-2d', 'main.js')
            if os.path.exists(main_js_path):
                with open(main_js_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                m = re.search(r"const\s+priorityFolders\s*=\s*\[(.*?)\]", content, re.S)
                # 若配置中有保存的模型名，优先选中
                ui_conf = self.config.get('ui', {}) if isinstance(self.config, dict) else {}
                preferred = ui_conf.get('live2d_model') if isinstance(ui_conf, dict) else None
                try:
                    self.log_signal.emit(f'[Live2D] main.js 路径: {main_js_path}  hasPref={bool(preferred)}  preferred={preferred}')
                except Exception:
                    pass
                if preferred and preferred in models:
                    idx = combo.findText(preferred)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                        try:
                            self.log_signal.emit(f'[Live2D] 已根据配置选中: {preferred}')
                        except Exception:
                            pass
        except Exception:
            pass

    def get_live2d_combo(self):
        """稳健地找到 Live2D 下拉框，优先使用已绑定属性，否则全局查找。"""
        combo = getattr(self.ui, 'comboBox_live2d_models', None)
        if combo:
            return combo
        try:
            combo = self.ui.findChild(QComboBox, 'comboBox_live2d_models')
            if combo:
                setattr(self.ui, 'comboBox_live2d_models', combo)
                try:
                    self.log_signal.emit('[Live2D] 通过 findChild 找到 comboBox_live2d_models')
                except Exception:
                    pass
                return combo
        except Exception:
            pass
        # 兜底：遍历所有页查找
        try:
            for i in range(self.ui.stackedWidget.count()):
                page = self.ui.stackedWidget.widget(i)
                combo = page.findChild(QComboBox, 'comboBox_live2d_models')
                if combo:
                    setattr(self.ui, 'comboBox_live2d_models', combo)
                    try:
                        self.log_signal.emit('[Live2D] 在某个页面中找到 comboBox_live2d_models')
                    except Exception:
                        pass
                    return combo
        except Exception:
            pass
        return None

    def on_live2d_model_changed(self, model_name: str):
        """当下拉选中改变时：写入配置并尝试更新 main.js 的 priorityFolders。"""
        if not model_name or model_name == '未找到任何模型':
            return
        # 更新内存配置并保存
        if 'ui' not in self.config:
            self.config['ui'] = {}
        self.config['ui']['live2d_model'] = model_name
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        # 写 main.js
        try:
            self._write_priority_folder_to_main_js(model_name)
        except Exception:
            pass

    def _write_priority_folder_to_main_js(self, model_name: str):
        """将所选模型写入 main.js 的 priorityFolders 首位，保留其余顺序。"""
        # 定位到 live-2d/main.js
        main_js_path = os.path.join(get_base_path(), 'live-2d', 'main.js')
        if not os.path.exists(main_js_path):
            try:
                self.log_signal.emit(f'[Live2D] 未找到 main.js: {main_js_path}')
            except Exception:
                pass
            return
        try:
            with open(main_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 提取现有列表
            m = re.search(r"(const\s+priorityFolders\s*=\s*)\[(.*?)\]", content, re.S)
            models = self.scan_live2d_models()
            others = [x for x in models if x != model_name]
            new_list = ', '.join([f'"{model_name}"'] + [f'"{x}"' for x in others])
            if m:
                prefix = m.group(1)
                new_content = re.sub(r"const\s+priorityFolders\s*=\s*\[(.*?)\]",
                                     f"{prefix}[{new_list}]", content, flags=re.S)
            else:
                # 不存在则在文件顶部插入一行声明
                new_content = f"const priorityFolders = [{new_list}];\n" + content
            with open(main_js_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            try:
                self.log_signal.emit(f'[Live2D] 已更新 main.js priorityFolders -> 首选: {model_name}')
            except Exception:
                pass
        except Exception:
            try:
                self.log_signal.emit('[Live2D] 写 main.js 失败')
            except Exception:
                pass

    # ===== 服务状态检查（可选） =====
    def check_all_service_status(self):
        # 如果没有任何状态标签，直接返回
        has_any = any(hasattr(self.ui, name) for name in ['label_terminal_status','label_asr_status','label_bert_status','label_rag_status'])
        if not has_any:
            return
        self.check_service_status('tts', 5000, 'label_terminal_status')
        self.check_service_status('asr', 1000, 'label_asr_status')
        self.check_service_status('bert', 6007, 'label_bert_status')
        self.check_service_status('rag', 8002, 'label_rag_status')

    def check_service_status(self, service_name: str, port: int, status_label: str):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.8)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            label = getattr(self.ui, status_label, None)
            if not label:
                return
            if result == 0:
                label.setText(f"状态：{service_name.upper()}服务正在运行")
                self.update_status_indicator(service_name, True)
            else:
                label.setText(f"状态：{service_name.upper()}服务未启动")
                self.update_status_indicator(service_name, False)
        except Exception:
            label = getattr(self.ui, status_label, None)
            if label:
                label.setText(f"状态：{service_name.upper()}服务未启动")
            self.update_status_indicator(service_name, False)

    def update_status_indicator(self, service_name: str, is_running: bool):
        indicators = {
            'tts': 'label_tts_status_indicator',
            'asr': 'label_asr_status_indicator',
            'bert': 'label_bert_status_indicator',
            'rag': 'label_rag_status_indicator',
        }
        name = indicators.get(service_name)
        if not name:
            return
        indicator = getattr(self.ui, name, None)
        if indicator:
            color = '#52c41a' if is_running else '#f5222d'
            indicator.setStyleSheet(f"background-color:{color};border-radius:6px;min-width:12px;min-height:12px;")

    def set_config(self):
        """设置配置到UI控件 - 适配新配置格式"""
        # API配置
        self.ui.lineEdit.setText(self.config['api']['api_key'])
        self.ui.lineEdit_2.setText(self.config['api']['api_url'])
        self.ui.lineEdit_3.setText(self.config['api']['model'])
        self.ui.textEdit_3.setPlainText(self.config['api']['system_prompt'])

        # UI配置
        ui_config = self.config.get('ui', {})
        self.ui.lineEdit_4.setText(ui_config.get('intro_text', '你好啊！'))

        # 上下文配置
        context_config = self.config.get('context', {})
        self.ui.lineEdit_5.setText(str(context_config.get('max_messages', 40)))
        self.ui.checkBox_4.setChecked(context_config.get('enable_limit', True))

        # 输入配置
        inputs = self.config.get('inputs', {})

        # 自动对话设置
        auto_chat = inputs.get('auto_chat', {})
        self.ui.lineEdit_interval.setText(str(auto_chat.get('interval', 20)))
        self.ui.checkBox.setChecked(auto_chat.get('enabled', False))

        # 弹幕/直播设置
        danmu = inputs.get('danmu', {})
        self.ui.lineEdit_6.setText(str(danmu.get('room_id', 0)))
        self.ui.checkBox_2.setChecked(danmu.get('enabled', False))

        # 功能设置
        features = self.config.get('features', {})
        self.ui.checkBox_mcp.setChecked(features.get('function_calling', False))  # MCP对应function_calling
        self.ui.checkBox_5.setChecked(features.get('screenshot', False))  # 视觉功能对应screenshot

        # 文字输入框设置
        self.ui.checkBox_3.setChecked(inputs.get('keyboard', {}).get('enabled', True))

        # Live2D和字幕设置
        self.ui.checkBox_live2d.setChecked(features.get('live2d', True))
        self.ui.checkBox_subtitle.setChecked(features.get('subtitle', True))

        # ASR和TTS设置
        self.ui.checkBox_asr.setChecked(inputs.get('asr', {}).get('enabled', True))
        self.ui.checkBox_tts.setChecked(features.get('cut_text_tts', True))

        # Live2D模型下拉回显
        combo = getattr(self.ui, 'comboBox_live2d_models', None)
        if combo:
            ui_conf = self.config.get('ui', {})
            preferred = ui_conf.get('live2d_model') if isinstance(ui_conf, dict) else None
            if preferred is not None:
                idx = combo.findText(preferred)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def save_config(self):
        """保存配置 - 适配新配置格式"""
        current_config = self.load_config()

        # 更新API配置
        current_config['api']['api_key'] = self.ui.lineEdit.text()
        current_config['api']['api_url'] = self.ui.lineEdit_2.text()
        current_config['api']['model'] = self.ui.lineEdit_3.text()
        current_config['api']['system_prompt'] = self.ui.textEdit_3.toPlainText()

        # 更新UI配置
        if 'ui' not in current_config:
            current_config['ui'] = {}
        current_config['ui']['intro_text'] = self.ui.lineEdit_4.text()

        # 更新上下文配置
        if 'context' not in current_config:
            current_config['context'] = {}
        current_config['context']['max_messages'] = int(
            self.ui.lineEdit_5.text()) if self.ui.lineEdit_5.text().isdigit() else 40
        current_config['context']['enable_limit'] = self.ui.checkBox_4.isChecked()

        # 更新输入配置
        if 'inputs' not in current_config:
            current_config['inputs'] = {}

        # 自动对话设置
        interval = int(self.ui.lineEdit_interval.text()) if self.ui.lineEdit_interval.text().isdigit() else 20
        current_config['inputs']['auto_chat'] = {
            'enabled': self.ui.checkBox.isChecked(),
            'interval': interval,
            'priority': 4
        }

        # 弹幕设置
        room_id_text = self.ui.lineEdit_6.text()
        if room_id_text == "你的哔哩哔哩直播间的房间号" or room_id_text == "":
            room_id = 0
        else:
            room_id = int(room_id_text) if room_id_text.isdigit() else 0

        current_config['inputs']['danmu'] = {
            'room_id': room_id,
            'enabled': self.ui.checkBox_2.isChecked(),
            'priority': 3
        }

        # 确保其他输入配置存在
        if 'asr' not in current_config['inputs']:
            current_config['inputs']['asr'] = {'enabled': True, 'priority': 1}
        if 'keyboard' not in current_config['inputs']:
            current_config['inputs']['keyboard'] = {'enabled': True, 'priority': 2}

        # 更新keyboard的enabled状态
        current_config['inputs']['keyboard']['enabled'] = self.ui.checkBox_3.isChecked()

        # 更新ASR设置
        current_config['inputs']['asr']['enabled'] = self.ui.checkBox_asr.isChecked()

        # 更新功能配置
        if 'features' not in current_config:
            current_config['features'] = {}

        current_config['features']['function_calling'] = self.ui.checkBox_mcp.isChecked()
        current_config['features']['screenshot'] = self.ui.checkBox_5.isChecked()
        current_config['features']['cut_text_tts'] = self.ui.checkBox_tts.isChecked()
        current_config['features']['live2d'] = self.ui.checkBox_live2d.isChecked()
        current_config['features']['subtitle'] = self.ui.checkBox_subtitle.isChecked()

        # 保持其他features的默认值
        features_defaults = {
            'live2d': True,
            'audio_output': True,
            'cut_text_tts': True
        }
        for key, value in features_defaults.items():
            if key not in current_config['features']:
                current_config['features'][key] = value

        # 保存 Live2D 模型选择
        combo = getattr(self.ui, 'comboBox_live2d_models', None)
        if combo:
            if 'ui' not in current_config:
                current_config['ui'] = {}
            name = combo.currentText().strip()
            if name and name != '未找到任何模型':
                current_config['ui']['live2d_model'] = name
                # 同步写 main.js
                try:
                    self._write_priority_folder_to_main_js(name)
                except Exception:
                    pass

        # 保存配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=4)

        # 使用Toast提示
        self.toast.show_message("保存成功", 1500)

    def load_config(self):
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def start_live_2d(self):
        # 检查是否已经有桌宠在运行
        if self.live2d_process and self.live2d_process.poll() is None:
            self.toast.show_message("桌宠已在运行中，请勿重复启动", 2000)
            return

        # 最简单的启动方式 - 什么都不重定向
        self.live2d_process = subprocess.Popen(["python", "main_chat.py"])

        self.toast.show_message("桌宠启动中...", 1500)

    def start_mcp(self):
        """启动MCP服务器"""
        try:
            # live-2d 下的 server-tools
            root_dir = os.path.dirname(get_app_path())
            mcp_path = os.path.join(root_dir, 'live-2d', 'server-tools')
            server_file = os.path.join(mcp_path, "server.js")

            # 检查文件是否存在
            if not os.path.exists(server_file):
                print(f"MCP服务器文件不存在: {server_file}")
                return

            # 检查服务器目录是否存在
            server_dir_abs = os.path.abspath(mcp_path)
            if not os.path.exists(server_dir_abs):
                self.mcp_log_signal.emit(f"服务器目录不存在: {server_dir_abs}")
                return

            # 检查node.exe是否存在
            parent_dir = os.path.dirname(server_dir_abs)
            node_path = os.path.join(parent_dir, "node", "node.exe")
            if not os.path.exists(node_path):
                self.mcp_log_signal.emit(f"找不到Node.exe: {node_path}")
                return

            # 创建启动脚本 - 使用GBK编码，这是CMD默认编码
            bat_path = os.path.join(server_dir_abs, "start_server.bat")
            with open(bat_path, "w", encoding="gbk") as f:
                f.write("@echo off\n")
                f.write("cd /d %~dp0\n")
                f.write("echo 正在启动MCP服务器...\n")
                f.write("\"..\\node\\node.exe\" server.js\n")
                f.write("if %ERRORLEVEL% NEQ 0 pause\n")
                f.write("exit\n")

            self.mcp_log_signal.emit("正在启动MCP服务器...")

            # 隐藏CMD窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            self.mcp_process = subprocess.Popen(
                bat_path,
                cwd=server_dir_abs,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                universal_newlines=False,
                bufsize=0,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            # 启动线程读取MCP日志
            from threading import Thread
            Thread(target=self.read_mcp_logs, daemon=True).start()

            self.mcp_log_signal.emit("MCP服务器已启动")

        except Exception as e:
            print(f"启动MCP进程失败: {e}")

    def read_mcp_logs(self):
        """读取MCP进程日志"""
        if not self.mcp_process:
            return

        try:
            # 使用二进制模式读取
            while True:
                line = self.mcp_process.stdout.readline()
                if not line:
                    break

                # 尝试多种编码方式直到成功
                text = None
                for encoding in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        text = line.decode(encoding).strip()
                        break
                    except UnicodeDecodeError:
                        continue

                if text:
                    self.mcp_log_signal.emit(text)
                else:
                    # 如果所有编码都失败，使用十六进制表示
                    hex_text = ' '.join(f'{b:02x}' for b in line)
                    self.mcp_log_signal.emit(f"[Binary data]: {hex_text}")
        except Exception as e:
            self.mcp_log_signal.emit(f"读取MCP输出出错: {str(e)}")

        # 读取错误输出
        try:
            while True:
                line = self.mcp_process.stderr.readline()
                if not line:
                    break

                # 尝试多种编码方式直到成功
                text = None
                for encoding in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        text = line.decode(encoding).strip()
                        break
                    except UnicodeDecodeError:
                        continue

                if text:
                    self.mcp_log_signal.emit(f"ERROR: {text}")
                else:
                    # 如果所有编码都失败，使用十六进制表示
                    hex_text = ' '.join(f'{b:02x}' for b in line)
                    self.mcp_log_signal.emit(f"[Binary error data]: {hex_text}")
        except Exception as e:
            self.mcp_log_signal.emit(f"读取MCP错误输出出错: {str(e)}")

    def close_mcp(self):
        """关闭MCP服务器"""
        try:
            if self.mcp_process and self.mcp_process.poll() is None:
                self.mcp_process.terminate()
                self.mcp_process = None
        except Exception as e:
            print(f"关闭MCP进程失败: {e}")

    def close_live_2d(self):
        # 关闭桌宠进程
        if self.live2d_process and self.live2d_process.poll() is None:
            try:
                self.live2d_process.terminate()  # 先尝试优雅关闭
                self.live2d_process.wait(timeout=3)  # 等待3秒
            except subprocess.TimeoutExpired:
                self.live2d_process.kill()  # 强制关闭
            except Exception as e:
                print(f"关闭桌宠进程失败: {e}")

        # 也可以用进程名强制关闭（备用方案）
        try:
            subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq main_chat.py*\"", shell=True, check=False)
        except Exception as e:
            print(f"强制关闭python进程失败: {e}")

        # 关闭桌宠时也关闭MCP（如果在运行）
        try:
            if self.mcp_process and self.mcp_process.poll() is None:
                self.close_mcp()
        except Exception as e:
            print(f"关闭MCP失败: {e}")

        self.toast.show_message("桌宠已关闭", 1500)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = set_pyqt()
    w.show()
    sys.exit(app.exec_())
