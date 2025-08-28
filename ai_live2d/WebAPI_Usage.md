# WebAPI 功能使用说明

## 概述

WebAPI功能允许通过HTTP接口与系统进行交互，实现与前端输入相同的效果。用户可以通过POST请求发送消息，系统会将消息传递给LLM处理并返回响应。

## 功能特点

- 🌐 **HTTP接口**: 支持通过HTTP POST请求发送消息
- 🔐 **安全认证**: 可选的API密钥验证
- 📝 **日志记录**: 完整的请求响应日志
- 🚀 **简单集成**: 易于与其他系统集成
- 🛡️ **错误处理**: 完善的错误处理和状态码
- 🌍 **CORS支持**: 支持跨域请求

## 配置说明

### 1. 在设置页面启用WebAPI

1. 打开程序，切换到"设置"标签页
2. 找到"WebAPI输入设置"部分
3. 勾选"启用WebAPI输入"
4. 配置以下参数：
   - **监听端口**: 默认8888，可自定义
   - **绑定地址**: 默认127.0.0.1（本地），设置为0.0.0.0可监听所有网卡
   - **API密钥**: 可选，用于验证请求的安全性

### 2. 配置LLM

确保在"LLM配置"标签页中正确配置了：
- API Key
- API URL
- 模型名称
- 系统提示词

## 使用方法

### 1. 启动服务

在设置页面点击"启动服务"按钮，系统将启动WebAPI服务器。

### 2. 发送请求

#### 基本聊天请求

```bash
curl -X POST http://127.0.0.1:8888/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己"
  }'
```

#### 带API密钥的请求

```bash
curl -X POST http://127.0.0.1:8888/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今天天气怎么样？",
    "api_key": "your-secret-key"
  }'
```

#### 服务状态检查

```bash
curl http://127.0.0.1:8888/api/status
```

### 3. 响应格式

#### 成功响应

```json
{
  "response": "你好！我是肥牛，一个可爱的AI助手...",
  "status": "success",
  "timestamp": 1703123456.789
}
```

#### 错误响应

```json
{
  "error": "Missing 'message' field",
  "status": "error",
  "code": 400
}
```

## API 端点

### POST /api/chat

发送聊天消息给LLM处理。

**请求参数:**
- `message` (string, 必需): 要发送的消息内容
- `api_key` (string, 可选): API密钥（如果配置了验证）

**响应:**
- 成功: 200 OK，包含LLM的回复
- 错误: 4xx/5xx，包含错误信息

### GET /api/status

检查服务状态。

**响应:**
```json
{
  "status": "running",
  "message": "WebAPI服务正在运行"
}
```

## 测试工具

程序包含了测试脚本 `test_webapi.py`，可以用来测试WebAPI功能：

```bash
python test_webapi.py
```

该脚本会自动测试：
- 服务状态检查
- 基本聊天功能
- 错误处理
- API密钥验证

## 故障排除

### 1. 端口被占用

如果启动失败提示端口被占用，请：
- 更换端口号
- 检查是否有其他程序占用该端口
- 在Windows中使用 `netstat -ano | findstr :8888` 查看端口占用

### 2. 连接被拒绝

- 确保服务已启动
- 检查防火墙设置
- 验证IP地址和端口号

### 3. LLM响应错误

- 检查LLM配置是否正确
- 验证API Key是否有效
- 查看日志文件获取详细错误信息

### 4. API密钥验证失败

- 确保请求中包含正确的api_key字段
- 检查密钥是否与配置中的一致

## 安全建议

1. **使用API密钥**: 在生产环境中务必设置API密钥
2. **网络限制**: 考虑使用防火墙限制访问来源
3. **HTTPS**: 在生产环境中考虑使用反向代理提供HTTPS
4. **输入验证**: 注意输入内容的安全性，避免恶意内容

## 集成示例

### Python 客户端

```python
import requests

def send_message(message, host='127.0.0.1', port=8888, api_key=None):
    url = f"http://{host}:{port}/api/chat"
    data = {"message": message}
    if api_key:
        data["api_key"] = api_key
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise Exception(f"Error: {response.json().get('error', 'Unknown error')}")

# 使用示例
try:
    response = send_message("你好")
    print(f"AI回复: {response}")
except Exception as e:
    print(f"错误: {e}")
```

### JavaScript 客户端

```javascript
async function sendMessage(message, apiKey = null) {
    const url = 'http://127.0.0.1:8888/api/chat';
    const data = { message: message };
    if (apiKey) {
        data.api_key = apiKey;
    }
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (response.ok) {
            return result.response;
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// 使用示例
sendMessage("你好")
    .then(response => console.log("AI回复:", response))
    .catch(error => console.error("错误:", error));
```

## 更新日志

- v1.0.0: 初始版本，支持基本的聊天API
- 支持API密钥验证
- 支持CORS跨域请求
- 完善的错误处理和日志记录
