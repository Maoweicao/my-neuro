# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLineEdit, QMenu, QAction
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


class AIWorker(QThread):
    """AI处理线程"""
    finished = pyqtSignal()

    def __init__(self, user_input, ai_module):
        super().__init__()
        self.user_input = user_input
        self.ai_module = ai_module

    def run(self):
        try:
            self.ai_module.process_user_input(self.user_input)
        except Exception as e:
            print(f"AI处理错误: {e}")
        finally:
            self.finished.emit()


class SearchBox(QWidget):
    def __init__(self, ai_module=None):
        super().__init__()
        self.drag_position = None
        self.ai_module = ai_module  # 接收AI模块
        self.ai_worker = None
        self.init_ui()

    def init_ui(self):
        # 获取屏幕信息进行自适应
        app = QApplication.instance()
        screen = app.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # 获取DPI缩放比例
        dpi_ratio = screen.logicalDotsPerInch() / 96.0

        # 计算自适应尺寸
        adaptive_width = min(int(screen_width * 0.25), 400)
        adaptive_height = max(int(65 * dpi_ratio), 60)

        # 设置窗口
        self.setWindowTitle('AI搜索')
        self.setFixedSize(adaptive_width, adaptive_height)

        # 修改窗口标志，确保窗口可见
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        # 智能定位：右下角位置
        margin = 20  # 距离屏幕边缘的间距
        bottom_right_x = screen_geometry.x() + screen_width - adaptive_width - margin
        bottom_right_y = screen_geometry.y() + screen_height - adaptive_height - margin
        self.move(bottom_right_x, bottom_right_y)

        print(f"窗口位置: ({bottom_right_x}, {bottom_right_y})")
        print(f"窗口大小: {adaptive_width} x {adaptive_height}")
        print(f"屏幕信息: {screen_width} x {screen_height}")

        # 现代化深色主题样式
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 20px;
            }
        """)

        # 创建水平布局
        layout = QHBoxLayout()
        margin = max(int(12 * dpi_ratio), 10)
        layout.setContentsMargins(margin, margin, margin, margin)

        # 创建搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('🔍 输入你的问题...')
        self.search_input.setAlignment(Qt.AlignVCenter)

        # 字体设置
        base_font_size = max(int(12 * dpi_ratio), 10)
        font = QFont('Microsoft YaHei', base_font_size)
        self.search_input.setFont(font)

        # 输入框高度
        input_height = max(int(40 * dpi_ratio), 35)
        self.search_input.setFixedHeight(input_height)

        self.search_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_input.customContextMenuRequested.connect(self.show_context_menu)

        # 现代化输入框样式
        padding = max(int(8 * dpi_ratio), 6)
        border_radius = max(int(15 * dpi_ratio), 12)

        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: {border_radius}px;
                padding: {padding}px 15px;
                font-size: {base_font_size}px;
                color: #ffffff;
                selection-background-color: #0078d4;
            }}
            QLineEdit:focus {{
                border: 2px solid #0078d4;
                background-color: #404040;
            }}
            QLineEdit:hover {{
                border: 2px solid #666666;
                background-color: #404040;
            }}
        """)

        # 连接信号
        self.search_input.returnPressed.connect(self.on_search)

        # 添加组件到布局
        layout.addWidget(self.search_input)
        self.setLayout(layout)

    def showEvent(self, event):
        """窗口显示时的事件处理"""
        super().showEvent(event)
        # 确保窗口获得焦点
        self.activateWindow()
        self.raise_()
        self.search_input.setFocus()
        print("窗口已显示并获得焦点")

    def on_search(self):
        user_input = self.search_input.text()
        if user_input.strip():
            print(f'你：{user_input}')
            self.search_input.clear()

            if self.ai_module:
                # 如果有AI线程在运行，先停止
                if self.ai_worker and self.ai_worker.isRunning():
                    self.ai_worker.terminate()
                    self.ai_worker.wait()

                # 创建新的AI线程
                self.ai_worker = AIWorker(user_input, self.ai_module)
                self.ai_worker.finished.connect(self.on_ai_finished)
                self.ai_worker.start()
            else:
                print("AI模块未连接")
        else:
            self.search_input.setPlaceholderText('💭 请输入内容...')

    def on_ai_finished(self):
        """AI处理完成"""
        pass  # 可以在这里添加完成后的操作

    def show_context_menu(self, position):
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 5px;
                color: #ffffff;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
        """)

        exit_action = QAction('🚪 退出', self)
        exit_action.triggered.connect(self.close_application)
        context_menu.addAction(exit_action)

        context_menu.exec_(self.search_input.mapToGlobal(position))

    def close_application(self):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()


def create_search_app(ai_module=None):
    """创建搜索应用，供ai_chat.py调用"""
    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = SearchBox(ai_module)
    window.show()

    # 确保窗口在所有桌面上都可见
    window.activateWindow()
    window.raise_()

    return app, window


def start_gui_with_ai(ai_function=None):
    """启动GUI并绑定指定的AI函数"""
    if ai_function is None:
        # 如果没有指定函数，就尝试找调用者模块的process_user_input
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_module = inspect.getmodule(caller_frame)
        ai_function = getattr(caller_module, 'process_user_input', None)

    # 创建一个包装模块，让原来的代码能工作
    class AIWrapper:
        def __init__(self, func):
            self.original_func = func

        def process_user_input(self, user_text):
            # 检查函数需要几个参数
            import inspect
            sig = inspect.signature(self.original_func)
            if len(sig.parameters) == 0:
                # 无参数函数，直接调用
                self.original_func()
            else:
                # 有参数函数，传入用户输入
                self.original_func(user_text)

    wrapper = AIWrapper(ai_function) if ai_function else None
    app, window = create_search_app(wrapper)
    return app.exec_()


if __name__ == '__main__':
    # 如果直接运行这个文件，不导入ai_chat避免循环导入
    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = SearchBox(None)
    window.show()

    # 调试信息
    print("应用程序启动完成")
    print(f"可用屏幕数量: {len(app.screens())}")
    for i, screen in enumerate(app.screens()):
        print(f"屏幕 {i}: {screen.geometry()}")

    sys.exit(app.exec_())
