#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多显示器字幕功能集成测试

测试完整的多显示器字幕功能，包括：
1. UI配置界面
2. 消息队列通信
3. 字幕管理器显示器选择
4. 实时字幕显示位置更新
"""

import sys
import json
import os
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QTextEdit, QFormLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class MultiMonitorSubtitleTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多显示器字幕功能集成测试")
        self.setGeometry(100, 100, 900, 700)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("多显示器字幕功能集成测试")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 配置信息显示
        self.config_info = QTextEdit()
        self.config_info.setMaximumHeight(150)
        layout.addWidget(QLabel("当前配置信息："))
        layout.addWidget(self.config_info)
        
        # 显示器信息
        self.monitor_info = QTextEdit()
        self.monitor_info.setMaximumHeight(200)
        layout.addWidget(QLabel("检测到的显示器信息："))
        layout.addWidget(self.monitor_info)
        
        # 配置控制面板
        config_group = QWidget()
        config_layout = QFormLayout(config_group)
        
        # 显示器选择
        self.monitor_combo = QComboBox()
        config_layout.addRow("选择显示器：", self.monitor_combo)
        
        # 位置选择
        self.position_combo = QComboBox()
        positions = [
            ("屏幕中央", "center"),
            ("屏幕上方", "top"),
            ("屏幕下方", "bottom"),
            ("左上角", "top_left"),
            ("右上角", "top_right"),
            ("左下角", "bottom_left"),
            ("右下角", "bottom_right")
        ]
        for display_name, value in positions:
            self.position_combo.addItem(display_name, value)
        config_layout.addRow("显示位置：", self.position_combo)
        
        # X偏移
        self.x_offset = QSpinBox()
        self.x_offset.setRange(-2000, 2000)
        config_layout.addRow("X偏移：", self.x_offset)
        
        # Y偏移
        self.y_offset = QSpinBox()
        self.y_offset.setRange(-2000, 2000)
        config_layout.addRow("Y偏移：", self.y_offset)
        
        layout.addWidget(QLabel("配置设置："))
        layout.addWidget(config_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新显示器列表")
        refresh_btn.clicked.connect(self.refresh_monitors)
        button_layout.addWidget(refresh_btn)
        
        load_config_btn = QPushButton("加载配置")
        load_config_btn.clicked.connect(self.load_config)
        button_layout.addWidget(load_config_btn)
        
        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_config_btn)
        
        test_subtitle_btn = QPushButton("测试字幕显示")
        test_subtitle_btn.clicked.connect(self.test_subtitle_display)
        button_layout.addWidget(test_subtitle_btn)
        
        layout.addLayout(button_layout)
        
        # 测试按钮组
        test_layout = QHBoxLayout()
        
        test_monitor_change_btn = QPushButton("测试显示器切换")
        test_monitor_change_btn.clicked.connect(self.test_monitor_change)
        test_layout.addWidget(test_monitor_change_btn)
        
        test_position_change_btn = QPushButton("测试位置切换")
        test_position_change_btn.clicked.connect(self.test_position_change)
        test_layout.addWidget(test_position_change_btn)
        
        test_offset_change_btn = QPushButton("测试偏移调整")
        test_offset_change_btn.clicked.connect(self.test_offset_change)
        test_layout.addWidget(test_offset_change_btn)
        
        layout.addWidget(QLabel("功能测试："))
        layout.addLayout(test_layout)
        
        # 测试日志
        self.test_log = QTextEdit()
        self.test_log.setMaximumHeight(150)
        layout.addWidget(QLabel("测试日志："))
        layout.addWidget(self.test_log)
        
        # 连接事件
        self.monitor_combo.currentIndexChanged.connect(self.on_monitor_changed)
        self.position_combo.currentIndexChanged.connect(self.on_position_changed)
        self.x_offset.valueChanged.connect(self.on_offset_changed)
        self.y_offset.valueChanged.connect(self.on_offset_changed)
        
        # 初始化
        self.refresh_monitors()
        self.load_config()
        
    def log_message(self, message):
        """添加测试日志"""
        current_time = time.strftime("%H:%M:%S")
        self.test_log.append(f"[{current_time}] {message}")
        print(f"[{current_time}] {message}")
        
    def refresh_monitors(self):
        """刷新显示器列表"""
        try:
            from PyQt5.QtWidgets import QDesktopWidget
            from PyQt5.QtGui import QGuiApplication
            
            # 清空下拉框
            self.monitor_combo.clear()
            monitor_info_text = ""
            
            # 获取所有屏幕
            desktop = QDesktopWidget()
            screen_count = desktop.screenCount()
            
            monitor_info_text += f"检测到 {screen_count} 个显示器\n\n"
            
            # 获取更详细的屏幕信息
            app = QGuiApplication.instance()
            if app:
                screens = app.screens()
                
                for i, screen in enumerate(screens):
                    # 获取屏幕几何信息
                    geometry = screen.geometry()
                    available_geometry = screen.availableGeometry()
                    
                    # 获取屏幕名称
                    screen_name = screen.name() if hasattr(screen, 'name') else f"显示器 {i+1}"
                    
                    # 获取屏幕分辨率
                    width = geometry.width()
                    height = geometry.height()
                    
                    # 检查是否是主屏幕
                    is_primary = screen == app.primaryScreen()
                    primary_text = " (主屏幕)" if is_primary else ""
                    
                    # 创建显示文本
                    display_text = f"{screen_name}: {width}x{height}{primary_text}"
                    self.monitor_combo.addItem(display_text, i)
                    
                    # 添加详细信息
                    monitor_info_text += f"显示器 {i+1}: {screen_name}\n"
                    monitor_info_text += f"  分辨率: {width} x {height}\n"
                    monitor_info_text += f"  位置: ({geometry.x()}, {geometry.y()})\n"
                    monitor_info_text += f"  可用区域: {available_geometry.width()} x {available_geometry.height()}\n"
                    monitor_info_text += f"  可用位置: ({available_geometry.x()}, {available_geometry.y()})\n"
                    monitor_info_text += f"  DPI: {screen.logicalDotsPerInch()}\n"
                    monitor_info_text += f"  主屏幕: {'是' if is_primary else '否'}\n\n"
            
            self.monitor_info.setText(monitor_info_text)
            self.log_message(f"检测到 {screen_count} 个显示器")
            
        except Exception as e:
            error_msg = f"刷新显示器列表失败: {e}"
            self.monitor_info.setText(error_msg)
            self.log_message(error_msg)
            
            # 添加默认选项
            self.monitor_combo.clear()
            self.monitor_combo.addItem("主显示器", 0)
    
    def load_config(self):
        """加载配置"""
        try:
            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                subtitle_config = config.get('subtitle', {})
                
                # 显示配置信息
                config_text = f"字幕配置信息:\n"
                config_text += f"显示器索引: {subtitle_config.get('display_monitor', 0)}\n"
                config_text += f"显示位置: {subtitle_config.get('display_position', 'center')}\n"
                config_text += f"X偏移: {subtitle_config.get('display_offset_x', 0)}\n"
                config_text += f"Y偏移: {subtitle_config.get('display_offset_y', 0)}\n"
                config_text += f"字体大小: {subtitle_config.get('font_size', 24)}\n"
                config_text += f"字体系列: {subtitle_config.get('font_family', 'Microsoft YaHei')}\n"
                
                self.config_info.setText(config_text)
                
                # 设置UI控件值
                monitor_index = subtitle_config.get('display_monitor', 0)
                for i in range(self.monitor_combo.count()):
                    if self.monitor_combo.itemData(i) == monitor_index:
                        self.monitor_combo.setCurrentIndex(i)
                        break
                
                # 设置位置
                position = subtitle_config.get('display_position', 'center')
                for i in range(self.position_combo.count()):
                    if self.position_combo.itemData(i) == position:
                        self.position_combo.setCurrentIndex(i)
                        break
                
                # 设置偏移
                self.x_offset.setValue(subtitle_config.get('display_offset_x', 0))
                self.y_offset.setValue(subtitle_config.get('display_offset_y', 0))
                
                self.log_message("配置加载成功")
            else:
                self.log_message("配置文件不存在")
                
        except Exception as e:
            self.log_message(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            config_path = "config.json"
            config = {}
            
            # 加载现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新字幕配置
            subtitle_config = config.setdefault('subtitle', {})
            
            # 保存显示器选择
            monitor_index = self.monitor_combo.currentData()
            if monitor_index is not None:
                subtitle_config['display_monitor'] = monitor_index
            
            # 保存位置
            position = self.position_combo.currentData()
            if position is not None:
                subtitle_config['display_position'] = position
            
            # 保存偏移
            subtitle_config['display_offset_x'] = self.x_offset.value()
            subtitle_config['display_offset_y'] = self.y_offset.value()
            
            # 保存配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            self.log_message("配置保存成功")
            self.load_config()  # 重新加载显示
            
        except Exception as e:
            self.log_message(f"保存配置失败: {e}")
    
    def on_monitor_changed(self):
        """显示器选择变化"""
        monitor_index = self.monitor_combo.currentData()
        if monitor_index is not None:
            self.log_message(f"显示器已切换到: {monitor_index}")
    
    def on_position_changed(self):
        """位置选择变化"""
        position = self.position_combo.currentData()
        if position is not None:
            self.log_message(f"显示位置已切换到: {position}")
    
    def on_offset_changed(self):
        """偏移量变化"""
        x_offset = self.x_offset.value()
        y_offset = self.y_offset.value()
        self.log_message(f"偏移量已调整为: X={x_offset}, Y={y_offset}")
    
    def test_subtitle_display(self):
        """测试字幕显示功能"""
        try:
            # 这里应该调用实际的字幕显示功能
            # 由于这是独立测试，我们模拟一个测试窗口
            
            monitor_index = self.monitor_combo.currentData() or 0
            position = self.position_combo.currentData() or "center"
            x_offset = self.x_offset.value()
            y_offset = self.y_offset.value()
            
            self.log_message(f"测试字幕显示: 显示器={monitor_index}, 位置={position}, 偏移=({x_offset}, {y_offset})")
            
            # 创建测试字幕窗口
            from test_multi_monitor import SubtitleTestWindow
            
            if hasattr(self, 'test_window') and self.test_window:
                self.test_window.close()
            
            self.test_window = SubtitleTestWindow(monitor_index, position, x_offset, y_offset)
            self.test_window.show()
            
            self.log_message("字幕测试窗口已创建")
            
        except Exception as e:
            self.log_message(f"测试字幕显示失败: {e}")
    
    def test_monitor_change(self):
        """测试显示器切换"""
        try:
            current_index = self.monitor_combo.currentIndex()
            next_index = (current_index + 1) % self.monitor_combo.count()
            self.monitor_combo.setCurrentIndex(next_index)
            self.log_message(f"自动切换到下一个显示器: {next_index}")
        except Exception as e:
            self.log_message(f"测试显示器切换失败: {e}")
    
    def test_position_change(self):
        """测试位置切换"""
        try:
            current_index = self.position_combo.currentIndex()
            next_index = (current_index + 1) % self.position_combo.count()
            self.position_combo.setCurrentIndex(next_index)
            self.log_message(f"自动切换到下一个位置: {self.position_combo.currentText()}")
        except Exception as e:
            self.log_message(f"测试位置切换失败: {e}")
    
    def test_offset_change(self):
        """测试偏移调整"""
        try:
            import random
            x_offset = random.randint(-500, 500)
            y_offset = random.randint(-500, 500)
            self.x_offset.setValue(x_offset)
            self.y_offset.setValue(y_offset)
            self.log_message(f"随机调整偏移量: X={x_offset}, Y={y_offset}")
        except Exception as e:
            self.log_message(f"测试偏移调整失败: {e}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("多显示器字幕功能集成测试")
    app.setApplicationVersion("1.0.0")
    
    # 创建主窗口
    window = MultiMonitorSubtitleTest()
    window.show()
    
    # 运行应用程序
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
