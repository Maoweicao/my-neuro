## 项目简介

本项目旨在几乎全方位复刻 Neuro-sama，同时向社区收集各种新奇有趣功能添加实现，由于其不错的训练代码。可以非常轻松的将少量数据集训练出非常好的效果。这一点是整个AI的核心。项目的目标是帮助用户打造专属的 AI 角色 - 通过您的数据印记,塑造出心目中理想的 AI 形象。

当前文档部署仅需6G显存不到，适配windows系统。同时需要有一个API-KEY 因为当前没有中转厂商来找我打广告，所以我不向各位推荐具体去哪里买API。但可以前往淘宝搜索“API”。里面有很多商家贩卖。

## 计划清单（打✔的是已经实现的功能）

### 双模型支持
- [x] 开源模型：基于开源模型微调，支持本地部署
- [x] 闭源模型：基于商业模型的 prompt 优化

### 核心功能
- [x] 超低延迟：模型回应仅需1秒左右
- [x] 字幕和语音同步输出
- [ ] 语音定制：支持男/女声切换，语速调节等
- [ ] 实时打断：支持随时打断模型对话
- [ ] 超吊的人机体验(类似真人交互设计，敬请期待)
- [ ] 丰富表情：根据对话内容展示不同的表情与动作
- [x] 集成视觉能力，支持图像识别，并通过语言意图判断何时启动视觉功能
- [ ] 声音模型（TTS）训练支持，默认使用gpt-sovits开源项目

### 扩展功能
- [ ] 桌面控制：支持语音控制打开软件等操作
- [ ] AI讲课：选择一个主题，让AI给你讲课。中途可提问。偏门课程可植入资料到数据库让AI理解
- [x] 替换各类live 2d模型
- [ ] web网页界面支持（已做好，近期会接入）
- [ ] 主动对话：根据上下文主动发起对话
- [ ] 联网接入，实时搜索最新信息
- [ ] 播放音效库中的音效，由模型自己决定播放何种音效
- [ ] 游戏陪玩，模型和用户共同游玩配合、双人、解密等游戏。目前实验游戏为：你画我猜、大富翁、galgame等小游戏
- [ ] 长期记忆，让模型记住你的关键信息，你的个性，脾气

### 模型自己想要的功能（待定考虑）
- [ ] 变色功能：按照模型心情让屏幕变色妨碍用户
- [ ] 自由走动：模型自由在屏幕中移动

## 🚀 快速开始

### 启动步骤

1. 创建并激活虚拟环境
```bash
conda create -n my-neuro python=3.11 -y

##启动虚拟环境
conda activate my-neuro
```

2. 安装依赖
```bash
pip install -r requirements.txt

#安装ffmpedg
conda install ffmpeg

#安装cuda 默认是11.8 可以自行修改
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

windows系统在执行pip install -r requirements.txt的时候，你可能会遇到一个报错：尝试安装 jieba_fast 包时缺少必要的 Microsoft Visual C++ 编译工具。

这个是因为gpt-sovits所需要的环境库必须要有jieba_fast这个包。而jieba_fast 是一个 C++ 加速版的 jieba 分词库，它需要通过编译 C++ 代码才能安装。

解决方法有些麻烦，不过测试下来是可以正常解决这个报错的。首先前往 https://visualstudio.microsoft.com/visual-cpp-build-tools/

打开后点击下载生成工具
![image](https://github.com/user-attachments/assets/232fe288-b013-48ea-afc4-e5a4f07db43a)

然后运行这个下载包
![image](https://github.com/user-attachments/assets/77f8683b-53ac-4d86-bc3c-a6c4bc09cdfd)

等待这个下载好
![image](https://github.com/user-attachments/assets/00bd1f69-02c0-4e3d-89b1-401d41698f08)

接着再按照顺序点击使用c++的桌面开发、然后安装
![image](https://github.com/user-attachments/assets/a05b60e3-3c7b-4415-a8bb-072e3236e34b)

安装好了以后，再运行：pip install -r requirements.txt  就不会出现这个bug了



3.自动下载需要的各种模型

```bash
python Batch_Download.py
```

4.启动bert服务

```bash
python bert_api.py
```

5.启动ASR服务
```bash
##第一次运行，会自动下载需要的模型
python asr_api.py
```

6.启动TTS服务
```bash
#进入tts-studio文件夹
cd tts-studio

#启动TTS服务
python tts_api.py -p 5000 -d cuda -s tts-model/FKTTS/fake_neuro.pth -dr tts-model/FKTTS/sama.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "英文"
```


7.等待ASR和TTS都输出IP后，即可打开此链接下载红框内的zip文件：https://github.com/morettt/my-neuro/releases/tag/v2.5.0

![image](https://github.com/user-attachments/assets/c4503b40-034c-4a1e-a5c1-76a64e207ce5)


下载后解压是这样的，接着你需要修改这个index.html文件

![image](https://github.com/user-attachments/assets/e80808b1-0306-4558-bbf2-c29089684f3d)


打开后在537、538行那里,需要修改成你的API信息

![image](https://github.com/user-attachments/assets/20a24f5a-bacb-413b-91f0-2dee7df28cc2)


在989行，这里是模型的名字修改的地方。

![image](https://github.com/user-attachments/assets/a9fda498-d4b0-4a93-8719-494702a3d00b)


改好后保存，然后双击go.bat 就可以开始和模型聊天了

![image](https://github.com/user-attachments/assets/4afe85ed-ae01-4864-b35b-1e2cd58fe0fe)



### 本地模型微调

微调训练在文件夹finetune中，当前正在完善适配更好的代码。


