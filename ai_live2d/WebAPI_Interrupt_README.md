# WebAPI 打断功能

## 概述

WebAPI 现在支持打断功能，可以中断当前正在进行的AI输出和语音播放操作。

## 新增API端点

### POST /api/interrupt

打断当前正在进行的AI输出和语音播放。

**请求格式：**
```json
{
  "api_key": "your_api_key"  // 可选，如果配置了API密钥验证
}
```

**响应格式：**
```json
{
  "status": "success",
  "message": "已打断当前AI输出和语音播放",
  "timestamp": 1640995200.123
}
```

**可能的响应：**
- `success`: 成功打断
- `warning`: 没有正在进行的操作需要打断
- `error`: 打断失败

## 使用方法

### 1. Python代码示例

```python
import requests
import json

# 发送打断请求
response = requests.post(
    "http://127.0.0.1:8888/api/interrupt",
    json={"api_key": "your_api_key"},  # 如果需要
    headers={"Content-Type": "application/json"}
)

result = response.json()
print(result)
```

### 2. cURL命令示例

```bash
# 基本打断请求
curl -X POST http://127.0.0.1:8888/api/interrupt \
  -H "Content-Type: application/json" \
  -d '{}'

# 带API密钥的打断请求
curl -X POST http://127.0.0.1:8888/api/interrupt \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your_api_key"}'
```

### 3. 测试脚本

运行测试脚本来验证打断功能：

```bash
python test_interrupt_demo.py
```

或使用现有的WebAPI测试脚本：

```bash
python webapi_test_script.py
```

## 打断机制

打断功能会执行以下操作：

1. **停止TTS播放**: 尝试停止当前正在播放的语音
2. **停止Live2D动作**: 停止所有正在播放的Live2D动画
3. **创建打断信号**: 生成`interrupt_signal.tmp`文件用于进程间通信
4. **记录日志**: 在系统日志中记录打断操作

## 注意事项

- 打断功能是尽力而为的，不能保证100%成功
- 如果没有正在进行的操作，打断请求会返回警告但不报错
- 建议在需要时使用打断功能，避免频繁调用

## 集成到现有代码

如果您想在自己的应用中集成打断功能，只需要：

1. 在用户界面添加一个"打断"按钮
2. 按钮点击时调用`/api/interrupt`端点
3. 处理响应并向用户显示结果

## 故障排除

如果打断功能不工作：

1. 检查WebAPI服务是否正在运行
2. 确认API密钥（如果配置了）
3. 查看日志文件中的错误信息
4. 确保有足够的权限访问相关资源
