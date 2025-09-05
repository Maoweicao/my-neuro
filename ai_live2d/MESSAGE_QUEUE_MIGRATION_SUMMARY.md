# 消息队列通信系统迁移总结

## 迁移概述

成功将 `main.py` 和 `UI.py` 之间的通信机制从 **socket 通信** 迁移到 **共享消息队列** 系统，提高了进程间通信的可靠性和稳定性。

## 迁移原因

1. **Socket 连接问题**: 原系统经常出现 `WinError 10061` (连接被拒绝) 错误
2. **连接超时**: Socket 连接超时导致消息发送失败
3. **复杂性**: 长度前缀协议增加了实现复杂度
4. **可靠性**: TCP socket 在本地进程通信中不够稳定

## 新系统架构

### 消息队列系统 (`utils/message_queue.py`)

- **混合存储**: 内存队列 + 文件持久化
- **优先级支持**: 3级优先级 (1=高, 2=中, 3=低)
- **线程安全**: 使用锁机制保证并发安全
- **消息持久化**: JSON 文件存储，重启后可恢复
- **处理器注册**: 支持按消息类型注册处理函数

### 核心功能

```python
# 发送消息
mq.send_message("interrupt", {"action": "stop_audio"}, priority=1)

# 接收消息
message = mq.receive_message(timeout=1.0)

# 注册处理器
mq.register_handler("interrupt", interrupt_handler)

# 启动监听器
mq.start_listener()
```

## 文件变更

### 1. 新增文件
- `utils/message_queue.py` - 消息队列核心实现

### 2. 主要变更

#### `main.py` 变更
- ❌ 移除: `start_interrupt_listener()` socket 监听
- ✅ 新增: `start_message_listener()` 消息队列监听
- ❌ 移除: `_handle_interrupt_connection()` socket 处理
- ✅ 新增: 各种消息处理器
  - `_handle_interrupt_message()`
  - `_handle_play_audio_message()`
  - `_handle_show_subtitle_message()`
  - `_handle_custom_action_message()`
  - `_handle_show_action_buttons_message()`
  - `_handle_hide_action_buttons_message()`

#### `UI.py` 变更
- ❌ 移除: `_send_socket_data()` socket 发送方法
- ✅ 新增: `_send_message_queue_data()` 消息队列发送方法
- 🔄 更新: 所有 WebAPI 处理器使用新的通信方法
  - 对话 API 处理器
  - 唱歌 API 处理器
  - 歌词 API 处理器
  - 中断请求处理器

## 支持的消息类型

| 消息类型 | 用途 | 优先级 |
|---------|------|--------|
| `interrupt` | 中断音频播放 | 1 (高) |
| `play_audio` | 播放音频文件 | 1 (高) |
| `show_subtitle` | 显示字幕 | 2 (中) |
| `custom_action` | 自定义动作 | 2 (中) |
| `show_action_buttons` | 显示操作按钮 | 2 (中) |
| `hide_action_buttons` | 隐藏操作按钮 | 2 (中) |
| `shutdown` | 关闭程序 | 1 (高) |

## 消息数据格式

```json
{
  "type": "play_audio",
  "data": {
    "audio_data": "base64_encoded_data",
    "audio_format": "wav"
  },
  "priority": 1,
  "timestamp": 1756993032.821,
  "id": "play_audio_1756993032821"
}
```

## 性能优化

1. **内存队列**: 优先使用内存中的 `queue.Queue` 提高响应速度
2. **文件回退**: 内存队列为空时从文件读取，确保消息不丢失
3. **队列限制**: 文件队列最多保留 100 条消息，防止文件过大
4. **超时机制**: 可配置的接收超时，避免阻塞
5. **锁机制**: 最小化锁的使用范围，提高并发性能

## 兼容性保证

- **消息格式**: 保持与原 socket 消息相同的数据结构
- **功能完整**: 所有原有的通信功能都得到保留
- **错误处理**: 增强的错误处理和日志记录
- **向后兼容**: 可以轻松切换回 socket 通信（如果需要）

## 测试验证

创建了两个测试文件验证系统功能：

1. `test_message_queue_integration.py` - 基础功能测试
2. `test_integration_final.py` - 集成测试

测试结果：✅ 所有测试通过

## 使用方法

1. **启动顺序**：
   ```bash
   # 先启动main.py
   python main.py
   
   # 再启动UI.py
   python UI.py
   ```

2. **查看消息队列文件**：
   ```bash
   # 消息队列存储在项目根目录
   type message_queue.json
   ```

3. **监控日志**：
   - main.py 日志会显示接收到的消息
   - UI.py 日志会显示发送的消息状态

## 优势总结

✅ **可靠性提升**: 消除了 socket 连接失败问题  
✅ **简化实现**: 移除了复杂的长度前缀协议  
✅ **持久化**: 消息可以在重启后恢复  
✅ **优先级**: 重要消息优先处理  
✅ **线程安全**: 支持多线程并发访问  
✅ **易于调试**: JSON 格式便于查看和调试  
✅ **扩展性**: 容易添加新的消息类型和处理器  

## 注意事项

1. 确保 `utils/` 目录存在且可写
2. 消息队列文件 `message_queue.json` 会自动创建
3. 如果遇到权限问题，检查文件写入权限
4. 监听器运行在后台线程，程序退出时会自动停止

---

**迁移完成时间**: 2025年1月25日  
**测试状态**: ✅ 全部通过  
**建议**: 在生产环境使用前进行充分测试
