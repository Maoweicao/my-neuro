# 字幕显示功能说明

## 功能概述

新增了台词和唱歌时的字幕显示功能，当启用字幕时：
- **台词模式**：AI念出来的台词会显示在字幕上
- **唱歌模式**：如果有对应的LRC歌词文件，会显示歌词；否则显示"♪ 唱歌中 ♫"

## 配置要求

### 1. 启用字幕
在 `config.json` 中设置：
```json
{
  "setting": {
    "subtitle_enabled": true
  }
}
```

### 2. 字幕样式配置
在 `config.json` 中可以配置字幕样式：
```json
{
  "subtitle": {
    "font_family": "Microsoft YaHei",
    "font_size": 24,
    "font_bold": false,
    "box_width": 1800,
    "box_height": 800,
    "padding": 20,
    "border_radius": 15,
    "fade_duration": 300
  }
}
```

## LRC歌词文件

### 文件命名规则
LRC歌词文件应放在以下位置之一：
- `lyrics/{audio_hash}.lrc`
- `lyrics/audio_{audio_hash}.lrc`
- `lrc/{audio_hash}.lrc`
- `lrc/audio_{audio_hash}.lrc`
- `{audio_hash}.lrc`
- `audio_{audio_hash}.lrc`

### 哈希值计算
`audio_hash` 是通过对音频base64数据进行MD5哈希后取前8位字符生成的。

### LRC文件格式示例
```
[00:12.00]歌词第一行
[00:15.50]歌词第二行
[00:18.20]歌词第三行
```

## 使用方法

### 1. WebAPI调用

#### 台词模式
```bash
curl -X POST http://127.0.0.1:8888/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"dialogue": "你好，我是AI助手"}'
```

#### 唱歌模式
```bash
curl -X POST http://127.0.0.1:8888/api/sing \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "base64_encoded_audio_data",
    "volume": 1.0,
    "loop": false,
    "singing_motion": "唱歌"
  }'
```

### 2. 自动显示逻辑

- **台词**：当字幕启用时，转换后的台词会自动显示在字幕上
- **唱歌**：开始播放音频时会检查对应的LRC文件，如果找到则显示歌词，否则显示"♪ 唱歌中 ♫"

## 技术实现

### 通信机制
- UI.py 通过socket (端口8889) 向 main.py 发送字幕显示请求
- main.py 接收请求后调用字幕管理器的 `add_text` 方法

### 信号类型
- `show_subtitle`：显示字幕信号
  - `text`：字幕文本内容
  - `source`：来源 ("dialogue" 或 "singing")
  - `timestamp`：时间戳

### 显示模式
- **台词**：使用流式显示（逐字显示效果）
- **唱歌**：使用完整显示（直接显示全部歌词或 ♪♫）

## 测试

运行测试脚本验证功能：
```bash
python test_subtitle_display.py
```

## 注意事项

1. 确保 main.py 正在运行并监听端口8889
2. 字幕管理器需要在 AppManager 中正确初始化
3. LRC文件需要使用UTF-8编码
4. 如果没有找到LRC文件，唱歌时会显示默认的"♪ 唱歌中 ♫"
