# Live2D模型参数控制功能说明

## 功能概述

Live2D模型参数控制功能允许用户在UI界面中实时调整Live2D模型的各种参数，如面部表情、眼部动作、身体姿态等。该功能支持参数检测、实时调整和配置保存。

## 使用方法

### 1. 参数检测

1. 在UI中打开"动画"标签页
2. 在左侧控制面板中找到"模型参数控制"组
3. 点击"检测参数"按钮自动检测当前Live2D模型的所有可用参数
4. 系统会显示检测到的参数数量和状态

### 2. 参数调整

- 使用滑块调整各个参数的数值
- 参数值会实时显示在滑块右侧
- 每个参数都有对应的重置按钮，可以快速重置为默认值
- 所有参数的取值范围和默认值会在参数名称的工具提示中显示

### 3. 参数应用

1. 调整参数后，点击"应用参数"按钮将设置发送到Live2D模型
2. 参数设置会自动保存到配置文件中
3. 系统会显示应用成功的参数数量

### 4. 参数重置

- 点击"重置参数"按钮可以将所有参数重置为默认值
- 或者点击单个参数旁边的重置按钮重置该参数

## 配置文件结构

参数设置保存在 `config.json` 文件的 `live2d` 节点下，按模型名称分组：

```json
{
    "live2d": {
        "模型名称": {
            "parameters": {
                "ParamEyeLOpen": 0.8,
                "ParamEyeROpen": 0.8,
                "ParamMouthOpenY": 0.3,
                "ParamAngleX": 5.0,
                "ParamAngleY": -2.0,
                "ParamBreath": 0.5
            }
        }
    }
}
```

## 支持的参数类型

### 标准参数（基于Live2D官方规范）

#### 眼部参数
- `ParamEyeLOpen` - 左眼开合 (0.0-1.0)
- `ParamEyeROpen` - 右眼开合 (0.0-1.0)
- `ParamEyeLSmile` - 左眼微笑 (0.0-1.0)
- `ParamEyeRSmile` - 右眼微笑 (0.0-1.0)
- `ParamEyeBallX` - 眼球X轴 (-1.0-1.0)
- `ParamEyeBallY` - 眼球Y轴 (-1.0-1.0)

#### 眉毛参数
- `ParamBrowLY` - 左眉Y轴 (-1.0-1.0)
- `ParamBrowRY` - 右眉Y轴 (-1.0-1.0)
- `ParamBrowLX` - 左眉X轴 (-1.0-1.0)
- `ParamBrowRX` - 右眉X轴 (-1.0-1.0)

#### 嘴部参数
- `ParamMouthOpenY` - 嘴巴开合 (0.0-1.0)
- `ParamMouthForm` - 嘴型 (-1.0-1.0)

#### 面部参数
- `ParamAngleX` - 面部X轴旋转 (-30.0-30.0)
- `ParamAngleY` - 面部Y轴旋转 (-30.0-30.0)
- `ParamAngleZ` - 面部Z轴旋转 (-30.0-30.0)

#### 身体参数
- `ParamBodyAngleX` - 身体X轴旋转 (-10.0-10.0)
- `ParamBodyAngleY` - 身体Y轴旋转 (-10.0-10.0)
- `ParamBodyAngleZ` - 身体Z轴旋转 (-10.0-10.0)

#### 其他参数
- `ParamBreath` - 呼吸 (0.0-1.0)

### 自定义参数

系统还支持模型特有的自定义参数，如水印控制等。这些参数会在检测时自动识别。

## 技术实现

### UI部分 (UI.py)
- `detect_live2d_parameters()` - 检测Live2D模型参数
- `_get_live2d_params_from_model()` - 从模型实例获取参数
- `_get_default_live2d_params()` - 获取默认参数列表
- `_create_params_controls()` - 创建参数控制UI
- `apply_live2d_parameters()` - 应用参数设置
- `reset_live2d_parameters()` - 重置参数
- `_update_live2d_params_widgets()` - 更新控件显示值

### 后端部分 (main.py)
- `_handle_set_live2d_parameters_message()` - 处理UI发送的参数消息
- `_apply_live2d_parameters()` - 应用参数到Live2D模型
- `_find_live2d_param_index()` - 查找参数索引

### 消息通信

UI和后端通过消息队列通信：
- 消息类型：`set_live2d_parameters`
- 数据格式：`{"parameters": {"param_id": value, ...}}`

## 参数应用方式

支持多种参数设置方式：

1. **SetParameterValue方法**（推荐）
   ```python
   model.SetParameterValue("ParamMouthOpenY", 1.0, 1.0)
   ```

2. **AddParameterValue方法**
   ```python
   model.AddParameterValue("ParamMouthOpenY", 1.0)
   ```

3. **标准参数常量**
   ```python
   from live2d.v3.params import StandardParams
   model.SetParameterValue(StandardParams.ParamMouthOpenY, 1.0, 1.0)
   ```

## 注意事项

1. 参数检测依赖于Live2D模型实例，确保模型已正确加载
2. 不同模型支持的参数可能不同，建议先进行参数检测
3. 参数值会实时保存到配置文件，重启应用后会自动恢复
4. 某些参数可能需要模型特定支持，不支持的参数会在日志中显示警告

## 故障排除

1. **参数检测失败**
   - 检查Live2D模型是否正确加载
   - 查看控制台日志获取详细错误信息

2. **参数应用无效果**
   - 确认模型支持该参数
   - 检查main.py中的日志输出
   - 验证消息队列连接是否正常

3. **UI界面无响应**
   - 重新点击"检测参数"按钮
   - 重启应用程序

## 扩展功能

该功能可以进一步扩展：
- 参数预设方案保存和加载
- 参数动画序列制作
- 批量参数导入导出
- 参数变化的实时预览