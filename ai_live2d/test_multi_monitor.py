#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多显示器字幕功能测试脚本

测试功能：
1. 检测可用显示器
2. 测试显示器选择功能
3. 验证字幕在不同显示器上的显示效果
"""

import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QTextEdit
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QDesktopWidget, QGuiApplication

class MultiMonitorTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多显示器字幕测试")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("多显示器字幕功能测试")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 显示器信息
        self.monitor_info = QTextEdit()
        self.monitor_info.setMaximumHeight(200)
        layout.addWidget(QLabel("检测到的显示器信息："))
        layout.addWidget(self.monitor_info)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        # 显示器选择
        control_layout.addWidget(QLabel("选择显示器："))
        self.monitor_combo = QComboBox()
        control_layout.addWidget(self.monitor_combo)
        
        # 位置选择
        control_layout.addWidget(QLabel("位置："))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["屏幕中央", "屏幕顶部", "屏幕底部", "左上角", "右上角", "左下角", "右下角"])
        control_layout.addWidget(self.position_combo)
        
        # X偏移
        control_layout.addWidget(QLabel("X偏移："))
        self.x_offset = QSpinBox()
        self.x_offset.setRange(-2000, 2000)
        control_layout.addWidget(self.x_offset)
        
        # Y偏移
        control_layout.addWidget(QLabel("Y偏移："))
        self.y_offset = QSpinBox()
        self.y_offset.setRange(-2000, 2000)
        control_layout.addWidget(self.y_offset)
        
        layout.addLayout(control_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新显示器列表")
        refresh_btn.clicked.connect(self.refresh_monitors)
        button_layout.addWidget(refresh_btn)
        
        test_btn = QPushButton("测试字幕显示")
        test_btn.clicked.connect(self.test_subtitle)
        button_layout.addWidget(test_btn)
        
        load_config_btn = QPushButton("加载配置")
        load_config_btn.clicked.connect(self.load_config)
        button_layout.addWidget(load_config_btn)
        
        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_config_btn)
        
        layout.addLayout(button_layout)
        
        # 测试窗口引用
        self.test_windows = []
        
        # 初始化
        self.refresh_monitors()
        self.load_config()
        
    def refresh_monitors(self):
        """刷新显示器列表"""
        try:
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
            else:
                # 如果获取不到详细信息，使用基础方法
                for i in range(screen_count):
                    geometry = desktop.screenGeometry(i)
                    width = geometry.width()
                    height = geometry.height()
                    is_primary = i == desktop.primaryScreen()
                    primary_text = " (主屏幕)" if is_primary else ""
                    
                    display_text = f"显示器 {i+1}: {width}x{height}{primary_text}"
                    self.monitor_combo.addItem(display_text, i)
                    
                    monitor_info_text += f"显示器 {i+1}\n"
                    monitor_info_text += f"  分辨率: {width} x {height}\n"
                    monitor_info_text += f"  位置: ({geometry.x()}, {geometry.y()})\n"
                    monitor_info_text += f"  主屏幕: {'是' if is_primary else '否'}\n\n"
            
            self.monitor_info.setText(monitor_info_text)
            print(f"检测到 {screen_count} 个显示器")
            
        except Exception as e:
            error_msg = f"刷新显示器列表失败: {e}"
            self.monitor_info.setText(error_msg)
            print(error_msg)
            
            # 添加默认选项
            self.monitor_combo.clear()
            self.monitor_combo.addItem("主显示器", 0)
    
    def test_subtitle(self):
        """测试字幕显示"""
        try:
            # 关闭之前的测试窗口
            for window in self.test_windows:
                window.close()
            self.test_windows.clear()
            
            # 获取选择的显示器
            monitor_index = self.monitor_combo.currentData()
            if monitor_index is None:
                monitor_index = 0
            
            # 获取位置设置
            position = self.position_combo.currentText()
            x_offset = self.x_offset.value()
            y_offset = self.y_offset.value()
            
            # 创建测试窗口
            test_window = SubtitleTestWindow(monitor_index, position, x_offset, y_offset)
            test_window.show()
            self.test_windows.append(test_window)
            
            print(f"在显示器 {monitor_index} 上测试字幕显示")
            
        except Exception as e:
            print(f"测试字幕显示失败: {e}")
    
    def load_config(self):
        """加载配置"""
        try:
            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                subtitle_config = config.get('subtitle', {})
                
                # 设置显示器选择
                monitor_index = subtitle_config.get('display_monitor', 0)
                for i in range(self.monitor_combo.count()):
                    if self.monitor_combo.itemData(i) == monitor_index:
                        self.monitor_combo.setCurrentIndex(i)
                        break
                
                # 设置位置
                position = subtitle_config.get('display_position', 'center')
                position_map = {
                    'center': '屏幕中央',
                    'top': '屏幕顶部',
                    'bottom': '屏幕底部',
                    'top_left': '左上角',
                    'top_right': '右上角',
                    'bottom_left': '左下角',
                    'bottom_right': '右下角'
                }
                position_text = position_map.get(position, '屏幕中央')
                index = self.position_combo.findText(position_text)
                if index >= 0:
                    self.position_combo.setCurrentIndex(index)
                
                # 设置偏移
                self.x_offset.setValue(subtitle_config.get('display_offset_x', 0))
                self.y_offset.setValue(subtitle_config.get('display_offset_y', 0))
                
                print("配置加载成功")
            else:
                print("配置文件不存在")
                
        except Exception as e:
            print(f"加载配置失败: {e}")
    
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
            position_text = self.position_combo.currentText()
            position_map = {
                '屏幕中央': 'center',
                '屏幕顶部': 'top',
                '屏幕底部': 'bottom',
                '左上角': 'top_left',
                '右上角': 'top_right',
                '左下角': 'bottom_left',
                '右下角': 'bottom_right'
            }
            position = position_map.get(position_text, 'center')
            subtitle_config['display_position'] = position
            
            # 保存偏移
            subtitle_config['display_offset_x'] = self.x_offset.value()
            subtitle_config['display_offset_y'] = self.y_offset.value()
            
            # 保存配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print("配置保存成功")
            
        except Exception as e:
            print(f"保存配置失败: {e}")


class SubtitleTestWindow(QWidget):
    """字幕测试窗口"""
    
    def __init__(self, monitor_index, position, x_offset, y_offset):
        super().__init__()
        self.monitor_index = monitor_index
        self.position = position
        self.x_offset = x_offset
        self.y_offset = y_offset
        
        self.setWindowTitle(f"字幕测试 - 显示器 {monitor_index + 1}")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 100);
                border: 2px solid #56B6C2;
                border-radius: 15px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(f"显示器 {monitor_index + 1} 字幕测试")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 测试文本
        self.test_label = QLabel("这是一个多显示器字幕测试\n正在测试字幕在不同显示器上的显示效果")
        self.test_label.setAlignment(Qt.AlignCenter)
        self.test_label.setWordWrap(True)
        layout.addWidget(self.test_label)
        
        # 信息标签
        info_text = f"位置: {position}\nX偏移: {x_offset}\nY偏移: {y_offset}"
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 16px; color: #CCCCCC;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
        
        # 设置窗口位置和大小
        self.setup_window_geometry()
        
        # 启动动画定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_text)
        self.animation_timer.start(2000)  # 每2秒更新一次
        
        self.animation_step = 0
        
    def setup_window_geometry(self):
        """设置窗口几何位置"""
        try:
            # 获取目标显示器的几何信息
            desktop = QDesktopWidget()
            
            if self.monitor_index < desktop.screenCount():
                screen_geometry = desktop.screenGeometry(self.monitor_index)
            else:
                # 如果指定的显示器不存在，使用主显示器
                screen_geometry = desktop.screenGeometry(desktop.primaryScreen())
                print(f"显示器 {self.monitor_index} 不存在，使用主显示器")
            
            # 设置窗口大小
            window_width = 800
            window_height = 200
            
            # 根据位置计算坐标
            if self.position == "屏幕中央":
                x = screen_geometry.x() + (screen_geometry.width() - window_width) // 2
                y = screen_geometry.y() + (screen_geometry.height() - window_height) // 2
            elif self.position == "屏幕顶部":
                x = screen_geometry.x() + (screen_geometry.width() - window_width) // 2
                y = screen_geometry.y() + 50
            elif self.position == "屏幕底部":
                x = screen_geometry.x() + (screen_geometry.width() - window_width) // 2
                y = screen_geometry.y() + screen_geometry.height() - window_height - 50
            elif self.position == "左上角":
                x = screen_geometry.x() + 50
                y = screen_geometry.y() + 50
            elif self.position == "右上角":
                x = screen_geometry.x() + screen_geometry.width() - window_width - 50
                y = screen_geometry.y() + 50
            elif self.position == "左下角":
                x = screen_geometry.x() + 50
                y = screen_geometry.y() + screen_geometry.height() - window_height - 50
            elif self.position == "右下角":
                x = screen_geometry.x() + screen_geometry.width() - window_width - 50
                y = screen_geometry.y() + screen_geometry.height() - window_height - 50
            else:
                # 默认居中
                x = screen_geometry.x() + (screen_geometry.width() - window_width) // 2
                y = screen_geometry.y() + (screen_geometry.height() - window_height) // 2
            
            # 应用偏移
            x += self.x_offset
            y += self.y_offset
            
            # 设置窗口位置和大小
            self.setGeometry(x, y, window_width, window_height)
            
            print(f"窗口位置设置为: ({x}, {y}), 大小: {window_width}x{window_height}")
            
        except Exception as e:
            print(f"设置窗口几何位置失败: {e}")
    
    def animate_text(self):
        """文本动画"""
        texts = [
            "这是一个多显示器字幕测试\n正在测试字幕在不同显示器上的显示效果",
            f"当前显示器: {self.monitor_index + 1}\n位置: {self.position}",
            f"偏移量: X={self.x_offset}, Y={self.y_offset}\n字幕显示正常",
            "多显示器功能测试成功！\n可以在不同显示器上显示字幕"
        ]
        
        self.test_label.setText(texts[self.animation_step % len(texts)])
        self.animation_step += 1
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if hasattr(self, 'animation_timer'):
            self.animation_timer.stop()
        super().closeEvent(event)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("多显示器字幕测试")
    app.setApplicationVersion("1.0.0")
    
    # 创建主窗口
    window = MultiMonitorTest()
    window.show()
    
    # 运行应用程序
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
