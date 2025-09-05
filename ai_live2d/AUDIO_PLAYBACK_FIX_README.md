# main.py 音频播放修复总结

## 🔧 修复的问题

### 1. 原始问题
- main.py播放音频时无声音输出
- sounddevice播放流管理不当
- 错误处理不够完善

### 2. 主要修复内容

#### A. 音频数据处理优化
```python
# 修复前：简单的类型转换
audio_float = audio_array.astype(np.float32) / 32767.0

# 修复后：根据采样位数进行正确转换
if sample_width == 2:
    audio_float = audio_array.astype(np.float32) / 32767.0
else:
    audio_float = audio_array.astype(np.float32) / 127.0

# 添加音量限制
audio_float = np.clip(audio_float, -1.0, 1.0)
```

#### B. 音频设备检查
```python
# 检查音频设备可用性
try:
    devices = sd.query_devices()
    output_devices = [d for d in devices if d['max_output_channels'] > 0]
    if not output_devices:
        raise Exception("没有可用的音频输出设备")
except Exception as e:
    # 回退到系统播放器
    self._play_audio_fallback(audio_data, volume, loop, singing_motion)
    return
```

#### C. 音频流管理改进
```python
# 修复前：直接使用sd.get_stream()可能返回None
while sd.get_stream().active and not self._stop_singing:
    time.sleep(0.01)

# 修复后：安全的流状态检查
if current_stream and hasattr(current_stream, 'active'):
    if not current_stream.active:
        break
else:
    try:
        sd.wait(timeout=0.1)
        if not sd.get_stream() or not sd.get_stream().active:
            break
    except:
        break
```

#### D. 错误处理和回退机制
```python
# 添加超时机制
start_time = time.time()
timeout = 30.0  # 30秒超时

# 增强的异常处理
try:
    current_stream = sd.play(audio_float, samplerate=framerate, blocking=False)
    self.current_audio_stream = current_stream
except Exception as play_error:
    if self.logger:
        self.logger.error(f">>> sounddevice播放失败: {play_error}")
    # 回退到系统播放器
    self._play_audio_fallback(audio_data, volume, loop, singing_motion)
```

## 🎯 测试结果

### 测试环境
- Windows 系统
- Python 3.11
- sounddevice 可用
- 18个音频输出设备

### 测试通过项目
- ✅ 音频格式转换：WAV格式检测和处理正常
- ✅ 直接音频播放：sounddevice播放功能正常
- ✅ 音频流管理：流启动和停止正常
- ✅ 音量控制：音量应用正确
- ✅ 错误处理：异常情况处理完善

## 🚀 使用方法

### 1. 通过代码直接调用
```python
from main import PetService

service = PetService()
# 设置必要属性...
service.play_singing_audio(audio_data, volume=0.7, loop=False, singing_motion="唱歌")
```

### 2. 通过消息队列（推荐）
```python
from utils.message_queue import get_message_queue
import base64

# 编码音频数据
audio_data_b64 = base64.b64encode(audio_data).decode('utf-8')

# 发送播放消息
message_queue = get_message_queue()
message_queue.send_message('play_audio', {
    'audio_data': audio_data_b64,
    'volume': 0.7,
    'loop': False,
    'singing_motion': '唱歌',
    'lrc_content': ''  # 可选的LRC歌词
})
```

### 3. 支持的音频格式
- WAV（推荐，直接播放）
- MP3（自动转换为WAV）
- FLAC（自动转换为WAV）
- OGG（自动转换为WAV）
- M4A/AAC（自动转换为WAV）

### 4. 播放参数
- `volume`: 音量 (0.0 - 1.0)
- `loop`: 是否循环播放
- `singing_motion`: Live2D动作名称
- `lrc_content`: LRC歌词内容（可选）

## 🛠️ 故障排查

### 如果仍然无声音
1. 检查系统音量设置
2. 确认音频设备正常工作
3. 运行 `python debug_audio_playback.py` 进行诊断
4. 查看日志输出了解详细信息

### 常见问题
- **ImportError**: 确保安装了 `sounddevice` 和 `numpy`
- **设备不可用**: 检查音频驱动和设备连接
- **播放中断**: 检查 `_stop_singing` 标志状态

## 📝 日志信息

修复后的版本提供详细的日志信息：
```
>>> 开始播放唱歌音频
>>> WAV解析完成: 1声道, 44100Hz, 88200帧
>>> 音频数据处理完成，应用音量: 0.7, 数据范围: [-0.700, 0.700]
>>> 找到 18 个音频输出设备
>>> 开始单次播放音频
>>> 音频流已启动
>>> 单次播放完成
```

这些日志可以帮助您诊断任何播放问题。
