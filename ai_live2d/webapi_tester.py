#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI测试工具 - PyQt版本
用于测试AI桌宠系统的所有WebAPI功能
"""

import sys
import json
import base64
import io
import wave
import numpy as np
import requests
import threading
import time
import os
from urllib.parse import urljoin

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QMessageBox, QProgressBar,
    QSplitter, QFrame, QScrollArea, QGridLayout, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

class ServiceStatusChecker(QThread):
    """服务状态检测线程"""
    status_checked = pyqtSignal(bool, str)  # (is_running, message)

    def __init__(self, host='127.0.0.1', port=8888):
        super().__init__()
        self.host = host
        self.port = port
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                url = f"http://{self.host}:{self.port}/api/status"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    result = response.json()
                    self.status_checked.emit(True, f"服务运行正常 - {result.get('message', '')}")
                else:
                    self.status_checked.emit(False, f"服务响应异常: {response.status_code}")

            except requests.exceptions.ConnectionError:
                self.status_checked.emit(False, "无法连接到服务")
            except Exception as e:
                self.status_checked.emit(False, f"检测失败: {str(e)}")

            # 每5秒检测一次
            time.sleep(5)

    def stop(self):
        self.is_running = False

class AudioGenerator:
    """音频生成器 - 用于唱歌测试"""

    @staticmethod
    def create_test_audio_base64(duration=2.0, frequency=440.0, sample_rate=44100):
        """创建一个简单的测试音频（正弦波）并转换为base64"""
        # 生成正弦波音频数据
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(frequency * 2 * np.pi * t)

        # 转换为16位整数
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # 创建WAV文件缓冲区
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        # 获取WAV数据并编码为base64
        wav_data = buffer.getvalue()
        audio_base64 = base64.b64encode(wav_data).decode('utf-8')

        return audio_base64

class WebAPITester(QMainWindow):
    """WebAPI测试工具主窗口"""

    # 定义信号
    update_chat_result = pyqtSignal(str)
    update_interrupt_result = pyqtSignal(str)
    update_dialogue_result = pyqtSignal(str)
    update_singing_result = pyqtSignal(str)
    update_batch_result = pyqtSignal(str)
    update_batch_progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI桌宠 WebAPI 测试工具")
        self.setGeometry(100, 100, 1000, 700)

        # 初始化变量
        self.host = '127.0.0.1'
        self.port = 8888
        self.api_key = ''
        self.status_checker = None

        # 连接信号
        self.update_chat_result.connect(self._update_chat_result_text)
        self.update_interrupt_result.connect(self._update_interrupt_result_text)
        self.update_dialogue_result.connect(self._update_dialogue_result_text)
        self.update_singing_result.connect(self._update_singing_result_text)
        self.update_batch_result.connect(self._update_batch_result_text)
        self.update_batch_progress.connect(self._update_batch_progress)

        # 创建UI
        self.create_ui()

        # 启动服务状态检测
        self.start_status_check()

        # 设置样式
        self.set_style()

    def create_ui(self):
        """创建用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 连接设置区域
        self.create_connection_settings(main_layout)

        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 服务状态标签页
        self.create_status_tab()

        # 聊天测试标签页
        self.create_chat_tab()

        # 打断测试标签页
        self.create_interrupt_tab()

        # 台词转换测试标签页
        self.create_dialogue_tab()

        # 唱歌测试标签页
        self.create_singing_tab()

        # 批量测试标签页
        self.create_batch_test_tab()

    def create_connection_settings(self, parent_layout):
        """创建连接设置区域"""
        group = QGroupBox("连接设置")
        layout = QHBoxLayout(group)

        # 主机
        layout.addWidget(QLabel("主机:"))
        self.host_edit = QLineEdit(self.host)
        self.host_edit.textChanged.connect(self.on_connection_changed)
        layout.addWidget(self.host_edit)

        # 端口
        layout.addWidget(QLabel("端口:"))
        self.port_edit = QLineEdit(str(self.port))
        self.port_edit.textChanged.connect(self.on_connection_changed)
        layout.addWidget(self.port_edit)

        # API密钥
        layout.addWidget(QLabel("API密钥:"))
        self.api_key_edit = QLineEdit(self.api_key)
        self.api_key_edit.setPlaceholderText("可选")
        self.api_key_edit.textChanged.connect(self.on_connection_changed)
        layout.addWidget(self.api_key_edit)

        # 连接测试按钮
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_connection_btn)

        # 状态标签
        self.connection_status_label = QLabel("未连接")
        self.connection_status_label.setStyleSheet("color: red;")
        layout.addWidget(self.connection_status_label)

        layout.addStretch()
        parent_layout.addWidget(group)

    def create_status_tab(self):
        """创建服务状态标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 状态显示区域
        status_group = QGroupBox("服务状态")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        status_layout.addWidget(self.status_text)

        # 手动刷新按钮
        refresh_btn = QPushButton("手动刷新状态")
        refresh_btn.clicked.connect(self.manual_status_check)
        status_layout.addWidget(refresh_btn)

        layout.addWidget(status_group)

        # API信息区域
        info_group = QGroupBox("API信息")
        info_layout = QVBoxLayout(info_group)

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("""支持的API端点:
/api/status - 获取服务状态
/api/chat - 聊天功能
/api/interrupt - 打断当前操作
/api/dialogue - 台词转换
/api/sing - 唱歌功能""")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "服务状态")

    def create_chat_tab(self):
        """创建聊天测试标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输入区域
        input_group = QGroupBox("聊天请求")
        input_layout = QVBoxLayout(input_group)

        input_layout.addWidget(QLabel("消息内容:"))
        self.chat_message_edit = QTextEdit()
        self.chat_message_edit.setPlaceholderText("输入要发送的消息...")
        self.chat_message_edit.setMaximumHeight(80)
        input_layout.addWidget(self.chat_message_edit)

        # 发送按钮
        chat_btn = QPushButton("发送聊天请求")
        chat_btn.clicked.connect(self.test_chat_api)
        input_layout.addWidget(chat_btn)

        layout.addWidget(input_group)

        # 结果显示区域
        result_group = QGroupBox("响应结果")
        result_layout = QVBoxLayout(result_group)

        self.chat_result_text = QTextEdit()
        self.chat_result_text.setReadOnly(True)
        result_layout.addWidget(self.chat_result_text)

        layout.addWidget(result_group)

        self.tab_widget.addTab(tab, "聊天测试")

    def create_interrupt_tab(self):
        """创建打断测试标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 说明区域
        info_group = QGroupBox("说明")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel("打断API用于中断当前正在进行的AI输出和语音播放操作。")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # 测试区域
        test_group = QGroupBox("测试")
        test_layout = QVBoxLayout(test_group)

        interrupt_btn = QPushButton("发送打断请求")
        interrupt_btn.clicked.connect(self.test_interrupt_api)
        test_layout.addWidget(interrupt_btn)

        layout.addWidget(test_group)

        # 结果显示区域
        result_group = QGroupBox("响应结果")
        result_layout = QVBoxLayout(result_group)

        self.interrupt_result_text = QTextEdit()
        self.interrupt_result_text.setReadOnly(True)
        result_layout.addWidget(self.interrupt_result_text)

        layout.addWidget(result_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "打断测试")

    def create_dialogue_tab(self):
        """创建台词转换测试标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输入区域
        input_group = QGroupBox("台词转换请求")
        input_layout = QVBoxLayout(input_group)

        input_layout.addWidget(QLabel("原始台词:"))
        self.dialogue_input_edit = QTextEdit()
        self.dialogue_input_edit.setPlaceholderText("输入要转换的台词...")
        self.dialogue_input_edit.setMaximumHeight(80)
        input_layout.addWidget(self.dialogue_input_edit)

        # 发送按钮
        dialogue_btn = QPushButton("转换台词")
        dialogue_btn.clicked.connect(self.test_dialogue_api)
        input_layout.addWidget(dialogue_btn)

        layout.addWidget(input_group)

        # 结果显示区域
        result_group = QGroupBox("转换结果")
        result_layout = QVBoxLayout(result_group)

        self.dialogue_result_text = QTextEdit()
        self.dialogue_result_text.setReadOnly(True)
        result_layout.addWidget(self.dialogue_result_text)

        layout.addWidget(result_group)

        self.tab_widget.addTab(tab, "台词转换")

    def create_singing_tab(self):
        """创建唱歌测试标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 参数设置区域
        param_group = QGroupBox("唱歌参数设置")
        param_layout = QFormLayout(param_group)

        # 音量
        self.singing_volume_spin = QDoubleSpinBox()
        self.singing_volume_spin.setRange(0.0, 2.0)
        self.singing_volume_spin.setValue(0.8)
        self.singing_volume_spin.setSingleStep(0.1)
        param_layout.addRow("音量:", self.singing_volume_spin)

        # 循环播放
        self.singing_loop_check = QCheckBox()
        self.singing_loop_check.setChecked(False)
        param_layout.addRow("循环播放:", self.singing_loop_check)

        # 唱歌动作
        self.singing_motion_combo = QComboBox()
        self.singing_motion_combo.addItems(["唱歌", "开始唱歌", "跳舞", "开心", "悲伤", "生气", "惊讶"])
        param_layout.addRow("Live2D动作:", self.singing_motion_combo)

        # 字幕开关
        self.singing_subtitle_check = QCheckBox()
        self.singing_subtitle_check.setChecked(True)
        param_layout.addRow("启用字幕:", self.singing_subtitle_check)

        layout.addWidget(param_group)

        # 测试区域
        test_group = QGroupBox("测试")
        test_layout = QVBoxLayout(test_group)

        # 文件选择区域
        file_group = QGroupBox("音频文件选择")
        file_layout = QHBoxLayout(file_group)

        self.audio_file_path = ""
        self.audio_file_label = QLabel("未选择文件")
        self.audio_file_label.setStyleSheet("border: 1px solid #ccc; padding: 5px; background: #f9f9f9;")
        file_layout.addWidget(self.audio_file_label)

        select_file_btn = QPushButton("选择音频文件")
        select_file_btn.clicked.connect(self.select_audio_file)
        file_layout.addWidget(select_file_btn)

        test_layout.addWidget(file_group)

        # LRC歌词文件选择区域
        lrc_group = QGroupBox("LRC歌词文件选择 (可选)")
        lrc_layout = QHBoxLayout(lrc_group)

        self.lrc_file_path = ""
        self.lrc_file_label = QLabel("未选择LRC文件")
        self.lrc_file_label.setStyleSheet("border: 1px solid #ccc; padding: 5px; background: #f9f9f9;")
        lrc_layout.addWidget(self.lrc_file_label)

        select_lrc_btn = QPushButton("选择LRC文件")
        select_lrc_btn.clicked.connect(self.select_lrc_file)
        lrc_layout.addWidget(select_lrc_btn)

        clear_lrc_btn = QPushButton("清除LRC")
        clear_lrc_btn.clicked.connect(self.clear_lrc_file)
        lrc_layout.addWidget(clear_lrc_btn)

        test_layout.addWidget(lrc_group)

        # 或者生成音频按钮
        generate_audio_btn = QPushButton("生成测试音频")
        generate_audio_btn.clicked.connect(self.generate_test_audio)
        test_layout.addWidget(generate_audio_btn)

        # 发送唱歌请求按钮
        singing_btn = QPushButton("发送唱歌请求")
        singing_btn.clicked.connect(self.test_singing_api)
        test_layout.addWidget(singing_btn)

        layout.addWidget(test_group)

        # 结果显示区域
        result_group = QGroupBox("响应结果")
        result_layout = QVBoxLayout(result_group)

        self.singing_result_text = QTextEdit()
        self.singing_result_text.setReadOnly(True)
        result_layout.addWidget(self.singing_result_text)

        layout.addWidget(result_group)

        self.tab_widget.addTab(tab, "唱歌测试")

    def create_batch_test_tab(self):
        """创建批量测试标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 测试选项
        options_group = QGroupBox("测试选项")
        options_layout = QVBoxLayout(options_group)

        self.batch_chat_check = QCheckBox("聊天API测试")
        self.batch_chat_check.setChecked(True)
        options_layout.addWidget(self.batch_chat_check)

        self.batch_interrupt_check = QCheckBox("打断API测试")
        self.batch_interrupt_check.setChecked(True)
        options_layout.addWidget(self.batch_interrupt_check)

        self.batch_dialogue_check = QCheckBox("台词转换API测试")
        self.batch_dialogue_check.setChecked(True)
        options_layout.addWidget(self.batch_dialogue_check)

        self.batch_singing_check = QCheckBox("唱歌API测试")
        self.batch_singing_check.setChecked(True)
        options_layout.addWidget(self.batch_singing_check)

        layout.addWidget(options_group)

        # 执行区域
        exec_group = QGroupBox("执行测试")
        exec_layout = QVBoxLayout(exec_group)

        self.batch_progress = QProgressBar()
        self.batch_progress.setRange(0, 100)
        exec_layout.addWidget(self.batch_progress)

        batch_btn = QPushButton("开始批量测试")
        batch_btn.clicked.connect(self.run_batch_test)
        exec_layout.addWidget(batch_btn)

        layout.addWidget(exec_group)

        # 结果显示区域
        result_group = QGroupBox("测试结果")
        result_layout = QVBoxLayout(result_group)

        self.batch_result_text = QTextEdit()
        self.batch_result_text.setReadOnly(True)
        result_layout.addWidget(self.batch_result_text)

        layout.addWidget(result_group)

        self.tab_widget.addTab(tab, "批量测试")

    def set_style(self):
        """设置样式"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QPushButton {
                padding: 8px 16px;
                font-size: 12px;
            }
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """)

    def on_connection_changed(self):
        """连接参数改变时的处理"""
        try:
            self.host = self.host_edit.text().strip()
            self.port = int(self.port_edit.text().strip())
            self.api_key = self.api_key_edit.text().strip()
        except ValueError:
            pass

    def start_status_check(self):
        """启动服务状态检测"""
        if self.status_checker:
            self.status_checker.stop()
            self.status_checker.wait()

        self.status_checker = ServiceStatusChecker(self.host, self.port)
        self.status_checker.status_checked.connect(self.on_status_checked)
        self.status_checker.start()

    def on_status_checked(self, is_running, message):
        """服务状态检测结果处理"""
        if is_running:
            self.connection_status_label.setText("✓ 已连接")
            self.connection_status_label.setStyleSheet("color: green;")
        else:
            self.connection_status_label.setText("✗ 未连接")
            self.connection_status_label.setStyleSheet("color: red;")

        # 添加到状态文本
        timestamp = time.strftime("%H:%M:%S")
        status_msg = f"[{timestamp}] {message}\n"
        self.status_text.append(status_msg)

    def manual_status_check(self):
        """手动刷新服务状态"""
        self.start_status_check()

    def test_connection(self):
        """测试连接"""
        try:
            url = f"http://{self.host}:{self.port}/api/status"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(self, "连接测试", f"连接成功!\n{result.get('message', '')}")
            else:
                QMessageBox.warning(self, "连接测试", f"连接失败: HTTP {response.status_code}")

        except Exception as e:
            QMessageBox.critical(self, "连接测试", f"连接失败: {str(e)}")

    def test_chat_api(self):
        """测试聊天API"""
        message = self.chat_message_edit.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "输入错误", "请输入消息内容")
            return

        def run_test():
            try:
                url = f"http://{self.host}:{self.port}/api/chat"
                data = {"message": message}
                if self.api_key:
                    data["api_key"] = self.api_key

                response = requests.post(url, json=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    self.update_chat_result.emit("状态: 成功")
                    self.update_chat_result.emit(f"响应: {result.get('response', '')}")
                    self.update_chat_result.emit(f"时间戳: {result.get('timestamp', '')}")
                else:
                    error_result = response.json()
                    self.update_chat_result.emit(f"状态: 失败 (HTTP {response.status_code})")
                    self.update_chat_result.emit(f"错误: {error_result.get('error', 'Unknown error')}")

            except Exception as e:
                self.update_chat_result.emit(f"请求异常: {str(e)}")

        # 清空结果文本
        self.chat_result_text.clear()

        # 在后台线程中运行测试
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()

    def test_interrupt_api(self):
        """测试打断API"""
        def run_test():
            try:
                url = f"http://{self.host}:{self.port}/api/interrupt"
                data = {}
                if self.api_key:
                    data["api_key"] = self.api_key

                response = requests.post(url, json=data, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    self.update_interrupt_result.emit(f"状态: 成功")
                    self.update_interrupt_result.emit(f"消息: {result.get('message', '')}")
                    self.update_interrupt_result.emit(f"时间戳: {result.get('timestamp', '')}")
                else:
                    error_result = response.json()
                    self.update_interrupt_result.emit(f"状态: 失败 (HTTP {response.status_code})")
                    self.update_interrupt_result.emit(f"错误: {error_result.get('error', 'Unknown error')}")

            except Exception as e:
                self.update_interrupt_result.emit(f"请求异常: {str(e)}")

        # 清空结果文本
        self.interrupt_result_text.clear()

        # 在后台线程中运行测试
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()

    def test_dialogue_api(self):
        """测试台词转换API"""
        dialogue = self.dialogue_input_edit.toPlainText().strip()
        if not dialogue:
            QMessageBox.warning(self, "输入错误", "请输入台词内容")
            return

        def run_test():
            try:
                url = f"http://{self.host}:{self.port}/api/dialogue"
                data = {"dialogue": dialogue}
                if self.api_key:
                    data["api_key"] = self.api_key

                response = requests.post(url, json=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    self.update_dialogue_result.emit(f"原始台词: {result.get('original_dialogue', '')}")
                    self.update_dialogue_result.emit(f"转换后: {result.get('converted_dialogue', '')}")
                    self.update_dialogue_result.emit(f"状态: 成功")
                    self.update_dialogue_result.emit(f"时间戳: {result.get('timestamp', '')}")
                else:
                    error_result = response.json()
                    self.update_dialogue_result.emit(f"状态: 失败 (HTTP {response.status_code})")
                    self.update_dialogue_result.emit(f"错误: {error_result.get('error', 'Unknown error')}")

            except Exception as e:
                self.update_dialogue_result.emit(f"请求异常: {str(e)}")

        # 清空结果文本
        self.dialogue_result_text.clear()

        # 在后台线程中运行测试
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()

    def select_audio_file(self):
        """选择音频文件"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.wma);;WAV文件 (*.wav);;MP3文件 (*.mp3);;FLAC文件 (*.flac);;OGG文件 (*.ogg);;M4A文件 (*.m4a);;AAC文件 (*.aac);;WMA文件 (*.wma);;所有文件 (*.*)"
        )

        if file_path:
            self.audio_file_path = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            self.audio_file_label.setText(f"已选择: {file_name} ({file_size} bytes)")
            # 清除生成的测试音频
            if hasattr(self, 'test_audio_base64'):
                delattr(self, 'test_audio_base64')
        else:
            self.audio_file_path = ""
            self.audio_file_label.setText("未选择文件")

    def load_audio_file_base64(self, file_path):
        """读取音频文件并转换为base64，支持多种格式"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise Exception(f"文件不存在: {file_path}")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise Exception("文件为空")
            
            if file_size > 50 * 1024 * 1024:  # 50MB限制
                raise Exception(f"文件过大: {file_size} bytes (最大50MB)")
            
            # 读取文件
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            
            # 转换为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return audio_base64
        except Exception as e:
            raise Exception(f"读取音频文件失败: {str(e)}")

    def generate_test_audio(self):
        """生成测试音频"""
        try:
            self.test_audio_base64 = AudioGenerator.create_test_audio_base64(
                duration=2.0, frequency=440.0
            )
            # 清除选择的文件
            self.audio_file_path = ""
            self.audio_file_label.setText("未选择文件")
            QMessageBox.information(self, "成功", "测试音频已生成！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成音频失败: {str(e)}")

    def test_singing_api(self):
        """测试唱歌API"""
        # 检查是否有音频源（生成或文件）
        if not hasattr(self, 'test_audio_base64') and not self.audio_file_path:
            QMessageBox.warning(self, "警告", "请先选择音频文件或生成测试音频")
            return

        def run_test():
            try:
                url = f"http://{self.host}:{self.port}/api/sing"

                # 准备音频数据
                if self.audio_file_path:
                    # 使用本地文件
                    audio_base64 = self.load_audio_file_base64(self.audio_file_path)
                    file_name = os.path.basename(self.audio_file_path)
                    file_ext = os.path.splitext(file_name)[1].lower()
                    self.update_singing_result.emit(f"使用文件: {file_name}")
                    self.update_singing_result.emit(f"原始格式: {file_ext}")
                    self.update_singing_result.emit("服务器将自动检测并转换为WAV格式进行播放")
                else:
                    # 使用生成的测试音频
                    audio_base64 = self.test_audio_base64
                    self.update_singing_result.emit("使用生成的测试音频 (WAV格式)")

                # 检查LRC文件
                lrc_content = None
                if self.lrc_file_path:
                    lrc_content = self.load_lrc_file_content(self.lrc_file_path)
                    if lrc_content:
                        self.update_singing_result.emit(f"LRC歌词文件: {os.path.basename(self.lrc_file_path)}")
                        self.update_singing_result.emit(f"歌词内容长度: {len(lrc_content)} 字符")
                    else:
                        self.update_singing_result.emit("LRC文件读取失败")

                data = {
                    "audio_base64": audio_base64,
                    "volume": self.singing_volume_spin.value(),
                    "loop": self.singing_loop_check.isChecked(),
                    "singing_motion": self.singing_motion_combo.currentText()
                }
                if self.api_key:
                    data["api_key"] = self.api_key

                # 显示字幕设置状态
                subtitle_enabled = self.singing_subtitle_check.isChecked()
                self.update_singing_result.emit(f"字幕启用: {'是' if subtitle_enabled else '否'}")
                if subtitle_enabled:
                    if lrc_content:
                        self.update_singing_result.emit("字幕模式: 显示LRC歌词")
                    else:
                        self.update_singing_result.emit("字幕模式: 显示 ♪ 唱歌中 ♫")
                else:
                    self.update_singing_result.emit("字幕模式: 禁用")

                self.update_singing_result.emit("发送唱歌请求到服务器...")
                response = requests.post(url, json=data, timeout=30)
                response = requests.post(url, json=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    self.update_singing_result.emit("✓ 状态: 成功")
                    self.update_singing_result.emit(f"音量: {result.get('volume', 'N/A')}")
                    self.update_singing_result.emit(f"循环: {result.get('loop', 'N/A')}")
                    self.update_singing_result.emit(f"动作: {result.get('singing_motion', 'N/A')}")
                    self.update_singing_result.emit(f"时间戳: {result.get('timestamp', 'N/A')}")
                    self.update_singing_result.emit("")
                    self.update_singing_result.emit("音频播放已在后台开始，Live2D动作已触发")
                    if self.singing_loop_check.isChecked():
                        self.update_singing_result.emit("注意: 循环播放模式，请使用打断API停止播放")
                else:
                    error_result = response.json()
                    self.update_singing_result.emit(f"✗ 状态: 失败 (HTTP {response.status_code})")
                    self.update_singing_result.emit(f"错误: {error_result.get('error', 'Unknown error')}")

            except requests.exceptions.Timeout:
                self.update_singing_result.emit("✗ 请求超时 (30秒)")
                self.update_singing_result.emit("可能的原因: 音频文件过大或服务器处理时间过长")
            except requests.exceptions.ConnectionError:
                self.update_singing_result.emit("✗ 连接失败")
                self.update_singing_result.emit("请检查服务器是否正在运行")
            except Exception as e:
                self.update_singing_result.emit(f"✗ 请求异常: {str(e)}")

        # 清空结果文本
        self.singing_result_text.clear()

        # 在后台线程中运行测试
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()

    def run_batch_test(self):
        """运行批量测试"""
        self.batch_result_text.clear()
        self.batch_progress.setValue(0)

        test_items = []
        if self.batch_chat_check.isChecked():
            test_items.append(("聊天API", self._batch_test_chat))
        if self.batch_interrupt_check.isChecked():
            test_items.append(("打断API", self._batch_test_interrupt))
        if self.batch_dialogue_check.isChecked():
            test_items.append(("台词转换API", self._batch_test_dialogue))
        if self.batch_singing_check.isChecked():
            test_items.append(("唱歌API", self._batch_test_singing))

        if not test_items:
            QMessageBox.warning(self, "警告", "请至少选择一个测试项目")
            return

        def run_batch():
            total_tests = len(test_items)
            completed = 0

            for test_name, test_func in test_items:
                self.batch_result_text.append(f"\n=== 开始测试: {test_name} ===")
                try:
                    test_func()
                    self.batch_result_text.append(f"✓ {test_name} 测试完成")
                except Exception as e:
                    self.batch_result_text.append(f"✗ {test_name} 测试失败: {str(e)}")

                completed += 1
                progress = int((completed / total_tests) * 100)
                self.batch_progress.setValue(progress)

            self.batch_result_text.append("\n=== 批量测试完成 ===")

        # 在后台线程中运行批量测试
        thread = threading.Thread(target=run_batch)
        thread.daemon = True
        thread.start()

    def _batch_test_chat(self):
        """批量测试聊天API"""
        test_messages = ["你好", "今天天气怎么样", "讲个笑话"]
        for msg in test_messages:
            try:
                url = f"http://{self.host}:{self.port}/api/chat"
                data = {"message": msg}
                if self.api_key:
                    data["api_key"] = self.api_key

                response = requests.post(url, json=data, timeout=10)
                if response.status_code == 200:
                    self.batch_result_text.append(f"  ✓ 消息 '{msg}' 发送成功")
                else:
                    self.batch_result_text.append(f"  ✗ 消息 '{msg}' 发送失败")
            except Exception as e:
                self.batch_result_text.append(f"  ✗ 消息 '{msg}' 异常: {str(e)}")

    def _batch_test_interrupt(self):
        """批量测试打断API"""
        try:
            url = f"http://{self.host}:{self.port}/api/interrupt"
            data = {}
            if self.api_key:
                data["api_key"] = self.api_key

            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                self.batch_result_text.append("  ✓ 打断请求成功")
            else:
                self.batch_result_text.append("  ✗ 打断请求失败")
        except Exception as e:
            self.batch_result_text.append(f"  ✗ 打断请求异常: {str(e)}")

    def _batch_test_dialogue(self):
        """批量测试台词转换API"""
        test_dialogues = ["你好啊", "我很开心", "这是什么"]
        for dialogue in test_dialogues:
            try:
                url = f"http://{self.host}:{self.port}/api/dialogue"
                data = {"dialogue": dialogue}
                if self.api_key:
                    data["api_key"] = self.api_key

                response = requests.post(url, json=data, timeout=10)
                if response.status_code == 200:
                    self.batch_result_text.append(f"  ✓ 台词 '{dialogue}' 转换成功")
                else:
                    self.batch_result_text.append(f"  ✗ 台词 '{dialogue}' 转换失败")
            except Exception as e:
                self.batch_result_text.append(f"  ✗ 台词 '{dialogue}' 异常: {str(e)}")

    def _batch_test_singing(self):
        """批量测试唱歌API（包含字幕测试）"""
        try:
            # 生成测试音频
            audio_base64 = AudioGenerator.create_test_audio_base64(duration=1.0)

            url = f"http://{self.host}:{self.port}/api/sing"

            # 测试1: 无字幕模式
            self.batch_result_text.append("  测试1: 无字幕唱歌")
            data_no_subtitle = {
                "audio_base64": audio_base64,
                "volume": 0.5,
                "loop": False,
                "singing_motion": "唱歌"
            }
            if self.api_key:
                data_no_subtitle["api_key"] = self.api_key

            response = requests.post(url, json=data_no_subtitle, timeout=10)
            if response.status_code == 200:
                self.batch_result_text.append("    ✓ 无字幕唱歌请求成功")
            else:
                self.batch_result_text.append("    ✗ 无字幕唱歌请求失败")

            # 等待一秒，避免请求过于频繁
            time.sleep(1)

            # 测试2: 有字幕模式（但没有LRC文件，会显示♪♫）
            self.batch_result_text.append("  测试2: 有字幕唱歌（无LRC文件）")
            data_with_subtitle = {
                "audio_base64": audio_base64,
                "volume": 0.5,
                "loop": False,
                "singing_motion": "唱歌"
            }
            if self.api_key:
                data_with_subtitle["api_key"] = self.api_key

            response = requests.post(url, json=data_with_subtitle, timeout=10)
            if response.status_code == 200:
                self.batch_result_text.append("    ✓ 有字幕唱歌请求成功（将显示 ♪ 唱歌中 ♫）")
            else:
                self.batch_result_text.append("    ✗ 有字幕唱歌请求失败")

        except Exception as e:
            self.batch_result_text.append(f"  ✗ 唱歌批量测试异常: {str(e)}")

    def _update_chat_result_text(self, text):
        """更新聊天结果文本"""
        self.chat_result_text.append(text)

    def _update_interrupt_result_text(self, text):
        """更新打断结果文本"""
        self.interrupt_result_text.append(text)

    def _update_dialogue_result_text(self, text):
        """更新台词转换结果文本"""
        self.dialogue_result_text.append(text)

    def _update_singing_result_text(self, text):
        """更新唱歌结果文本"""
        self.singing_result_text.append(text)

    def _update_batch_result_text(self, text):
        """更新批量测试结果文本"""
        self.batch_result_text.append(text)

    def _update_batch_progress(self, value):
        """更新批量测试进度"""
        self.batch_progress.setValue(value)

    def select_lrc_file(self):
        """选择LRC歌词文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择LRC歌词文件", "", "LRC文件 (*.lrc);;所有文件 (*)"
        )
        if file_path:
            self.lrc_file_path = file_path
            self.lrc_file_label.setText(os.path.basename(file_path))
            self.update_singing_result.emit(f"已选择LRC文件: {os.path.basename(file_path)}")

    def clear_lrc_file(self):
        """清除LRC文件选择"""
        self.lrc_file_path = ""
        self.lrc_file_label.setText("未选择LRC文件")
        self.update_singing_result.emit("已清除LRC文件选择")

    def load_lrc_file_content(self, file_path):
        """加载LRC文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content
        except Exception as e:
            self.update_singing_result.emit(f"读取LRC文件失败: {str(e)}")
            return None

def main():
    """主函数"""
    # 设置高DPI支持（必须在QApplication创建之前）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AI桌宠 WebAPI 测试工具")
    app.setApplicationVersion("1.0")

    # 创建主窗口
    window = WebAPITester()
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
