# coding:utf-8
import json
import sys, os
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtCore import Qt, QRect, QUrl, QEvent, QThread, pyqtSignal, QObject
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
    QSizePolicy
)

from qfluentwidgets import (NavigationInterface,NavigationItemPosition, NavigationWidget, MessageBox,
                            isDarkTheme, setTheme, Theme, qrouter)
from qfluentwidgets import FluentIcon as FIF, Action, SystemTrayMenu, LineEdit, DoubleSpinBox, SpinBox, CheckBox, ScrollArea, PrimaryToolButton, ToolButton, InfoBar, InfoBarPosition, PasswordLineEdit, TextBrowser, PixmapLabel
from qframelesswindow import FramelessWindow, TitleBar


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
                    "\"& {"
                    " $ErrorActionPreference='Continue';"
                    f" $base = '{base_dir}';"
                    " $run = Join-Path $base 'Run-MyNeuro.ps1';"
                    " $usedRun = $false;"
                    " if (Test-Path $run) { . $run; $usedRun = $true }"
                    " elseif (Test-Path (Join-Path $base '.venv\\Scripts\\Activate.ps1')) { . (Join-Path $base '.venv\\Scripts\\Activate.ps1') }"
                    " if ($usedRun -and $env:VIRTUAL_ENV) {"
                    "   Write-Host '解除上层VIRTUAL_ENV以优先使用my-neuro环境';"
                    "   $env:PATH = ($env:PATH -split ';' | Where-Object {$_ -notlike '*ai_live2d\\.venv*'}) -join ';';"
                    "   $env:VIRTUAL_ENV = $null;"
                    " }"
                    f"; Set-Location -Path '{bat_dir}';"
                    "; Write-Host '=== 环境检查 ===';"
                    "; Write-Host ('PWD: ' + (Get-Location).Path);"
                    "; Write-Host ('CONDA_DEFAULT_ENV: ' + ($env:CONDA_DEFAULT_ENV));"
                    "; Write-Host ('VIRTUAL_ENV: ' + ($env:VIRTUAL_ENV));"
                    "; Get-Command python -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('python cmd: ' + $_.Source) };"
                    "; & python -c 'import sys, importlib.util as u; print(\"python:\", sys.version); print(\"pip:\", \"ok\" if u.find_spec(\"pip\") else \"missing\"); print(\"py3langid:\", \"ok\" if u.find_spec(\"py3langid\") else \"missing\")';"
                    "; Write-Host '=== 启动脚本 ===';"
                    f" & '{bat_ps}'"
                    " }\""
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
        self.widgets = {}  # 存储所有控件引用
        self.setObjectName(text.replace(' ', '-'))

        self.tab_chose(num)()

    def tab_chose(self, num):
        """创建各个配置部分的标签页"""
        tab_list = [self.create_main_tab,
                    self.create_llm_tab,
                    self.create_asr_tab,
                    self.create_tts_tab,
                    self.create_ui_tab,
                    self.create_subtitle_tab,
                    self.create_user_input_tab,
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
                content="出现了错误哦",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self
            )
            return False
        
    def reload_config(self):
        """重新加载配置文件"""
        self.config_data = self.load_config()
        self.update_widgets()
        InfoBar.success(
                title='加载成功',
                content="已重新加载配置文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        
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

        # 确保日志处理器已设置
        if not self.log_handler:
            self.log_handler = QTextBrowserHandler(self.left_browser)
            logger = logging.getLogger()
            logger.addHandler(self.log_handler)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.log_handler.setFormatter(formatter)
        
        # 创建并启动工作线程
        self.bat_worker = BatWorker(r"start_project.bat")  # 替换为您的BAT路径
        self.bat_worker.output_signal.connect(self.append_output)
        self.bat_worker.finished_signal.connect(self.on_bat_finished)
        self.bat_worker.start()
        
        # 更新UI
        self.append_output("BAT脚本已启动...")
    
    def stop_bat(self):
        """停止BAT进程"""
        if self.bat_worker and self.bat_worker.isRunning():
            self.bat_worker.stop()
            self.append_output("正在停止BAT脚本...")

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
            elif isinstance(widget, CheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, SpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, DoubleSpinBox):
                widget.setValue(float(value))

    def collect_values(self):
        """收集所有控件的值到配置字典"""
        for key_path, widget_info in self.widgets.items():
            widget = widget_info["widget"]
            current_value = None
            
            if isinstance(widget, LineEdit):
                current_value = widget.text()
            elif isinstance(widget, CheckBox):
                current_value = widget.isChecked()
            elif isinstance(widget, SpinBox):
                current_value = widget.value()
            elif isinstance(widget, DoubleSpinBox):
                current_value = widget.value()
            
            # 更新配置数据
            keys = key_path.split('.')
            config_ptr = self.config_data
            for key in keys[:-1]:
                config_ptr = config_ptr.setdefault(key, {})
            config_ptr[keys[-1]] = current_value

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
        self.right_browser.setHtml("<p>欢迎使用，点击按钮即可打开终端(*´∀ ˋ*)。<br/>什么，你想问上图作者是谁(*ﾟ∀ﾟ*)？<br/>是<b>菊花茶洋参</b>大佬哦ξ( ✿＞◡❛)</p>")
        
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
        
        fields = [
            ("API Key", "llm.api_key", "passwordlineedit", ""),
            ("API URL", "llm.api_url", "lineedit", ""),
            ("模型", "llm.model", "lineedit", ""),
            ("启用限制", "llm.enable_limit", "checkbox", False),
            ("最大消息数", "llm.max_messages", "spinbox", 8),
            ("系统提示词", "llm.system_prompt", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "大语言模型配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_asr_tab(self):
        """创建ASR配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        fields = [
            ("VAD URL", "asr.vad_url", "lineedit", ""),
            ("ASR URL", "asr.asr_url", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "语音识别配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_tts_tab(self):
        """创建TTS配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        fields = [
            ("URL", "tts.url", "lineedit", ""),
            ("语言", "tts.language", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "语音合成配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_ui_tab(self):
        """创建UI配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        fields = [
            ("介绍文本", "ui.intro_text", "lineedit", ""),
            ("模型缩放", "ui.model_scale", "doublespin", 1.0),
            ("模型路径", "ui.model_path", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "UI配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_subtitle_tab(self):
        """创建字幕配置标签页"""
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        fields = [
            ("字体", "subtitle.font_family", "lineedit", ""),
            ("字体大小", "subtitle.font_size", "spinbox", 24),
            ("粗体", "subtitle.font_bold", "checkbox", False),
            ("文本框高度", "subtitle.box_height", "spinbox", 800),
            ("文本框宽度", "subtitle.box_width", "spinbox", 1800),
            ("文本颜色R", "subtitle.text_color_r", "spinbox", 255),
            ("文本颜色G", "subtitle.text_color_g", "spinbox", 255),
            ("文本颜色B", "subtitle.text_color_b", "spinbox", 255),
            ("文本颜色A", "subtitle.text_color_a", "spinbox", 255),
            ("轮廓颜色R", "subtitle.outline_color_r", "spinbox", 0),
            ("轮廓颜色G", "subtitle.outline_color_g", "spinbox", 0),
            ("轮廓颜色B", "subtitle.outline_color_b", "spinbox", 0),
            ("轮廓颜色A", "subtitle.outline_color_a", "spinbox", 200),
            ("背景颜色R", "subtitle.bg_color_r", "spinbox", 0),
            ("背景颜色G", "subtitle.bg_color_g", "spinbox", 0),
            ("背景颜色B", "subtitle.bg_color_b", "spinbox", 0),
            ("背景颜色A", "subtitle.bg_color_a", "spinbox", 60),
            ("内边距", "subtitle.padding", "spinbox", 20),
            ("边框半径", "subtitle.border_radius", "spinbox", 15),
            ("淡入淡出时间", "subtitle.fade_duration", "spinbox", 300),
            ("自动隐藏延迟", "subtitle.auto_hide_delay", "spinbox", 0),
            ("字符延迟", "subtitle.char_delay", "spinbox", 50)
        ]
        
        group = self.create_form_group(self, "字幕配置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_user_input_tab(self):
        self.startButton.hide()
        self.closeButton.hide()
        while self.vBoxLayout.count():
            item = self.vBoxLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        fields = [
            ("窗口宽度", "user_input.width", "spinbox", 400),
            ("窗口高度", "user_input.height", "spinbox", 150),
            ("字体", "user_input.font_family", "lineedit", "Microsoft YaHei"),
            ("字体大小", "user_input.font_size", "spinbox", 16),
            ("边框圆角", "user_input.border_radius", "spinbox", 10),
            
            # 背景颜色
            ("背景颜色R", "user_input.bg_color_r", "spinbox", 40),
            ("背景颜色G", "user_input.bg_color_g", "spinbox", 44),
            ("背景颜色B", "user_input.bg_color_b", "spinbox", 52),
            ("背景颜色A", "user_input.bg_color_a", "spinbox", 220),
            
            # 文字颜色
            ("文字颜色R", "user_input.text_color_r", "spinbox", 220),
            ("文字颜色G", "user_input.text_color_g", "spinbox", 220),
            ("文字颜色B", "user_input.text_color_b", "spinbox", 220),
            
            # 边框颜色
            ("边框颜色R", "user_input.border_color_r", "spinbox", 86),
            ("边框颜色G", "user_input.border_color_g", "spinbox", 182),
            ("边框颜色B", "user_input.border_color_b", "spinbox", 194),
            
            # 输入框背景颜色
            ("输入框背景R", "user_input.status_bg_color_r", "spinbox", 60),
            ("输入框背景G", "user_input.status_bg_color_g", "spinbox", 60),
            ("输入框背景B", "user_input.status_bg_color_b", "spinbox", 70),
            ("输入框背景A", "user_input.status_bg_color_a", "spinbox", 220),
        ]
        
        group = self.create_form_group(self, "对话框", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

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
        """创建MCP配置标签页"""
        fields = [
            ("MCP URL", "mcp.urls", "lineedit", ""),
            ("MCP Paths", "mcp.paths", "lineedit", "")
        ]
        
        group = self.create_form_group(self, "RAG配置", fields)
        self.vBoxLayout.addWidget(group)
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
            ("RAG开关", "setting.rag_enabled", "checkbox", True),
            ("MCP开关", "setting.mcp_enabled", "checkbox", True),
            ("视觉开关", "setting.vision_enabled", "checkbox", True),
            ("记忆开关", "setting.memory_enabled", "checkbox", True),
            ("主动对话开关", "setting.auto_chat_enabled", "checkbox", True),
            ("B站直播开关", "setting.bilibili_enabled", "checkbox", False),
        ]
        
        group = self.create_form_group(self, "项目设置", fields)
        self.vBoxLayout.addWidget(group)
        self.vBoxLayout.addStretch()

    def create_voice_clone_tab(self):
        """创建“声音克隆”页面：包含两个子选项卡
        1) TTS模型更换：选择模型.pth与参考音频.wav，角色名、语种与参考文本，生成配置/批处理
        2) 一键训练TTS模型：包装现有一键批处理，输出日志，可停止
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

        # Tab2: 一键训练
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)

        self.train_browser = TextBrowser(self)
        t2_btns = QHBoxLayout()
        self.train_start_btn = PrimaryToolButton(FIF.PLAY)
        self.train_start_btn.setText("开始训练")
        self.train_stop_btn = ToolButton(FIF.PAUSE)
        self.train_stop_btn.setText("停止")
        t2_btns.addWidget(self.train_start_btn)
        t2_btns.addWidget(self.train_stop_btn)
        t2_btns.addStretch(1)

        t2_layout.addLayout(t2_btns)
        t2_layout.addWidget(self.train_browser)

        tabs.addTab(tab2, "一键训练TTS模型")

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
                "echo 已写入配置: voice_clone_config.json",
                "if exist ..\\..\\一键克隆音色.bat (",
                "  call ..\\..\\一键克隆音色.bat",
                ") else (",
                "  echo 未找到一键克隆音色.bat，请手动处理",
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
        bat_path = os.path.abspath("一键克隆音色.bat")
        if not os.path.exists(bat_path):
            self.train_browser.append("未找到 一键克隆音色.bat，无法启动训练。")
            return
        self.train_worker = BatWorker(bat_path)
        self.train_worker.output_signal.connect(self.train_browser.append)
        self.train_worker.finished_signal.connect(lambda: self.train_browser.append("训练进程已结束"))
        self.train_worker.start()
        self.train_browser.append("已启动训练脚本…")

    def _stop_voice_train(self):
        if self.train_worker and self.train_worker.isRunning():
            self.train_worker.stop()
            self.train_browser.append("正在尝试停止训练脚本…")
        else:
            self.train_browser.append("没有运行中的训练脚本。")

class SystemTrayIcon(QSystemTrayIcon):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setIcon(parent.windowIcon())
        self.setToolTip('肥牛菜单')

        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addActions([
            Action('显示', triggered=self.show_menu),
            Action('设置'),
            Action('退出', triggered=self.exit_menu)
        ])
        self.setContextMenu(self.menu)

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

    def show_menu(self):
        self.parent().show()
        

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
                raw = self.proc.stdout.readline()
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
                self.line.emit(s.rstrip())
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
            'tts': os.path.join(base_dir, 'TTS.bat'),
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
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            bat_abs = os.path.abspath(bat)
            bat_dir = os.path.dirname(bat_abs)
            # PowerShell 单引号内转义
            base_ps = base_dir.replace("'", "''")
            batdir_ps = bat_dir.replace("'", "''")
            bat_ps = bat_abs.replace("'", "''")
            # 使用 PowerShell，优先点源 Run-MyNeuro.ps1（自动 conda/.venv），否则尝试激活 .venv
            ps_cmd = (
                "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                "\"& {"
                " $ErrorActionPreference='Continue';"
                f" $base = '{base_ps}';"
                " $run = Join-Path $base 'Run-MyNeuro.ps1';"
                " $usedRun = $false;"
                " if (Test-Path $run) { . $run; $usedRun = $true }"
                " elseif (Test-Path (Join-Path $base '.venv\\Scripts\\Activate.ps1')) { . (Join-Path $base '.venv\\Scripts\\Activate.ps1') }"
                " if ($usedRun -and $env:VIRTUAL_ENV) {"
                "   Write-Host '解除上层VIRTUAL_ENV以优先使用my-neuro环境';"
                "   $env:PATH = ($env:PATH -split ';' | Where-Object {$_ -notlike '*ai_live2d\\.venv*'}) -join ';';"
                "   $env:VIRTUAL_ENV = $null;"
                " }"
                f"; Set-Location -Path '{batdir_ps}';"
                "; Write-Host '=== 环境检查 ===';"
                "; Write-Host ('PWD: ' + (Get-Location).Path);"
                "; Write-Host ('CONDA_DEFAULT_ENV: ' + ($env:CONDA_DEFAULT_ENV));"
                "; Write-Host ('VIRTUAL_ENV: ' + ($env:VIRTUAL_ENV));"
                "; Get-Command python -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('python cmd: ' + $_.Source) };"
                "; & python -c 'import sys, importlib.util as u; print(\"python:\", sys.version); print(\"pip:\", \"ok\" if u.find_spec(\"pip\") else \"missing\"); print(\"py3langid:\", \"ok\" if u.find_spec(\"py3langid\") else \"missing\")';"
                "; Write-Host '=== 启动脚本 ===';"
                f" & '{bat_ps}'"
                " }\""
            )
            wrapped = f"chcp 65001 >NUL & {ps_cmd}"
            proc = subprocess.Popen(
                wrapped,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                bufsize=0,
                cwd=bat_dir
            )
            self.processes[key] = proc
            reader = StreamReader(proc)
            self.readers[key] = reader
            reader.line.connect(lambda s, k=key: self._append(k, s))
            reader.finished.connect(lambda k=key: self._on_finished(k))
            reader.start()
            self._update_status(key, True)
            self._append(key, '启动中…')
        except Exception as e:
            self._append(key, f'启动失败：{e}')

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

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(18, 18))


class Window(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.setTitleBar(CustomTitleBar(self))

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
        self.OtherInterface = Widget('Others', 7, parent=self)
        self.SettingInterface = Widget('Setting', 8, parent=self)
        self.VoiceCloneInterface = Widget('VoiceClone', 9, parent=self)
        self.TerminalInterface = TerminalRoom(self)


        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()

        # 系统托盘
        self.systemTrayIcon = SystemTrayIcon(self)
        self.systemTrayIcon.show()

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
        event.ignore()
        self.hide()


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()
