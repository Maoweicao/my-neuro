# coding:utf-8
import json
import sys, os
import subprocess
import logging
import warnings
from logging.handlers import RotatingFileHandler

# 抑制SIP相关的弃用警告，这是PyQt5版本兼容性问题
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*sipPyTypeDict.*")
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
    QColorDialog
)

from qfluentwidgets import (NavigationInterface,NavigationItemPosition, NavigationWidget, MessageBox,
                            isDarkTheme, setTheme, Theme, qrouter)
from qfluentwidgets import FluentIcon as FIF, Action, SystemTrayMenu, LineEdit, DoubleSpinBox, SpinBox, CheckBox, ScrollArea, PrimaryToolButton, ToolButton, InfoBar, InfoBarPosition, PasswordLineEdit, TextBrowser, PixmapLabel, PushButton, ColorDialog
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


class MCPToolManager(QWidget):
    """MCP工具管理器 - 支持增删改查MCP工具配置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.mcp_tools = []
        self.setup_ui()
        self.load_mcp_config()
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # 左侧：工具列表和操作按钮
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 工具列表
        self.tool_list = QListWidget()
        self.tool_list.itemClicked.connect(self.on_tool_selected)
        left_layout.addWidget(QLabel("MCP工具列表:"))
        left_layout.addWidget(self.tool_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = PushButton("添加", self)
        self.edit_btn = PushButton("编辑", self)
        self.delete_btn = PushButton("删除", self)
        self.test_btn = PushButton("测试连接", self)
        
        self.add_btn.clicked.connect(self.add_tool)
        self.edit_btn.clicked.connect(self.edit_tool)
        self.delete_btn.clicked.connect(self.delete_tool)
        self.test_btn.clicked.connect(self.test_tool)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.test_btn)
        left_layout.addLayout(btn_layout)
        
        # 右侧：详细配置
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 配置表单
        form_group = QGroupBox("MCP工具配置")
        form_layout = QFormLayout(form_group)
        
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("工具名称")
        form_layout.addRow("名称:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["server", "client", "middleware"])
        form_layout.addRow("类型:", self.type_combo)
        
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("ws://localhost:3000/mcp 或 http://api.example.com")
        form_layout.addRow("URL:", self.url_edit)
        
        self.path_edit = LineEdit()
        self.path_edit.setPlaceholderText("本地路径或执行命令")
        form_layout.addRow("路径/命令:", self.path_edit)
        
        self.enabled_check = CheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("启用:", self.enabled_check)
        
        self.args_edit = QTextEdit()
        self.args_edit.setPlaceholderText('{"arg1": "value1", "arg2": "value2"}')
        self.args_edit.setMaximumHeight(80)
        form_layout.addRow("参数(JSON):", self.args_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("工具描述...")
        self.description_edit.setMaximumHeight(60)
        form_layout.addRow("描述:", self.description_edit)
        
        right_layout.addWidget(form_group)
        
        # 保存按钮
        save_btn = PrimaryToolButton(FIF.SAVE)
        save_btn.setText("保存配置")
        save_btn.clicked.connect(self.save_current_tool)
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
    
    def load_mcp_config(self):
        """从父组件的配置中加载MCP工具列表，兼容传统格式"""
        if hasattr(self.parent_widget, 'config_data'):
            mcp_config = self.parent_widget.config_data.get('mcp', {})
            
            # 新格式：直接使用tools数组
            if 'tools' in mcp_config:
                self.mcp_tools = mcp_config.get('tools', [])
            else:
                # 传统格式：从urls和paths转换
                self.mcp_tools = []
                
                # 处理URLs
                urls = mcp_config.get('urls', [])
                if isinstance(urls, str):
                    urls = [url.strip() for url in urls.split(',') if url.strip()]
                elif not isinstance(urls, list):
                    urls = []
                
                for i, url in enumerate(urls):
                    if url.strip():
                        tool = {
                            'name': f'URL工具{i+1}',
                            'type': 'server',
                            'url': url.strip(),
                            'path': '',
                            'enabled': True,
                            'args': {},
                            'description': f'从配置文件导入的URL: {url.strip()}'
                        }
                        self.mcp_tools.append(tool)
                
                # 处理Paths
                paths = mcp_config.get('paths', [])
                if isinstance(paths, str):
                    paths = [path.strip() for path in paths.split(',') if path.strip()]
                elif not isinstance(paths, list):
                    paths = []
                
                for i, path in enumerate(paths):
                    if path.strip():
                        tool = {
                            'name': f'路径工具{i+1}',
                            'type': 'server',
                            'url': '',
                            'path': path.strip(),
                            'enabled': True,
                            'args': {},
                            'description': f'从配置文件导入的路径: {path.strip()}'
                        }
                        self.mcp_tools.append(tool)
                
                # 自动保存转换后的格式到配置中
                if self.mcp_tools:
                    self.save_to_parent_config()
        
        self.refresh_tool_list()
    
    def refresh_tool_list(self):
        """刷新工具列表显示"""
        self.tool_list.clear()
        for i, tool in enumerate(self.mcp_tools):
            item_text = f"{tool.get('name', f'工具{i+1}')} ({'✓' if tool.get('enabled', True) else '✗'})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)  # 存储索引
            self.tool_list.addItem(item)
    
    def on_tool_selected(self, item):
        """工具选中事件"""
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self.mcp_tools):
            tool = self.mcp_tools[index]
            self.load_tool_to_form(tool)
        self.update_buttons()
    
    def load_tool_to_form(self, tool):
        """将工具配置加载到表单"""
        self.name_edit.setText(tool.get('name', ''))
        
        tool_type = tool.get('type', 'server')
        index = self.type_combo.findText(tool_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        self.url_edit.setText(tool.get('url', ''))
        self.path_edit.setText(tool.get('path', ''))
        self.enabled_check.setChecked(tool.get('enabled', True))
        
        args = tool.get('args', {})
        if isinstance(args, dict):
            self.args_edit.setPlainText(json.dumps(args, indent=2, ensure_ascii=False))
        else:
            self.args_edit.setPlainText(str(args))
        
        self.description_edit.setPlainText(tool.get('description', ''))
    
    def clear_form(self):
        """清空表单"""
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.url_edit.clear()
        self.path_edit.clear()
        self.enabled_check.setChecked(True)
        self.args_edit.clear()
        self.description_edit.clear()
    
    def get_form_data(self):
        """从表单获取数据"""
        try:
            args_text = self.args_edit.toPlainText().strip()
            args = json.loads(args_text) if args_text else {}
        except json.JSONDecodeError:
            args = {}
        
        return {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'url': self.url_edit.text().strip(),
            'path': self.path_edit.text().strip(),
            'enabled': self.enabled_check.isChecked(),
            'args': args,
            'description': self.description_edit.toPlainText().strip()
        }
    
    def add_tool(self):
        """添加新工具"""
        self.clear_form()
        self.name_edit.setFocus()
        self.update_buttons()
    
    def edit_tool(self):
        """编辑当前选中的工具"""
        current_item = self.tool_list.currentItem()
        if current_item:
            index = current_item.data(Qt.UserRole)
            if 0 <= index < len(self.mcp_tools):
                self.load_tool_to_form(self.mcp_tools[index])
    
    def delete_tool(self):
        """删除当前选中的工具"""
        current_item = self.tool_list.currentItem()
        if not current_item:
            return
        
        index = current_item.data(Qt.UserRole)
        if 0 <= index < len(self.mcp_tools):
            tool_name = self.mcp_tools[index].get('name', f'工具{index+1}')
            reply = QMessageBox.question(
                self, '确认删除', 
                f'确定要删除工具 "{tool_name}" 吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.mcp_tools[index]
                self.refresh_tool_list()
                self.clear_form()
                self.update_buttons()
                self.save_to_parent_config()
    
    def save_current_tool(self):
        """保存当前表单中的工具配置"""
        tool_data = self.get_form_data()
        
        if not tool_data['name']:
            InfoBar.warning(
                title='保存失败',
                content="请输入工具名称",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        current_item = self.tool_list.currentItem()
        if current_item:
            # 编辑现有工具
            index = current_item.data(Qt.UserRole)
            if 0 <= index < len(self.mcp_tools):
                self.mcp_tools[index] = tool_data
        else:
            # 添加新工具
            self.mcp_tools.append(tool_data)
        
        self.refresh_tool_list()
        self.save_to_parent_config()
        
        InfoBar.success(
            title='保存成功',
            content=f"工具 '{tool_data['name']}' 已保存",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def test_tool(self):
        """测试工具连接"""
        current_item = self.tool_list.currentItem()
        if not current_item:
            InfoBar.warning(
                title='测试失败',
                content="请先选择一个工具",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        index = current_item.data(Qt.UserRole)
        if 0 <= index < len(self.mcp_tools):
            tool = self.mcp_tools[index]
            url = tool.get('url', '')
            path = tool.get('path', '')
            
            if url:
                # 简单的URL测试（可以扩展为实际的MCP连接测试）
                try:
                    import requests
                    response = requests.get(url, timeout=5)
                    InfoBar.success(
                        title='连接成功',
                        content=f"URL {url} 响应状态: {response.status_code}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                except Exception as e:
                    InfoBar.error(
                        title='连接失败',
                        content=f"无法连接到 {url}: {str(e)}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
            elif path:
                # 路径或命令测试
                if os.path.exists(path):
                    InfoBar.success(
                        title='路径有效',
                        content=f"路径 {path} 存在",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    InfoBar.warning(
                        title='路径无效',
                        content=f"路径 {path} 不存在",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
            else:
                InfoBar.warning(
                    title='无法测试',
                    content="工具未配置URL或路径",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def update_buttons(self):
        """更新按钮状态"""
        has_selection = self.tool_list.currentItem() is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.test_btn.setEnabled(has_selection)
    
    def save_to_parent_config(self):
        """保存到父组件的配置中"""
        if hasattr(self.parent_widget, 'config_data'):
            if 'mcp' not in self.parent_widget.config_data:
                self.parent_widget.config_data['mcp'] = {}
            self.parent_widget.config_data['mcp']['tools'] = self.mcp_tools
    
    def get_tools_config(self):
        """获取工具配置，供外部调用，同时保持向后兼容"""
        # 生成URLs和Paths列表（向后兼容）
        urls = []
        paths = []
        
        for tool in self.mcp_tools:
            if tool.get('enabled', True):
                if tool.get('url'):
                    urls.append(tool['url'])
                if tool.get('path'):
                    paths.append(tool['path'])
        
        return {
            'tools': self.mcp_tools,  # 新格式
            'urls': urls,             # 传统格式兼容
            'paths': paths            # 传统格式兼容
        }


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

        # 初始化LLM交互日志记录器
        self.init_llm_logger()

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
        
    def reload_config(self):
        """重新加载配置文件"""
        self.config_data = self.load_config()
        self.update_widgets()
        
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
                current_value = widget.currentData() if widget.currentData() is not None else widget.currentText()
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
        self.vBoxLayout.addStretch()

    def _scan_model_roots(self):
        """返回可能的模型根目录列表，优先 models/2d，再回退 live-2d/2D 与 ai_live2d/2D"""
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        return [
            os.path.join(proj_root, 'models', '2d'),
            os.path.join(proj_root, 'live-2d', '2D'),
            os.path.join(os.path.dirname(__file__), '2D'),
        ]

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
                        display = parts[0] if len(parts) >= 2 else os.path.basename(os.path.dirname(full))
                        key = (display, full)
                        if display and key not in added:
                            self.model_combo.addItem(display, full)
                            added.add(key)

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
        """创建MCP配置标签页 - 使用高级MCP工具管理器"""
        # 创建MCP工具管理器
        self.mcp_manager = MCPToolManager(self)
        self.vBoxLayout.addWidget(self.mcp_manager)
        
        # 传统的简单配置（保留兼容性）
        simple_group = QGroupBox("传统配置（兼容）")
        simple_form = QFormLayout(simple_group)
        
        # 读取配置
        mcp_config = self.config_data.get('mcp', {})
        
        # MCP URLs (多个URL用逗号分隔)
        urls_edit = LineEdit()
        urls_value = mcp_config.get('urls', '')
        if isinstance(urls_value, list):
            urls_value = ', '.join(urls_value)
        urls_edit.setText(str(urls_value))
        self.widgets['mcp.urls'] = {"widget": urls_edit, "type": "lineedit"}
        simple_form.addRow("MCP URLs (逗号分隔):", urls_edit)
        
        # MCP Paths (多个路径用逗号分隔)
        paths_edit = LineEdit()
        paths_value = mcp_config.get('paths', '')
        if isinstance(paths_value, list):
            paths_value = ', '.join(paths_value)
        paths_edit.setText(str(paths_value))
        self.widgets['mcp.paths'] = {"widget": paths_edit, "type": "lineedit"}
        simple_form.addRow("MCP Paths (逗号分隔):", paths_edit)
        
        # 全局开关
        enabled_check = CheckBox()
        enabled_check.setChecked(bool(mcp_config.get('enabled', True)))
        self.widgets['mcp.enabled'] = {"widget": enabled_check, "type": "checkbox"}
        simple_form.addRow("启用MCP:", enabled_check)
        
        self.vBoxLayout.addWidget(simple_group)
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
            clear_icon = getattr(FIF, 'CLOSE', FIF.STOP)
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

class SystemTrayIcon(QSystemTrayIcon):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setIcon(parent.windowIcon())
        self.setToolTip('肥牛菜单')

        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addActions([
            Action('显示', triggered=self.restore_window),
            Action('设置'),
            Action('退出', triggered=self.exit_menu)
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
                " # skip VIRTUAL_ENV PATH adjustment to avoid brace complexity"
                f"; Set-Location -Path '{batdir_ps}';"
                "; Write-Host '=== 环境检查 ===';"
                "; Write-Host ('PWD: ' + (Get-Location).Path);"
                "; Write-Host ('CONDA_DEFAULT_ENV: ' + ($env:CONDA_DEFAULT_ENV));"
                "; Write-Host ('VIRTUAL_ENV: ' + ($env:VIRTUAL_ENV));"
                "; $pcmd = (Get-Command python -ErrorAction SilentlyContinue); if ($pcmd) { Write-Host ('python cmd: ' + $pcmd.Source) } ;"
                "; # skip inline python checks to avoid quoting issues"
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

    def changeEvent(self, e):
        super().changeEvent(e)
        # 点击最小化按钮时，隐藏到托盘
        if e.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                if self.systemTrayIcon:
                    self.systemTrayIcon.showMessage('提示', '程序已最小化到托盘', QSystemTrayIcon.Information, 2000)


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()
