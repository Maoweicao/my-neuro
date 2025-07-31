"""
Live2D模型控制器 - 负责显示和控制Live2D模型
"""

import os
import sys
import win32gui
import win32con
import OpenGL.GL as gl
import numpy as np
import logging
import asyncio
from PyQt5.QtCore import QTimerEvent, Qt, pyqtSignal, QThread, QEvent, pyqtSlot, QMetaObject, Q_ARG
from PyQt5.QtGui import QMouseEvent, QCursor, QSurfaceFormat
from PyQt5.QtWidgets import QOpenGLWidget, QApplication
from PyQt5.QtGui import QGuiApplication

from .lip_sync_thread import LipSyncThread
import live2d.v3 as live2d
from live2d.v3 import StandardParams

logger = logging.getLogger("live2d_model")

# 全局变量，用于管理应用和资源
_app = None
_model = None

class Live2DModel(QOpenGLWidget):
    """Live2D模型控制器类，继承自QOpenGLWidget"""

    # 定义信号
    model_clicked = pyqtSignal(float, float)  # 点击模型信号
    model_dragged = pyqtSignal(float, float)  # 拖拽模型信号
    model_loaded = pyqtSignal()               # 模型加载完成信号

    def __init__(self, config=None, event_bus=None):
        """初始化Live2D模型控制器

        Args:
            config: 配置信息
            event_bus: 事件总线
        """
        super().__init__()

        # 保存配置和事件总线
        self.config = config or {}
        self.event_bus = event_bus

        # 从配置获取模型路径和设置
        self.model_path = self.config.get("model_path", "")
        self.model_scale = self.config.get("ui", {}).get("model_scale", 1.0)

        # 窗口初始化设置
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )  # 无边框窗口，任务栏不显示图标，永远置顶
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 透明背景

        # 设置分层窗口和初始穿透属性
        self.hwnd = int(self.winId())
        win32gui.SetWindowLong(
            self.hwnd,
            win32con.GWL_EXSTYLE,
            win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE) |
            win32con.WS_EX_LAYERED |
            win32con.WS_EX_TRANSPARENT
        )
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, win32con.LWA_ALPHA)

        # 模型位置偏移量
        self.model_offset_x = 1050
        self.model_offset_y = 600
        self.drag_mode = 1  # 0为移动窗口模型，1为移动模型模式

        # 窗口状态
        self.isInModelArea = False  # 鼠标是否在模型区域内
        self.isClickingModel = False  # 是否正在点击模型
        self.screen_size = QGuiApplication.primaryScreen().geometry()
        self.window_size = (1000, 1000)

        # 根据拖拽模式不同设置窗口大小和位置
        if self.drag_mode:
            self.resize(self.screen_size.width()+1, self.screen_size.height())
            # 将窗口移动到中心位置
            self.move(
                (self.screen_size.width()-self.frameGeometry().width())//2,
                (self.screen_size.height()-self.frameGeometry().height())//2
            )
        else:
            self.resize(self.window_size[0], self.window_size[1])  # 窗口大小
            self.move(
                (self.screen_size.width()-self.frameGeometry().width())//2,
                (self.screen_size.height()-self.frameGeometry().height())//2
            )

        # 鼠标和缩放相关
        self.is_pressed = False
        self.scale = self.model_scale  # 使用配置中的缩放比例
        self.clickX = -1
        self.clickY = -1
        self.drag_start_offset_x = 0
        self.drag_start_offset_y = 0

        # 显示系统缩放比例
        self.systemScale = QGuiApplication.primaryScreen().devicePixelRatio()

        # Live2D模型相关
        self.model = None  # 存储Live2D模型实例
        self.is_talking = False  # 是否正在说话
        self.is_listening = False  # 是否正在聆听
        self.current_expression = ""  # 当前表情

        # 初始化WavHandler用于嘴型同步
        self.lip_sync_intensity = 3.0  # 嘴型动作强度系数

        # 添加嘴型同步线程引用
        self.lip_sync_thread = None

        # 键盘控制动作相关
        self.tapbody_motions = []  # 动作列表 [索引, ...]
        self.current_tapbody_idx = 0  # 当前动作索引
        self.is_playing_tapbody = False  # 是否正在播放动作
        self.motion_group_name = None  # 存储当前使用的动作组名称（TapBody 或 Tap）

        # 启用键盘焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        logger.info("Live2D模型控制器初始化完成")

    def initializeGL(self):
        """初始化OpenGL和加载Live2D模型"""
        try:
            # 将当前窗口作为OpenGL上下文
            self.makeCurrent()

            # 初始化Live2D
            if hasattr(live2d, 'LIVE2D_VERSION') and live2d.LIVE2D_VERSION == 3:
                try:
                    live2d.glInit()  # 初始化OpenGL(仅限Live2D v3)
                    logger.info("Live2D glInit 成功")
                except Exception as e:
                    logger.error(f"Live2D glInit 失败: {e}")

            # 创建模型实例
            try:
                self.model = live2d.LAppModel()
                logger.info("Live2D 模型实例创建成功")
            except Exception as e:
                logger.error(f"Live2D 模型实例创建失败: {e}")
                raise

            # 加载模型
            model_loaded = False
            if self.model_path and os.path.exists(self.model_path):
                try:
                    self.model.LoadModelJson(self.model_path)
                    logger.info(f"从配置路径加载模型成功: {self.model_path}")
                    model_loaded = True
                except Exception as e:
                    logger.error(f"从配置路径加载模型失败: {self.model_path}, 错误: {e}")

            if not model_loaded and hasattr(live2d, 'LIVE2D_VERSION') and live2d.LIVE2D_VERSION == 3:
                # 自动搜索2D文件夹下的.model3.json文件
                search_dirs = ["2D", "UI/2D", "."]  # 搜索目录优先级

                for search_dir in search_dirs:
                    if not os.path.exists(search_dir):
                        continue

                    try:
                        # 遍历目录下的所有文件
                        for file in os.listdir(search_dir):
                            if file.endswith('.model3.json'):
                                model_path = os.path.join(search_dir, file)
                                try:
                                    self.model.LoadModelJson(model_path)
                                    logger.info(f"自动发现并加载模型: {model_path}")
                                    model_loaded = True
                                    break
                                except Exception as e:
                                    logger.error(f"加载模型失败: {model_path}, 错误: {e}")

                        if model_loaded:
                            break

                    except Exception as e:
                        logger.error(f"搜索目录失败: {search_dir}, 错误: {e}")

                if not model_loaded:
                    logger.warning("未能找到任何.model3.json文件")

            # 设置模型缩放
            if self.model:
                self.model.SetScale(self.scale)

            # 启动高帧率定时器
            self.startTimer(int(1000 / 60))  # 启动60FPS定时器

            # 设置模型初始偏移位置
            if self.model and (self.model_offset_x != 0 or self.model_offset_y != 0):
                canvas_w, canvas_h = self.model.GetCanvasSize()
                self.model.SetOffset(
                    (self.model_offset_x - canvas_w / 2) / (self.screen_size.height() / 2),
                    (-self.model_offset_y + canvas_h / 2) / (self.screen_size.height() / 2)
                )
                logger.info(f"设置模型偏移: x={self.model_offset_x}, y={self.model_offset_y}")

            # 初始化动作列表
            self.setup_motion_list()

            # 发送模型加载完成信号
            self.model_loaded.emit()

            logger.info("Live2D模型初始化完成")

        except Exception as e:
            logger.error(f"初始化Live2D模型失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def setup_motion_list(self):
        """初始化动作列表 - 优先TapBody，备选Tap"""
        if self.model:
            try:
                motions = self.model.GetMotionGroups()

                # 确定使用的动作组名称：优先TapBody，没有就用Tap
                self.motion_group_name = None
                if "TapBody" in motions:
                    self.motion_group_name = "TapBody"
                elif "Tap" in motions:
                    self.motion_group_name = "Tap"
                else:
                    print("未找到TapBody或Tap动作组")
                    return

                # 获取动作数量
                motion_count = motions[self.motion_group_name]
                self.tapbody_motions = list(range(motion_count))

                print(f"=== Live2D {self.motion_group_name}动作列表 ===")
                print(f"{self.motion_group_name}组共 {motion_count} 个动作")
                for i in range(motion_count):
                    print(f"{i + 1}: {self.motion_group_name}[{i}] - 按 Ctrl+{i + 1}")
                print(f"=== 快捷键说明 ===")
                print(f"Ctrl+1~{min(motion_count, 10)}: 播放对应{self.motion_group_name}动作")
                print(f"Ctrl+U: 循环切换{self.motion_group_name}动作")

            except Exception as e:
                logger.error(f"获取动作列表失败: {e}")

    def keyPressEvent(self, event):
        """键盘按下事件"""
        # Ctrl+数字键 播放对应的动作
        if event.modifiers() == Qt.ControlModifier:
            # 获取数字键
            key = event.key()
            if Qt.Key_1 <= key <= Qt.Key_9:  # 支持Ctrl+1到Ctrl+9
                motion_index = key - Qt.Key_1  # 转换为0-8的索引
                self.play_tapbody_motion(motion_index)
            elif key == Qt.Key_0:  # Ctrl+0 播放第10个动作
                self.play_tapbody_motion(9)
            elif key == Qt.Key_U:  # 保留Ctrl+U作为循环切换
                self.switch_to_next_motion()

        super().keyPressEvent(event)

    def play_tapbody_motion(self, motion_index):
        """播放指定索引的动作 - 兼容TapBody和Tap"""
        # 检查是否有可用的动作组
        if not hasattr(self, 'motion_group_name') or not self.motion_group_name:
            print("没有可用的动作组")
            return

        if not self.tapbody_motions:
            print(f"没有可用的{self.motion_group_name}动作")
            return

        if motion_index >= len(self.tapbody_motions):
            print(f"动作索引 {motion_index + 1} 超出范围，{self.motion_group_name}组只有 {len(self.tapbody_motions)} 个动作")
            return

        # 使用检测到的动作组名称播放动作
        if self.model:
            try:
                self.model.StartMotion(self.motion_group_name, motion_index, 3)  # 高优先级
                self.is_playing_tapbody = True
                # print(f"播放{self.motion_group_name}动作 [{motion_index + 1}]")
            except Exception as e:
                logger.error(f"播放{self.motion_group_name}动作失败: {e}")

    def switch_to_next_motion(self):
        """切换到下一个动作（兼容版本）"""
        if not hasattr(self, 'motion_group_name') or not self.motion_group_name:
            print("没有可用的动作组")
            return

        if not self.tapbody_motions:
            print(f"没有可用的{self.motion_group_name}动作")
            return

        # 切换到下一个动作
        self.current_tapbody_idx = (self.current_tapbody_idx + 1) % len(self.tapbody_motions)
        motion_idx = self.tapbody_motions[self.current_tapbody_idx]

        # 播放动作
        if self.model:
            try:
                self.model.StartMotion(self.motion_group_name, motion_idx, 3)  # 高优先级
                self.is_playing_tapbody = True
                # print(f"播放{self.motion_group_name}动作 [{self.current_tapbody_idx + 1}]")
            except Exception as e:
                logger.error(f"播放{self.motion_group_name}动作失败: {e}")

    def resizeGL(self, width, height):
        """窗口大小改变时调整模型参数"""
        if self.model:
            self.model.Resize(width, height)

    def paintGL(self):
        """每帧渲染模型"""
        try:
            # 清空OpenGL缓冲区
            live2d.clearBuffer()

            if self.model:
                # 更新模型参数(物理、动作等)
                self.model.Update()

                # 如果模型动作结束，根据当前状态触发不同动作
                if self.model.IsMotionFinished():
                    # 如果刚播放完动作，回到Idle状态
                    if self.is_playing_tapbody:
                        self.is_playing_tapbody = False
                        print(f"{self.motion_group_name}动作播放完毕，回到Idle状态")

                    # 根据状态播放对应动作
                    if self.is_talking:
                        # 如果正在说话，播放说话动作
                        self.model.StartMotion("Talk", 0, 2)
                    elif self.is_listening:
                        # 如果正在聆听，播放聆听动作
                        self.model.StartMotion("Listen", 0, 2)
                    else:
                        # 默认播放Idle动作
                        self.model.StartMotion("Idle", 0, 1)  # 低优先级，循环播放

                # 绘制模型
                self.model.Draw()

        except Exception as e:
            logger.error(f"渲染模型失败: {e}")

    def timerEvent(self, event):
        """定时器事件，用于更新模型状态和窗口交互"""
        if not self.isVisible():
            return

        try:
            # 获取当前窗口样式
            current_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)

            # 获取鼠标相对于窗口的位置
            local_x, local_y = QCursor.pos().x() - self.x(), QCursor.pos().y() - self.y()

            # 如果不是拖拽模式，将鼠标位置传递给模型
            if not self.drag_mode and self.model:
                self.model.Drag(local_x, local_y)

            # 检查鼠标是否在模型区域内 - 修改方法名以避免与属性冲突
            in_model_area = self.check_in_model_area(local_x, local_y)

            # 更新窗口穿透属性
            if in_model_area:
                # 鼠标在模型区域内，禁用穿透
                new_style = current_style & ~win32con.WS_EX_TRANSPARENT
                self.isInModelArea = True
            else:
                # 鼠标不在模型区域内，启用穿透
                new_style = current_style | win32con.WS_EX_TRANSPARENT
                self.isInModelArea = False

            # 如果样式发生变化，更新窗口属性
            if new_style != current_style:
                win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, new_style)
                win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, win32con.LWA_ALPHA)

            # 请求重绘
            self.update()

        except Exception as e:
            logger.error(f"定时器事件处理失败: {e}")

    # 将原方法名改为check_in_model_area，以避免与属性名冲突
    def check_in_model_area(self, x, y):
        """判断坐标是否在模型区域内

        Args:
            x: 相对于窗口的X坐标
            y: 相对于窗口的Y坐标

        Returns:
            是否在模型区域内
        """
        try:
            # 计算OpenGL坐标
            gl_x = int(x * self.systemScale)
            gl_y = int((self.height() - y) * self.systemScale)

            # 检查坐标是否在窗口范围内
            if (gl_x < 0 or gl_y < 0 or
                gl_x >= self.width() * self.systemScale or
                gl_y >= self.height() * self.systemScale):
                return False

            # 读取像素的Alpha通道值
            alpha = gl.glReadPixels(gl_x, gl_y, 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)[3]

            # 如果Alpha值大于阈值，则认为在模型区域内
            return alpha > 50

        except Exception as e:
            logger.error(f"判断模型区域失败: {e}")
            return False

    def mousePressEvent(self, event):
        """鼠标按下事件

        Args:
            event: 鼠标事件
        """
        # 获取键盘焦点
        self.setFocus()

        x, y = event.localPos().x(), event.localPos().y()

        # 判断点击是否在模型区域
        if self.check_in_model_area(x, y):
            self.isClickingModel = True
            self.clickX, self.clickY = x, y  # 记录点击位置
            self.is_pressed = True

            # 记录按下时的初始偏移量
            self.drag_start_offset_x = self.model_offset_x
            self.drag_start_offset_y = self.model_offset_y

            # 发送模型点击信号
            self.model_clicked.emit(x, y)

            logger.debug("模型被点击")

    def mouseReleaseEvent(self, event):
        """鼠标释放事件

        Args:
            event: 鼠标事件
        """
        if self.drag_mode:
            # 拖拽模式下，结束拖拽
            self.isClickingModel = False
            self.is_pressed = False
        else:
            # 非拖拽模式下，处理点击
            x, y = event.localPos().x(), event.localPos().y()
            if self.is_pressed or self.isInModelArea:
                if self.model:
                    self.model.Drag(x, y)
                self.isClickingModel = False
                self.is_pressed = False

        logger.debug("鼠标释放")

    def mouseMoveEvent(self, event):
        """鼠标移动事件

        Args:
            event: 鼠标事件
        """
        x, y = event.localPos().x(), event.localPos().y()

        # 只有当点击了模型区域时才处理移动
        if self.isClickingModel:
            if self.drag_mode:
                # 拖拽模式：移动模型
                # 计算鼠标移动的增量（考虑系统缩放比例）
                dx = (x - self.clickX) / self.systemScale
                dy = (y - self.clickY) / self.systemScale

                # 更新模型偏移量
                self.model_offset_x = self.drag_start_offset_x + dx
                self.model_offset_y = self.drag_start_offset_y + dy

                # 设置模型偏移
                if self.model:
                    canvas_w, canvas_h = self.model.GetCanvasSize()
                    # 设置模型偏移（Y轴方向可能需要取反，根据实际效果调整）
                    self.model.SetOffset(
                        (self.model_offset_x - canvas_w/2)/(self.screen_size.height()/2),
                        (-self.model_offset_y + canvas_h/2)/(self.screen_size.height()/2)
                    )

                # 发送模型拖拽信号
                self.model_dragged.emit(dx, dy)
            else:
                # 非拖拽模式：移动窗口
                self.move(int(self.x() + x - self.clickX), int(self.y() + y - self.clickY))

    def wheelEvent(self, event):
        """鼠标滚轮事件，用于缩放模型

        Args:
            event: 滚轮事件
        """
        delta = event.angleDelta().y()

        # 根据滚轮方向缩放模型
        new_scale = self.scale * (1.07 if delta > 0 else 0.93)

        # 限制缩放范围
        min_scale = 0.5
        max_scale = 5.0
        new_scale = max(min_scale, min(max_scale, new_scale))

        # 应用新的缩放比例
        if new_scale != self.scale:
            self.scale = new_scale
            if self.model:
                self.model.SetScale(self.scale)

            logger.debug(f"模型缩放比例: {self.scale}")

    def start_lip_sync(self, audio_path):
        """开始嘴型同步

        Args:
            audio_path: 音频文件路径
        """
        # 确保路径存在
        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return False

        # 停止之前的嘴型同步
        self.stop_lip_sync()

        try:
            # 创建并启动嘴型同步线程
            self.lip_sync_thread = LipSyncThread(audio_path, self.event_bus, self.lip_sync_intensity)

            # 连接信号
            self.lip_sync_thread.update_signal.connect(self._update_mouth)
            self.lip_sync_thread.finished_signal.connect(self.on_lip_sync_finished)
            self.lip_sync_thread.error_signal.connect(self.on_lip_sync_error)

            # 启动线程
            self.lip_sync_thread.start()

            return True

        except Exception as e:
            logger.error(f"启动嘴型同步失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def stop_lip_sync(self):
        """停止嘴型同步"""
        if self.lip_sync_thread:
            # 调用线程的stop方法
            self.lip_sync_thread.stop()
            # 清除引用
            self.lip_sync_thread = None

            # 重置嘴部参数
            if self.model:
                try:
                    self.model.SetParameterValue(StandardParams.ParamMouthOpenY, 0.0)
                except Exception as e:
                    logger.error(f"重置嘴部参数失败: {e}")

    @pyqtSlot(float)
    def _update_mouth(self, value):
        if self.model:
            # 同时设置两种参数名，不管哪个生效
            try:
                from live2d.v3 import StandardParams
                self.model.SetParameterValue(StandardParams.ParamMouthOpenY, value)
            except:
                pass

            try:
                self.model.SetParameterValue("PARAM_MOUTH_OPEN_Y", value)
            except:
                pass

    def on_lip_sync_finished(self):
        """嘴型同步完成回调"""
        # 重置嘴部参数
        if self.model:
            try:
                self.model.SetParameterValue(StandardParams.ParamMouthOpenY, 0.0)
            except Exception as e:
                logger.error(f"重置嘴部参数失败: {e}")

    def on_lip_sync_error(self, error_msg):
        """嘴型同步错误回调"""
        logger.error(f"嘴型同步错误: {error_msg}")

    # 确保在窗口关闭时停止嘴型同步
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 尝试获取现有事件循环
            loop = asyncio.get_event_loop()
            loop.create_task(self.async_stop_lip_sync())
        except RuntimeError:
            # 如果没有事件循环，创建新的
            asyncio.run(self.async_stop_lip_sync())

        super().closeEvent(event)

    async def async_stop_lip_sync(self):
        """异步停止嘴型同步"""
        self.stop_lip_sync()
        # 取消事件订阅
        if self.event_bus:
            await self.event_bus.unsubscribe("lip_sync_start", self.start_lip_sync)
            await self.event_bus.unsubscribe("set_talking", self.set_talking)

    # 确保在析构时停止嘴型同步
    def __del__(self):
        """析构函数"""
        self.stop_lip_sync()

    def set_talking(self, is_talking):
        """设置说话状态

        Args:
            is_talking: 是否正在说话
        """
        self.is_talking = is_talking
        logger.debug(f"设置说话状态: {is_talking}")

    def set_listening(self, is_listening):
        """设置聆听状态

        Args:
            is_listening: 是否正在聆听
        """
        self.is_listening = is_listening
        logger.debug(f"设置聆听状态: {is_listening}")

    def set_expression(self, expression):
        """设置表情

        Args:
            expression: 表情名称
        """
        if self.model:
            try:
                # 设置表情
                self.model.SetExpression(expression)
                self.current_expression = expression

                logger.debug(f"设置表情: {expression}")
            except Exception as e:
                logger.error(f"设置表情失败: {e}")

    def set_random_expression(self):
        """设置随机表情"""
        if self.model:
            try:
                # 设置随机表情
                expression = self.model.SetRandomExpression()
                self.current_expression = expression

                logger.debug(f"设置随机表情: {expression}")
                return expression
            except Exception as e:
                logger.error(f"设置随机表情失败: {e}")
                return None

    def reset_expression(self):
        """重置为默认表情"""
        if self.model:
            try:
                # 重置表情
                self.model.ResetExpression()
                self.current_expression = ""

                logger.debug("重置为默认表情")
            except Exception as e:
                logger.error(f"重置表情失败: {e}")

    def get_available_expressions(self):
        """获取可用的表情列表

        Returns:
            表情ID列表
        """
        if self.model:
            try:
                # 获取表情列表
                expressions = self.model.GetExpressionIds()
                return expressions
            except Exception as e:
                logger.error(f"获取表情列表失败: {e}")

        return []

    def get_available_motions(self):
        """获取可用的动作组和数量

        Returns:
            动作组字典 {组名: 动作数量}
        """
        if self.model:
            try:
                # 获取动作组字典
                motions = self.model.GetMotionGroups()
                return motions
            except Exception as e:
                logger.error(f"获取动作组失败: {e}")

        return {}

    def toggle_auto_breath(self, enable=True):
        """切换自动呼吸功能

        Args:
            enable: 是否启用
        """
        if self.model:
            try:
                # 设置自动呼吸
                self.model.SetAutoBreathEnable(enable)

                logger.debug(f"设置自动呼吸: {enable}")
            except Exception as e:
                logger.error(f"设置自动呼吸失败: {e}")

    def toggle_auto_blink(self, enable=True):
        """切换自动眨眼功能

        Args:
            enable: 是否启用
        """
        if self.model:
            try:
                # 设置自动眨眼
                self.model.SetAutoBlinkEnable(enable)

                logger.debug(f"设置自动眨眼: {enable}")
            except Exception as e:
                logger.error(f"设置自动眨眼失败: {e}")


# 初始化和清理Live2D
def init_live2d():
    """初始化Live2D引擎"""
    try:
        live2d.init()
        logger.info("Live2D引擎初始化完成")
        return True
    except Exception as e:
        logger.error(f"初始化Live2D引擎失败: {e}")
        return False


def dispose_live2d():
    """清理Live2D引擎"""
    try:
        live2d.dispose()
        logger.info("Live2D引擎清理完成")
        return True
    except Exception as e:
        logger.error(f"清理Live2D引擎失败: {e}")
        return False


# ==================== 简化的启动接口 ====================

def start_desktop_pet(config=None, event_bus=None, blocking=True):
    """启动桌面宠物

    Args:
        config: 配置信息
        event_bus: 事件总线
        blocking: 是否阻塞运行（默认True）

    Returns:
        如果blocking=False，返回(app, model)元组
        如果blocking=True，运行完毕后返回退出码
    """
    global _app, _model

    # 设置日志（如果还没设置）
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # 初始化Live2D引擎
    if not init_live2d():
        logger.error("Live2D引擎初始化失败")
        return None

    try:
        # 创建QT应用
        _app = QApplication(sys.argv if not QApplication.instance() else [])

        # 设置垂直同步
        format = QSurfaceFormat.defaultFormat()
        format.setSwapInterval(0)  # 0禁用垂直同步，1启用
        QSurfaceFormat.setDefaultFormat(format)

        # 创建Live2D模型窗口
        _model = Live2DModel(config, event_bus)
        _model.show()

        logger.info("桌面宠物启动成功")

        if blocking:
            # 阻塞运行
            exit_code = _app.exec()

            # 清理资源
            dispose_live2d()

            return exit_code
        else:
            # 非阻塞运行，返回应用和模型实例
            return _app, _model

    except Exception as e:
        logger.error(f"启动桌面宠物失败: {e}")
        dispose_live2d()
        return None


def stop_desktop_pet():
    """停止桌面宠物"""
    global _app, _model

    if _model:
        _model.close()
        _model = None

    if _app:
        _app.quit()
        _app = None

    # 清理Live2D引擎
    dispose_live2d()


def get_desktop_pet():
    """获取当前运行的桌面宠物实例

    Returns:
        (app, model) 元组，如果没有运行则返回 (None, None)
    """
    global _app, _model
    return _app, _model


def is_running():
    """检查桌面宠物是否正在运行

    Returns:
        bool: 是否正在运行
    """
    global _app, _model
    return _app is not None and _model is not None


# ==================== 便捷函数 ====================

def quick_start():
    """快速启动桌面宠物（使用默认配置）"""
    return start_desktop_pet()


def start_with_model(model_path):
    """使用指定模型启动桌面宠物

    Args:
        model_path: 模型文件路径
    """
    config = {"model_path": model_path}
    return start_desktop_pet(config)


def start_with_config(model_path=None, scale=1.0, **kwargs):
    """使用自定义配置启动桌面宠物

    Args:
        model_path: 模型文件路径
        scale: 缩放比例
        **kwargs: 其他配置参数
    """
    config = {
        "model_path": model_path or "",
        "ui": {"model_scale": scale}
    }
    config.update(kwargs)
    return start_desktop_pet(config)


# ==================== 示例用法 ====================

if __name__ == "__main__":
    # 方式1: 最简单的启动
    quick_start()

    # 方式2: 指定模型
    # start_with_model("path/to/your/model.model3.json")

    # 方式3: 自定义配置
    # start_with_config(
    #     model_path="path/to/your/model.model3.json",
    #     scale=1.5
    # )

    # 方式4: 非阻塞启动（用于集成到其他应用）
    # app, model = start_desktop_pet(blocking=False)
    # if app and model:
    #     # 做其他事情...
    #     app.exec()  # 最后运行事件循环