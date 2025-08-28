# WebAPI 测试脚本说明

根据您提供的WebAPI使用说明，我创建了多个测试脚本来验证API功能。

## 📋 测试脚本列表

### 1. `webapi_test_script.py` - 完整测试脚本
**功能最全面的测试工具**
- ✅ 自动批量测试
- ✅ 单条消息测试
- ✅ 错误处理测试
- ✅ 详细的测试报告
- ✅ 交互式模式

```bash
python webapi_test_script.py
```

### 2. `quick_test.py` - 快速测试脚本  
**最简单快速的测试方式**
- ✅ 一键快速测试
- ✅ 自定义配置测试
- ✅ 简洁的输出格式

```bash
python quick_test.py
```

### 3. `curl_test.py` - cURL样式测试
**命令行专家的选择**
- ✅ 模拟cURL命令格式
- ✅ 支持命令行参数
- ✅ 显示实际HTTP请求过程

```bash
# 基本用法
python curl_test.py --message "你好"

# 带API密钥
python curl_test.py --message "你好" --api-key "your-key"

# 检查状态
python curl_test.py --status

# 自定义服务器
python curl_test.py --host 192.168.1.100 --port 8888 --message "测试"
```

### 4. `webapi_client.py` - 交互式客户端
**持续对话测试**
- ✅ 类似聊天的交互体验
- ✅ 持续会话测试
- ✅ 实时响应显示

```bash
python webapi_client.py
```

### 5. `test_webapi.py` - 原始测试脚本
**传统的测试方式**
- ✅ 基础功能测试
- ✅ 错误场景测试

```bash
python test_webapi.py
```

## 🚀 快速开始

### 方法一：使用批处理菜单
```bash
# 双击运行或在命令行执行
WebAPI_Tools.bat
```

### 方法二：直接运行脚本
```bash
# 最快速的测试
python quick_test.py

# 最全面的测试  
python webapi_test_script.py

# 类似cURL的测试
python curl_test.py --message "你好"
```

## 📝 API 格式验证

所有测试脚本都严格按照您提供的API格式：

### 请求格式
```json
POST /api/chat
Content-Type: application/json

{
  "message": "你好",
  "api_key": "你的密钥" // 可选
}
```

### 响应格式
```json
{
  "response": "LLM回复内容", 
  "status": "success"
}
```

## 🔧 测试配置

### 默认配置
- **服务器**: 127.0.0.1
- **端口**: 8888  
- **API密钥**: 无（可选配置）
- **超时**: 30秒

### 自定义配置
所有脚本都支持自定义配置：
- 服务器地址
- 端口号
- API密钥
- 超时时间

## 📊 测试内容

### 基础功能测试
- ✅ 服务状态检查 (`GET /api/status`)
- ✅ 正常聊天消息 (`POST /api/chat`)
- ✅ 带API密钥的请求
- ✅ 响应时间测试

### 错误处理测试
- ✅ 空消息处理
- ✅ 缺少字段处理  
- ✅ 无效JSON处理
- ✅ 连接超时处理
- ✅ 服务不可用处理

### 压力测试
- ✅ 批量连续请求
- ✅ 长文本消息
- ✅ 并发请求模拟

## 🎯 使用建议

1. **开发阶段**: 使用 `quick_test.py` 快速验证
2. **测试阶段**: 使用 `webapi_test_script.py` 全面测试
3. **调试阶段**: 使用 `curl_test.py` 查看详细HTTP交互
4. **演示阶段**: 使用 `webapi_client.py` 展示对话效果

## 🔍 故障排除

### 常见问题
1. **连接失败**: 检查WebAPI服务是否启动
2. **超时错误**: 检查LLM配置是否正确
3. **认证失败**: 验证API密钥设置
4. **格式错误**: 确认请求JSON格式正确

### 调试技巧
```bash
# 查看详细HTTP交互
python curl_test.py --message "测试" 

# 检查服务状态
python curl_test.py --status

# 测试不同配置
python quick_test.py  # 选择自定义测试
```

Happy Testing! 🎉
