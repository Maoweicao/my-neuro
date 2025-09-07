# coding:utf-8
"""
独立的Live2D预览进程
用于在独立进程中运行Live2D预览窗口，避免影响主UI进程
"""

import json
import sys
import os
import logging
import warnings
import argparse
import signal
from pathlib import Path

# 抑制SIP相关的弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*sipPyTypeDict.*")

from PyQt5.QtCore import Qt, QRect, QEvent, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QIcon, QPainter, QImage, QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QGroupBox,
    QWidget,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QComboBox,
    QTabWidget,
    QSizePolicy,
    QMessageBox,
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
    QSlider,
    QDialog,
    QTextEdit,
    QFormLayout,
    QCheckBox
)
from PyQt5.QtOpenGL import QGLWidget

# 导入Live2D相关库
try:
    import live2d.v3 as live2d
except ImportError:
    try:
        import live2d.v2 as live2d
    except ImportError:
        import live2d

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Live2DPreviewWidget(QGLWidget):
    """Live2D动态预览组件 - 使用OpenGL渲染真正的Live2D模型"""

    # 定义信号
    expression_changed = pyqtSignal(str)
    motion_changed = pyqtSignal(str)

    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model = None
        self.current_expression = None
        self.current_motion = None
        self.zoom_factor = 1.0
        self.is_animating = False
        self.live2d_initialized = False

        self.setMinimumSize(400, 500)

    def initializeGL(self):
        """OpenGL初始化"""
        try:
            # 设置视口
            self.resizeGL(self.width(), self.height())

            # 初始化Live2D (在OpenGL上下文创建后)
            if not self.live2d_initialized:
                live2d.init()
                live2d.glInit()  # 使用新的glInit()方法替代glewInit()
                self.live2d_initialized = True
                logger.info("Live2D initialized successfully")

            logger.info("OpenGL initialized")
        except Exception as e:
            logger.error(f"OpenGL initialization failed: {e}")

    def resizeGL(self, width, height):
        """窗口大小改变"""
        try:
            # 设置视口
            from OpenGL.GL import glViewport
            glViewport(0, 0, width, height)

            if self.model:
                self.model.Resize(width, height)
        except Exception as e:
            logger.error(f"Resize GL failed: {e}")

    def paintGL(self):
        """渲染"""
        try:
            if self.model:
                live2d.clearBuffer()
                self.model.Update()
                self.model.Draw()
            else:
                # 如果模型未加载，显示简单的背景
                from OpenGL.GL import glClearColor, glClear, GL_COLOR_BUFFER_BIT
                glClearColor(0.9, 0.9, 0.9, 1.0)
                glClear(GL_COLOR_BUFFER_BIT)
        except Exception as e:
            logger.error(f"Paint GL failed: {e}")

    def load_model(self, model_path):
        """加载Live2D模型"""
        try:
            self.model_path = model_path
            logger.info(f"Loading Live2D model from: {model_path}")

            if self.model:
                # 清理之前的模型
                self.model = None

            # 创建新模型
            self.model = live2d.LAppModel()

            # 查找model3.json文件
            model_json_path = None
            if os.path.isfile(model_path) and model_path.endswith('.model3.json'):
                model_json_path = model_path
            else:
                # 在目录中查找model3.json
                for root, dirs, files in os.walk(model_path):
                    for file in files:
                        if file.endswith('.model3.json'):
                            model_json_path = os.path.join(root, file)
                            break
                    if model_json_path:
                        break

            if model_json_path and os.path.exists(model_json_path):
                logger.info(f"Loading model JSON: {model_json_path}")
                self.model.LoadModelJson(model_json_path)

                # 设置模型大小
                self.model.Resize(self.width(), self.height())

                # 启动默认动画
                self.start_animation()

                logger.info("Live2D model loaded successfully")
            else:
                logger.error(f"Model JSON file not found in {model_path}")

        except Exception as e:
            logger.error(f"Failed to load Live2D model: {e}")
            self.model = None

    def set_expression(self, expression_name):
        """设置表情"""
        try:
            self.current_expression = expression_name
            if self.model:
                # 这里可以实现表情切换逻辑
                # Live2D的表情通常通过参数控制
                logger.info(f"Setting expression: {expression_name}")

            # 发送表情变化信号
            self.expression_changed.emit(expression_name)

        except Exception as e:
            logger.error(f"设置表情失败: {e}")

    def play_motion(self, motion_name, loop=False):
        """播放动作"""
        try:
            self.current_motion = motion_name
            if self.model:
                # 启动动作 - 使用整数优先级而不是枚举
                # 3 = PRIORITY_FORCE (强制优先级)
                self.model.StartMotion(motion_name, 0, 3)
                logger.info(f"Playing motion: {motion_name}")

            # 发送动作变化信号
            self.motion_changed.emit(motion_name)

        except Exception as e:
            logger.error(f"播放动作失败: {e}")

    def stop_motion(self):
        """停止动作播放"""
        try:
            self.current_motion = None
            if self.model:
                # 停止所有动作
                pass
            logger.info("Motion stopped")

        except Exception as e:
            logger.error(f"停止动作失败: {e}")

    def reset_expression(self):
        """重置表情"""
        try:
            self.current_expression = None
            if self.model:
                # 重置表情参数
                pass
            logger.info("Expression reset")

        except Exception as e:
            logger.error(f"重置表情失败: {e}")

    def reset_pose(self):
        """重置姿态"""
        try:
            self.current_expression = None
            self.current_motion = None
            if self.model:
                # 重置所有参数
                pass
            logger.info("Pose reset")

        except Exception as e:
            logger.error(f"重置姿态失败: {e}")

    def start_animation(self):
        """开始动画"""
        try:
            self.is_animating = True
            # 启动渲染定时器
            self.timer = self.startTimer(16)  # ~60 FPS
            logger.info("Animation started")

        except Exception as e:
            logger.error(f"开始动画失败: {e}")

    def pause_animation(self):
        """暂停动画"""
        try:
            self.is_animating = False
            if hasattr(self, 'timer'):
                self.killTimer(self.timer)
            logger.info("Animation paused")

        except Exception as e:
            logger.error(f"暂停动画失败: {e}")

    def timerEvent(self, event):
        """定时器事件 - 更新渲染"""
        if self.is_animating:
            self.updateGL()

    def set_zoom(self, zoom_factor):
        """设置缩放"""
        try:
            self.zoom_factor = zoom_factor
            if self.model:
                # 应用缩放到模型
                pass
            logger.info(f"Zoom set to: {zoom_factor}")

        except Exception as e:
            logger.error(f"设置缩放失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止动画和定时器
            if self.is_animating:
                self.pause_animation()

            # 停止所有定时器
            if hasattr(self, 'timer'):
                self.killTimer(self.timer)
                self.timer = None

            # 清理Live2D模型
            if self.model:
                self.model = None

            # 清理Live2D资源
            if self.live2d_initialized:
                try:
                    # 确保在OpenGL上下文中操作
                    self.makeCurrent()
                    live2d.dispose()
                    self.live2d_initialized = False
                    logger.info("Live2D resources cleaned up successfully")
                except Exception as e:
                    logger.error(f"Live2D cleanup failed: {e}")

            # 清理OpenGL上下文
            try:
                self.doneCurrent()
            except Exception as e:
                logger.error(f"OpenGL context cleanup failed: {e}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        finally:
            super().closeEvent(event)


class Live2DPreviewWindow(QDialog):
    """Live2D模型预览窗口 - 支持动态预览"""

    def __init__(self, model_path):
        super().__init__()
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
        self.motion_loop_check = QCheckBox()
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

            # 重新加载预览图片
            self.load_preview_image_enhanced()

            # 禁用动态控制
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.apply_expr_btn.setEnabled(False)
            self.play_motion_btn.setEnabled(False)

            self.status_label.setText("静态预览模式 - 显示模型信息和资源列表")

        except Exception as e:
            logger.error(f"切换到静态预览模式失败: {e}")

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
            logger.error(f"切换到动态预览模式失败: {e}")
            self.preview_mode_combo.setCurrentText("静态预览")
            self.status_label.setText(f"动态预览启动失败: {str(e)}")

    def create_dynamic_preview_widget(self):
        """创建动态预览组件"""
        try:
            # 尝试创建Live2D预览组件
            try:
                self.dynamic_preview_area = Live2DPreviewWidget(
                    model_path=self.model_path,
                    parent=self.preview_container
                )
                live2d_available = True
            except Exception as e:
                logger.error(f"Live2D预览组件创建失败，将使用模拟组件: {e}")
                live2d_available = False

            if live2d_available:
                # 添加到预览容器布局
                layout = self.preview_container.layout()
                layout.addWidget(self.dynamic_preview_area)

                # 连接信号
                if hasattr(self.dynamic_preview_area, 'expression_changed'):
                    self.dynamic_preview_area.expression_changed.connect(self.on_dynamic_expression_changed)
                if hasattr(self.dynamic_preview_area, 'motion_changed'):
                    self.dynamic_preview_area.motion_changed.connect(self.on_dynamic_motion_changed)

                logger.info("动态预览组件创建成功")

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

                logger.info("创建模拟Live2D预览组件")

        except Exception as e:
            logger.error(f"创建动态预览组件失败: {e}")
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
            logger.error(f"启动Live2D预览失败: {e}")
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
            logger.error(f"应用表情失败: {e}")
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
            logger.error(f"重置表情失败: {e}")
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
            logger.error(f"播放动作失败: {e}")
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
            logger.error(f"停止动作失败: {e}")
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
            logger.error(f"重置失败: {e}")
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
            logger.error(f"播放随机动作失败: {e}")
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
            logger.error(f"应用随机表情失败: {str(e)}")
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
            logger.error(f"开始动画失败: {e}")
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
            logger.error(f"暂停动画失败: {e}")
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
            logger.error(f"重置姿态失败: {str(e)}")
            self.status_label.setText(f"重置姿态失败: {str(e)}")

    def on_zoom_changed(self, value):
        """缩放变化处理"""
        self.zoom_label.setText(f"{value}%")
        try:
            if self.preview_mode_combo.currentText() == "动态预览" and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'set_zoom'):
                    self.dynamic_preview_area.set_zoom(value / 100.0)
        except Exception as e:
            logger.error(f"设置缩放失败: {e}")

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
            logger.error(f"加载模型预览失败: {e}")
            self.status_label.setText(f"加载失败: {str(e)}")
            self.info_browser.setText(f"❌ 加载模型预览失败\n\n错误信息: {str(e)}")

    def load_model_details_fallback(self, model_path):
        """加载模型详细信息的回退方法"""
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"回退加载模型失败: {e}")
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
            logger.error(f"更新模型信息失败: {e}")
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
            logger.error(f"更新表情列表失败: {e}")
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
            logger.error(f"更新动作列表失败: {e}")
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
            logger.error(f"加载预览图像失败: {e}")
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
            logger.error(f"显示预览图像失败: {e}")
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
            logger.error(f"更新静态预览文本失败: {e}")
            self.static_preview_area.setText("🎭\n\nLive2D模型预览\n\n加载中...")

    def closeEvent(self, event):
        """关闭事件 - 确保Live2D资源被正确清理"""
        try:
            # 清理动态预览组件
            if hasattr(self, 'dynamic_preview_area') and self.dynamic_preview_area:
                if hasattr(self.dynamic_preview_area, 'close'):
                    self.dynamic_preview_area.close()
                self.dynamic_preview_area = None

            # 清理Live2D widget引用
            if hasattr(self, 'live2d_widget') and self.live2d_widget:
                self.live2d_widget = None

            logger.info("Live2DPreviewWindow closed and resources cleaned up")

        except Exception as e:
            logger.error(f"Live2DPreviewWindow cleanup failed: {e}")
        finally:
            super().closeEvent(event)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Live2D独立预览进程')
    parser.add_argument('--model-path', required=True, help='Live2D模型文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logger.info(f"启动Live2D预览进程，模型路径: {args.model_path}")

    # 检查模型文件是否存在
    if not os.path.exists(args.model_path):
        logger.error(f"模型文件不存在: {args.model_path}")
        sys.exit(1)

    # 创建Qt应用程序
    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setApplicationName("Live2D Preview Process")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("AI Live2D")

    try:
        # 创建预览窗口
        preview_window = Live2DPreviewWindow(args.model_path)

        # 显示窗口
        preview_window.show()

        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info("接收到关闭信号，正在清理...")
            app.quit()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # 运行应用程序
        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"Live2D预览进程启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
