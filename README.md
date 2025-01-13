# Fake-Neuro

这是一个用于复刻neuro-same 的开源项目。目的是打造属于自己的neuro。
不过

## ✨ 功能特性

### 🤖 双模型支持
- 开源模型：基于开源模型微调，支持本地部署
- 闭源模型：基于商业模型的 prompt 优化

### 🎯 核心功能
- 超低延迟：优化后的推理速度仅需2秒左右
- 语音定制：支持男/女声切换，语速调节等
- 实时打断：支持随时打断模型对话
- 自然交互：类真人的交互体验
- 丰富表情：根据对话内容展示不同的表情与动作

### 🎮 扩展功能
- 桌面控制：支持语音控制打开软件等操作
- 多模态支持：集成视觉能力，支持图像识别
- 主动对话：根据上下文主动发起对话

## 🚀 快速开始

### 环境要求
- Linux 操作系统
- Python 3.10+
- CUDA 支持（推荐）

### 安装步骤

1. 创建并激活虚拟环境
```bash
conda create -n my-neuro python=3.10 -y
source activate my-neuro
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 下载模型
```bash
export MODELSCOPE_CACHE="./model"
modelscope download --model Qwen/Qwen2.5-7B-Instruct
```

## 🔧 模型训练

完成基础配置后，可以进入 finetune 文件夹进行模型微调。详细的训练流程和参数设置请参考训练文档。


