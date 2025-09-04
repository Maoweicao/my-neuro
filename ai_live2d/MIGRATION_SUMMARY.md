# 音频播放和动作按钮迁移总结

## 迁移概述

本次迁移将UI.py中的音频播放功能和动作按钮管理功能移动到了main.py中的PetService类中，以解决UI界面卡死的问题。

## 迁移内容

### 1. 音频播放功能迁移

#### 从UI.py移除的方法：
- `_convert_audio_format()` - 音频格式检测和转换
- `_play_singing_audio()` - 唱歌音频播放
- `_play_audio_fallback()` - 音频播放回退方法
- `_get_motion_index_by_name()` - 获取动作索引

#### 迁移到main.py PetService类的方法：
- `play_singing_audio()` - 播放唱歌音频
- `_convert_audio_format()` - 音频格式检测和转换
- `_play_singing_audio()` - 播放唱歌音频（内部方法）
- `_play_audio_fallback()` - 音频播放回退方法
- `_get_motion_index_by_name()` - 获取动作索引

### 2. 动作按钮功能迁移

#### 从UI.py移除的内容：
- `ActionButtonsWindow` 的创建和引用
- `interrupt_current_operations()` 方法（保留但修改为发送信号）
- `trigger_custom_action()` 方法（修改为发送信号）
- 所有对 `actionButtonsWindow` 的引用

#### 迁移到main.py PetService类的内容：
- `initialize_action_buttons()` - 初始化动作按钮窗口
- `interrupt_current_operations()` - 中断当前操作
- `trigger_custom_action()` - 触发自定义动作
- `show_action_buttons()` - 显示动作按钮
- `hide_action_buttons()` - 隐藏动作按钮

### 3. 进程间通信改进

#### 新增功能：
- 通过socket通信在UI.py和main.py之间传递音频播放请求
- 支持音频数据通过base64编码传输
- 支持自定义动作请求
- 支持中断信号处理

## 技术实现

### 1. 音频播放流程
```
UI.py (WebAPIHandler) -> Socket -> main.py (PetService) -> 音频播放
```

### 2. 动作按钮流程
```
UI.py (trigger_custom_action) -> Socket -> main.py (PetService) -> Live2D动作
```

### 3. 中断流程
```
UI.py (interrupt_current_operations) -> Socket -> main.py (PetService) -> 中断操作
```

## 优势

1. **解决UI卡死问题**：音频播放不再阻塞UI主线程
2. **更好的架构分离**：业务逻辑与UI逻辑分离
3. **进程间通信**：使用socket实现可靠的进程间通信
4. **错误处理改进**：更好的错误处理和回退机制
5. **代码可维护性**：功能集中管理，便于维护

## 测试

创建了 `test_migration.py` 脚本来测试迁移后的功能：
- 音频播放测试
- 自定义动作测试
- 中断功能测试

## 使用方法

1. 启动main.py服务：`python main.py`
2. 启动UI界面：正常启动应用程序
3. 通过WebAPI发送音频播放请求
4. 使用动作按钮触发自定义动作
5. 使用中断功能停止当前操作

## 注意事项

1. 需要确保main.py服务正常运行
2. socket通信端口为8889
3. 音频数据通过base64编码传输
4. 动作按钮配置需要在config.json中设置

## 修复记录

### 2025-09-04 修复内容

#### 1. 修复WebAPI唱歌错误
- **问题**：`'WebAPIHandler' object has no attribute '_convert_audio_format'`
- **原因**：UI.py中的`_process_singing_request`方法仍然调用已移除的`_convert_audio_format`方法
- **修复**：修改`_process_singing_request`方法，直接将音频数据发送给main.py处理

#### 2. 修复动作按钮显示问题
- **问题**：动作按钮搬到main.py后界面上没有显示
- **原因**：缺少显示/隐藏动作按钮的控制逻辑
- **修复**：
  - 在main.py中添加`show_action_buttons`和`hide_action_buttons`方法
  - 在UI.py中添加通过socket发送显示/隐藏信号的逻辑
  - 确保动作按钮窗口正确初始化和定位

#### 3. 进程间通信增强
- **新增信号类型**：
  - `show_action_buttons` - 显示动作按钮
  - `hide_action_buttons` - 隐藏动作按钮
- **触发时机**：
  - BAT启动时显示动作按钮（如果启用）
  - BAT停止时隐藏动作按钮
  - 动作按钮开关状态变化时相应显示/隐藏

#### 4. 代码清理
- 移除UI.py中所有对已迁移方法的调用
- 确保所有方法调用都有对应的实现
- 验证语法正确性

## 测试验证

创建了以下测试脚本：
- `test_migration.py` - 测试音频播放和动作按钮迁移
- `test_action_buttons_display.py` - 测试动作按钮显示功能

## 验证步骤

1. 启动main.py服务：`python main.py`
2. 启动UI界面：正常启动应用程序
3. 在设置中启用动作按钮开关
4. 启动BAT脚本，观察动作按钮是否显示
5. 停止BAT脚本，观察动作按钮是否隐藏
6. 使用WebAPI发送唱歌请求，验证音频播放正常
