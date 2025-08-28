# Live2D WebAPI 控制说明

## 使用步骤

### 1. 启动UI控制面板
```bash
cd ai_live2d
python UI.py
```

### 2. 启动WebAPI服务器
- 在UI界面中，切换到"其他设置"标签页
- 找到"WebAPI设置"部分
- 点击"启动服务"按钮
- 确认状态显示为"服务状态: 已启动"

### 3. 启动Live2D桌宠
- 在UI界面主页面，点击绿色播放按钮启动Live2D桌宠
- 等待桌宠程序完全启动

### 4. 测试WebAPI控制
```bash
python simple_webapi_test.py
```

## API接口说明

### 动作控制
```
POST http://127.0.0.1:8888/api/live2d/motion
Content-Type: application/json

{
  "motion": 0  // 动作索引，0-7
}
```

### 表情控制
```
POST http://127.0.0.1:8888/api/live2d/expression
Content-Type: application/json

{
  "expression": "happy"  // 表情名称
}
```

### 服务状态查询
```
GET http://127.0.0.1:8888/api/status
```

## 工作原理

1. UI通过WebAPI接收控制请求
2. 将请求写入临时文件：
   - `motion_trigger.tmp` - 动作触发文件
   - `expression_trigger.tmp` - 表情触发文件
3. Live2D桌宠程序通过文件监听器检测文件变化
4. 执行相应的动作或表情变化

## 故障排除

### WebAPI连接失败
- 确保UI.py已启动
- 确保在UI中点击了"启动服务"按钮
- 检查端口8888是否被占用

### Live2D没有响应
- 确保Live2D桌宠程序已启动
- 检查文件监听器是否正常工作
- 查看桌宠程序的日志输出

### 400错误
- 检查请求格式是否正确
- 确保JSON格式有效
- 检查必需字段是否存在

## 示例代码

```python
import requests

# 触发动作
response = requests.post('http://127.0.0.1:8888/api/live2d/motion', 
                        json={'motion': 0})
print(response.json())

# 触发表情
response = requests.post('http://127.0.0.1:8888/api/live2d/expression', 
                        json={'expression': 'happy'})
print(response.json())
```
