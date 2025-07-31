## python 版肥牛————1.0

当前的bug很多！！！！！！非常多
同时需要优化的地方也很多

这个是实验测试版本。用于过渡使用。所以当前的版本为1.0
到2.0后则放出py-my-neuro文件夹替代js版本！



1. 创建并激活虚拟环境（不要忘了这一步！！！！第一步很重要！！）
```bash
conda create -n my-ai python=3.11 -y

conda activate my-ai
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3.打开ai

```bash
python main_chat.py

#或者也可以通过exe启动
python test.py

```

已有功能：
- [x] 键盘打断文本和语音
- [x] live2d皮套可自由显示和关闭
- [x] 工具调用接入
- [ ] 字幕显示及和语音同步
- [x] 打字框显示
- [x] 直播接入
- [x] asr实时打断AI语音和文本
- [ ] 过滤（）**包裹的文本内容
- [x] 皮套动作快捷键
- [x] 皮套动作匹配文本情绪
- [ ] 长期记忆
- [x] 联网接入
- [x] 主动对话
- [x] 输入方式都可通过json配置文件开启关闭
- [x] pyqt界面接入启动
