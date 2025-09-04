# 唱歌接口多格式音频支持

## 概述

唱歌接口现在支持多种常见的音频文件格式，而不仅仅是WAV格式。接口会自动检测音频格式并转换为WAV格式进行播放。本次更新修复了音频播放完成后界面卡住的问题，并改进了错误处理机制。

## 最新改进

### v2.0 更新内容
- ✅ **自动格式检测**：无需手动指定格式，系统自动识别
- ✅ **界面卡住修复**：修复音频播放完成后界面卡住的问题
- ✅ **更好的错误处理**：改进超时机制和异常处理
- ✅ **循环播放优化**：循环播放不再阻塞界面
- ✅ **多格式支持**：支持MP3、FLAC、OGG、M4A、WMA等多种格式

## 支持的音频格式

- **WAV** (.wav) - 原始WAV格式，无需转换
- **MP3** (.mp3) - MPEG Audio Layer III
- **FLAC** (.flac) - Free Lossless Audio Codec
- **OGG** (.ogg) - Ogg Vorbis
- **AAC** (.aac) - Advanced Audio Coding
- **M4A** (.m4a) - MPEG-4 Audio
- **WMA** (.wma) - Windows Media Audio（需要ffmpeg）

## API使用方法

### 请求格式

```http
POST /api/sing
Content-Type: application/json

{
  "audio_base64": "base64编码的音频数据",
  "volume": 0.8,
  "loop": false,
  "singing_motion": "唱歌",
  "api_key": "可选的API密钥"
}
```

### 参数说明

- `audio_base64`: **必需**，base64编码的音频数据
- `volume`: 可选，音量倍数 (0.0-2.0)，默认为0.8
- `loop`: 可选，是否循环播放，默认为false
- `singing_motion`: 可选，唱歌时的Live2D动作，默认为"唱歌"
- `api_key`: 可选，如果配置了API密钥验证则需要提供

**注意**：不再需要手动指定`format`参数，系统会自动检测音频格式。

### 响应格式

```json
{
  "status": "success",
  "message": "唱歌请求已开始处理",
  "volume": 0.8,
  "loop": false,
  "singing_motion": "唱歌",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 依赖要求

### 必需依赖
```bash
pip install pydub>=0.25.1
```

### 可选依赖（用于WMA等格式）
- ffmpeg：从 https://ffmpeg.org/download.html 下载并添加到PATH

## 工作流程

1. **接收请求**：服务器接收base64音频数据
2. **自动检测**：检查文件头识别音频格式
3. **智能转换**：
   - WAV格式：直接使用
   - 其他格式：使用pydub转换为WAV
   - 转换失败：尝试ffmpeg
4. **安全播放**：
   - 后台线程播放，不阻塞界面
   - 自动触发Live2D动作
   - 播放完成自动停止动作
5. **循环控制**：循环播放可通过中断API停止

## 示例代码

### Python示例

```python
import requests
import base64

# 读取任意格式的音频文件
with open('song.mp3', 'rb') as f:  # 可以是mp3、flac、wav等任何支持格式
    audio_data = f.read()

# 转换为base64（系统会自动检测格式）
audio_base64 = base64.b64encode(audio_data).decode('utf-8')

# 发送请求（无需指定format参数）
response = requests.post('http://127.0.0.1:8888/api/sing', json={
    'audio_base64': audio_base64,
    'volume': 0.8,
    'loop': False,
    'singing_motion': '开心'
})

print(response.json())
```

### JavaScript示例

```javascript
const fs = require('fs');
const axios = require('axios');

// 读取音频文件（任意支持格式）
const audioData = fs.readFileSync('song.flac');
const audioBase64 = audioData.toString('base64');

// 发送请求（系统自动检测格式）
axios.post('http://127.0.0.1:8888/api/sing', {
    audio_base64: audioBase64,
    volume: 1.2,
    loop: true,
    singing_motion: '跳舞'
})
.then(response => {
    console.log(response.data);
})
.catch(error => {
    console.error(error.response.data);
});
```

## 注意事项

1. **文件大小限制**：最大支持50MB的音频文件
2. **自动检测**：系统通过文件头自动识别格式，无需手动指定
3. **转换性能**：大文件转换可能需要更多时间
4. **播放控制**：
   - 单次播放：自动停止
   - 循环播放：需通过中断API停止
5. **错误处理**：转换失败时会尝试直接播放或回退方案

## 测试工具

### WebAPI测试工具
```bash
python webapi_tester.py
```
在"唱歌测试"标签页中可以：
- 选择多种格式的音频文件
- 生成测试音频
- 实时查看转换和播放状态

### 格式转换测试
```bash
python test_audio_format_conversion.py
```

## 日志和监控

系统会记录详细的处理日志到 `logs/webapi_interactions.log`：
- 音频格式自动检测结果
- 转换过程和时间
- 播放状态变化
- 错误信息和处理方案

## 故障排除

### 常见问题

1. **"缺少音频处理库"**
   ```bash
   pip install pydub
   ```

2. **"ffmpeg转换失败"**
   - 下载ffmpeg并添加到PATH
   - 或使用其他支持的格式

3. **音频播放无声**
   - 检查系统音频设置
   - 确认音频文件完整性

4. **界面卡住**（已修复）
   - 如果仍有问题，重启应用程序
   - 检查后台线程状态

5. **格式检测失败**
   - 系统会假设为WAV格式继续处理
   - 检查文件是否损坏

### 性能优化建议

- 小文件（<10MB）转换最快
- WAV格式无需转换，播放最流畅
- 避免在循环播放时进行大量其他操作
- 及时使用中断API停止不需要的循环播放
