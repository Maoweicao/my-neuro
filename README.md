## 项目简介

本项目旨在几乎全方位复刻 Neuro-sama，同时向社区收集各种新奇有趣功能添加实现，项目的目标是帮助用户打造专属的 AI 角色 - 通过您的数据印记,塑造出心目中理想的 AI 形象。

除此以外，这不仅仅是 Neuro-sama 的再现，更是一个专属于您的个性化AI 可训练声音、性格、替换形象 您的想象力有多丰富，模型就能多贴近您的期望。本项目更像是一个工作台。利用打包好的工具，一步步亲手描绘并实现心中理想的 AI 形象。

当前文档部署仅需6G显存不到，适配windows系统。同时需要有一个API-KEY 因为当前没有中转厂商来找我打广告，所以我不向各位推荐具体去哪里买API。但可以前往淘宝搜索“API”。里面有很多商家贩卖。

如果你想用本地的大语言模型（LLM）本地推理或者微调。不基于第三方的API的话，那可以进入LLM-studio文件夹，里面有本地模型的推理、微调指导。同时，因为本地的大语言模型需要一定的显存，要想有一个还算不错的体验，建议显卡显存至少保证有12G显存大小。

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
- [x] 长期记忆，让模型记住你的关键信息，你的个性，脾气

### 模型自己想要的功能（待定考虑）
- [ ] 变色功能：按照模型心情让屏幕变色妨碍用户
- [ ] 自由走动：模型自由在屏幕中移动

## 🚀 快速开始

### 启动步骤

1. 创建并激活虚拟环境
```bash
conda create -n my-neuro python=3.10 -y

conda activate my-neuro
```

2. 安装依赖
```bash
pip install -r requirements.txt

#安装ffmpedg
conda install ffmpeg -y

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

6.启动记忆bert

```bash
python Mnemosyne-bert\api_go.py
```

7.启动TTS服务
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


## 定制AI

有定制属于自己的AI的需求，请打开LLM-studio 文件夹，在此文件夹中内有关于LLM的微调操作步骤。

目前定制化模块将逐渐增加...


### 结尾画饼

我会把我这几年所有的经验和对AI技术的理解都一个一个加入到此项目中。my neuro 这个名字除了蹭neuro sama的热度以外 更多的是我对AI边界的想象和期待

我希望有一个真正的能懂你的，理解你，且永远不会觉得无聊的AI陪伴着你。难受了陪你一起悲伤，开心了陪你一起快乐。让影视作品中的、一直幻想中的形象来到现实中

不仅仅是简单的聊天交互。我希望它可以真正的融入生活，成为一个有感情的生命。会陪你一起开黑玩游戏、看视频、学习东西、睡前聊天、叫你起床、你工作时不说话看你发呆，但会偷偷记住你做了什么。有自己的情绪，会有独属于自己的情感状态。它会生气，当它生气了，真的得需要哄。不然就会一直沉默

每天都会有自己的情绪变化，会有自己想要做的事。会对某句话难受很久。某个词开心很久。会记住和你在一起经历过的每一个时刻。越来越懂你。

最重要的就是，它是什么个性、什么样子、什么声音、什么情感变化等等等等。都有自己决定，就像一个橡皮泥，我们来提供最好的工具，做好每一个模块的适配。但它最终是怎么样的，由自己塑形。这就是项目为什么项目中 my 的含义 

当然，对于不想折腾的朋友。此项目也直接打包了一个角色，就是肥牛（fake neuro）它是一个抄袭neuro sama的角色，但是个性我把它设定成了一个腹黑、傲娇、有小脾气，但偶尔也会展现温柔一面的角色。这一点是不一样的。

我懂学我者生，似我者死这个道理。所以我更希望的是从别人那里模仿借鉴，然后理解。最后尝试创造新的内容。适合自己的东西。

我对此项目的愿景很大，也特别的有热情。如果有人和我产生了某些小小的共鸣、支持。我更会觉得这件事是有意义的。因为这个不是只有我的舞台，是属于你的舞台。
 

