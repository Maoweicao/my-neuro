# coding:utf-8
import json
import sys, os
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtCore import Qt, QRect, QUrl, QEvent, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPainter, QImage, QBrush, QColor, QFont, QDesktopServices, QPixmap
from PyQt5.QtWidgets import QApplication, QFrame, QStackedWidget, QHBoxLayout, QLabel, QSystemTrayIcon, QVBoxLayout, QGroupBox, QFormLayout, QWidget

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
            self.process = subprocess.Popen(
                self.bat_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                text=True,
                encoding='utf-8',  # Windows中文环境常用编码
                bufsize=1
            )
            
            # 实时读取输出
            while self.is_running:
                output = self.process.stdout.readline()
                if not output:
                    break
                # 打印带颜色的输出到控制台
                self.print_colored(output.strip())
                # 发送原始输出到UI
                self.output_signal.emit(output.strip())
            
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
                    self.create_setting_tab
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

        self.addSubInterface(self.MainInterface, FIF.HOME_FILL, '主菜单')
        self.addSubInterface(self.LLMInterface, FIF.ROBOT, 'LLM')
        self.addSubInterface(self.ASRInterface, FIF.HEADPHONE, 'ASR')
        self.addSubInterface(self.TTSInterface, FIF.MICROPHONE, 'TTS')
        self.addSubInterface(self.Live2dInterface, FIF.PEOPLE, 'Live 2D')
        self.addSubInterface(self.SubtitleInterface, FIF.FONT, '字幕')
        self.addSubInterface(self.UserInputInterface, FIF.SEND, '对话框')
        self.addSubInterface(self.OtherInterface, FIF.APPLICATION, '其他')

        # add navigation items to scroll area
        # for i in range(1, 21):
        #     self.navigationInterface.addItem(
        #         f'folder{i}',
        #         FIF.FOLDER,
        #         f'Folder {i}',
        #         lambda: print('Folder clicked'),
        #         position=NavigationItemPosition.SCROLL
        #     )

        # add custom widget to bottom
        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=AvatarWidget(),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM
        )

        self.addSubInterface(self.SettingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)

        #!IMPORTANT: don't forget to set the default route key
        qrouter.setDefaultRouteKey(self.stackWidget, self.MainInterface.objectName())

        # set the maximum width
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
