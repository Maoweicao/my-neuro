# WebAPI 快速启动指南

## 🚀 快速开始

### 1. 基本配置

1. **启动程序**
   ```bash
   python UI.py
   ```

2. **配置LLM**（必需）
   - 切换到"LLM配置"标签页
   - 填入API Key和API URL
   - 选择或输入模型名称
   - 保存配置

3. **启用WebAPI**
   - 切换到"设置"标签页
   - 勾选"启用WebAPI输入"
   - 配置端口（默认8888）
   - 可选：设置API密钥

4. **启动服务**
   - 点击"启动服务"按钮
   - 看到绿色"运行中"状态即表示成功

### 2. 测试连接

使用内置测试工具：
```bash
python test_webapi.py
```

或者手动测试：
```bash
curl http://127.0.0.1:8888/api/status
```

### 3. 发送消息

```bash
curl -X POST http://127.0.0.1:8888/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

### 4. 交互式聊天

```bash
python webapi_client.py
```

## ⚡ 一键启动

双击运行 `WebAPI_Tools.bat` 获得图形化菜单。

## 🔧 常见问题

**Q: 端口被占用怎么办？**
A: 在设置中更改端口号，或者停止占用该端口的程序。

**Q: LLM没有响应？**
A: 检查LLM配置是否正确，API Key是否有效。

**Q: 连接被拒绝？**
A: 确保服务已启动，检查IP和端口是否正确。

**Q: 如何启用安全验证？**
A: 在WebAPI设置中填入API密钥，请求时需要包含该密钥。

## 📚 更多信息

查看完整文档：`WebAPI_Usage.md`
