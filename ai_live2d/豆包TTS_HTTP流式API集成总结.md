# 豆包TTS HTTP流式API集成总结

## 🎯 集成状态

### ✅ 已完成的工作
1. **API迁移**: 成功将豆包TTS从旧的v1 WebSocket API迁移到新的v3 HTTP流式API
2. **代码更新**: 更新了以下文件以支持新的API：
   - `voice/tts_client.py`: 实现了HTTP流式请求处理
   - `UI.py`: 添加了Resource ID配置字段
   - `config.json`: 添加了`doubao_resource_id`参数
3. **测试脚本**: 创建了`test_doubao_http_stream.py`用于验证API功能
4. **请求结构**: 正确实现了新的请求头和请求体格式

### ❌ 当前问题
**API权限错误 (403 Forbidden)**
- 错误信息: `[resource_id=...] requested resource not granted`
- 原因: 当前的APP ID和Access Token没有权限访问豆包TTS HTTP流式API

## 🔧 解决方案

### 1. 验证API凭据
请在火山引擎控制台检查：
- APP ID: `9732033966`
- Access Token: `s0FmSeo36OWS3V2jeVRYGSvOJSxrJZyw`
- 确保这些凭据有效且未过期

### 2. 检查服务权限
确认在火山引擎控制台已：
- 购买豆包TTS服务
- 启用HTTP流式API权限
- 配置正确的Resource ID

### 3. 获取正确的Resource ID
可能的Resource ID值包括：
- `volc.btts.voice`
- `volc.btts.speech`
- `volc.btts.tts`
- 或其他在控制台显示的值

### 4. 测试步骤
1. 在火山引擎控制台确认API权限
2. 更新`config.json`中的`doubao_resource_id`为正确值
3. 运行测试脚本验证功能

## 📋 配置参数

```json
{
  "tts": {
    "doubao_app_id": "9732033966",
    "doubao_access_token": "s0FmSeo36OWS3V2jeVRYGSvOJSxrJZyw",
    "doubao_resource_id": "需要从控制台获取",
    "doubao_voice_type": "zh_female_yuanqishaonv_mars_bigtts",
    "doubao_encoding": "ogg"
  }
}
```

## 🚀 下一步行动
1. 登录火山引擎控制台
2. 检查豆包TTS服务状态和权限
3. 获取正确的Resource ID
4. 更新配置文件
5. 重新测试API功能

## 📝 技术实现细节

### API端点
- **新API**: `https://openspeech.bytedance.com/api/v3/tts/unidirectional`
- **旧API**: `wss://openspeech.bytedance.com/api/v1/tts/ws_binary`

### 请求头
```python
headers = {
    "X-Api-App-Id": app_id,
    "X-Api-Access-Key": access_token,
    "X-Api-Resource-Id": resource_id,
    "X-Api-App-Key": "aGjiRDfUWi",
    "Content-Type": "application/json"
}
```

### 请求体结构
```python
{
    "user": {
        "uid": "doubao_test_user"
    },
    "req_params": {
        "text": "测试文本",
        "speaker": "zh_female_yuanqishaonv_mars_bigtts",
        "audio_params": {
            "format": "ogg",
            "sample_rate": 24000,
            "enable_timestamp": True
        },
        "additions": "{\"explicit_language\":\"zh\",\"disable_markdown_filter\":true}"
    }
}
```

## 🎵 音频流处理
- 支持流式接收音频数据块
- 自动解码base64编码的音频数据
- 支持多种音频格式 (wav, ogg, mp3)
- 实时处理句子信息和时间戳

---

**状态**: ⚠️ 等待用户验证API权限和获取正确的Resource ID</content>
<parameter name="filePath">f:\my-neuro\ai_live2d\豆包TTS_HTTP流式API集成总结.md
