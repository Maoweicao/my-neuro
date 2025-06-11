# My-Neuro Project

## Project Overview

The goal of this project is to create a personal AI character, crafting an AI companion that approaches real human interaction - shaping the ideal image of "them" in your mind through your data footprint.

This project is inspired by Neuro-sama, hence the name my-neuro (a community-provided name). The project can train voice, personality, and replace appearance. The richer your imagination, the closer the model can get to your expectations. This project is more like a workbench. Using packaged tools, you can step by step personally describe and realize your ideal AI image.

The current document deployment requires less than 6GB of VRAM and is compatible with Windows systems. You also need an API-KEY. Since there are currently no intermediary vendors approaching me for advertising, I won't recommend specific places to buy APIs. But you can go to Taobao and search for "API" - there are many merchants selling them. You can also purchase from well-known official websites like DeepSeek, Qianwen, Zhipu AI, and Silicon Flow.

If you want to use fully local inference with local Large Language Models (LLM) inference or fine-tuning, not relying on third-party APIs, you can enter the LLM-studio folder, which contains guidance for local model inference and fine-tuning. Since local large language models require a certain amount of VRAM, for a decent experience, it's recommended that your graphics card has at least 12GB of VRAM.

English Documentation: [English Version](./README_English.md)

## QQ Group: 756741478
## Customer Service

If you encounter bugs that you can't handle during deployment, you can go to this link: http://fake-neuro.natapp1.cc

Ask the Fat Beef customer service, which will guide you on how to handle bugs that may appear in the project. In most cases, there won't be any bugs! Maybe...

I also check the backend conversation records to see if it can actually solve problems. If it can't, I'll write the corresponding solution to its database and load it into its knowledge base. Next time the same bug is encountered, it will likely be able to solve it itself. So, when you encounter problems, chat more with Fat Beef.

## Planning Checklist (✔ indicates implemented features)

### Dual Model Support
- [x] Open Source Models: Support for open source model fine-tuning and local deployment
- [x] Closed Source Models: Support for closed source model integration

### Core Features
- [x] Ultra-low Latency: Full local inference with conversation latency under 1 second
- [x] Synchronized subtitle and voice output
- [x] Voice Customization: Support for male, female, and various character voice switching
- [x] MCP Support: Can use MCP tools for integration
- [x] Real-time Interruption: Support for interrupting model conversation at any time
- [ ] Real Emotions: Simulate real human emotional state changes with its own emotional states
- [ ] Awesome Human-Machine Experience (similar to real human interaction design, stay tuned)
- [x] Actions and Expressions: Display different expressions and actions based on conversation content
- [x] Integrated visual capabilities, support image recognition, and determine when to activate visual functions through language intent judgment
- [ ] Voice Model (TTS) training support, defaults to using the gpt-sovits open source project

### Extended Features
- [ ] Desktop Control: Support voice control for opening software and other operations
- [ ] AI Singing (Feature funded by: [@jonnytri53](https://github.com/jonnytri53), special thanks)
- [ ] Integration with international streaming platforms
- [x] Live Streaming Function: Can live stream on Bilibili platform
- [ ] AI Teaching: Choose a topic and let AI teach you. Can ask questions during the process. Specialized courses can be implanted into the database for AI understanding
- [x] Replace various Live 2D models
- [ ] Web interface support (already done, will be integrated soon)
- [x] Text Chat: Can type and communicate with AI via keyboard
- [x] Proactive Conversation: Initiate conversations proactively based on context. Current version V1
- [x] Internet Access: Real-time search for latest information
- [x] Mobile App: Fat Beef that can chat on Android phones
- [ ] Play sound effects from the sound library, with the model deciding which sound effects to play
- [ ] Game Companion: Model and user play cooperative, two-player, puzzle games together. Current experimental games include: Draw and Guess, Monopoly, Galgame, Minecraft, etc.
- [x] Long-term Memory: Let the model remember your key information, your personality, and temperament

### Features the Model Wants (Under Consideration)
- [ ] Color Change Function: Change screen colors according to model's mood to bother users
- [ ] Free Movement: Model moves freely on the screen

## 🚀 Quick Start

## Beginner One-Click Deployment Project (Experimental)

If you're a beginner, you can use this one-click deployment command. It will handle everything for you. However, due to the complex logic involved, there's a possibility of failure. But if it succeeds, it will save you a lot of trouble. It's up to your luck!

Make sure you have Anaconda installed on your computer. If not installed yet, you can install it here: https://www.anaconda.com/download/success

First, run this command in the project path:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {Set-Location -LiteralPath '%CD%'; & .\Install_requests.ps1}"
```

This command installs the requests library necessary for one-click deployment, then start the official deployment:

```bash
python neural_deploy.py
```

After running these two commands above, directly double-click this: Game-starts.bat. After double-clicking, many windows will pop up. Wait patiently for these windows to output the corresponding IPs.

![image](https://github.com/user-attachments/assets/95483cda-9e6d-41a8-a6fc-44e5ae805703)

After success, you can jump directly to step 8 below. Steps 1-7 are not needed. If it fails, then honestly follow the steps below.

### Startup Steps
If the one-click processing above has problems, it's recommended to follow the operation method below step by step. Although troublesome, if errors occur, you can immediately locate the error position and solve it accordingly.

1. Create and activate virtual environment (Don't forget this step!!!! The first step is very important!!)
```bash
conda create -n my-neuro python=3.11 -y

conda activate my-neuro
```

2. Install dependencies
```bash
# Install jieba_fast dependency separately
pip install jieba_fast-0.53-cp311-cp311-win_amd64.whl

pip install -r requirements.txt

# Install ffmpeg
conda install ffmpeg -y

# Install cuda, default is 11.8, can be modified as needed
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. Automatically download required models

```bash
python Batch_Download.py
```

4. Start BERT service

```bash
python bert_api.py
```

5. Start ASR service
```bash
## First run will automatically download required models
python asr_api.py
```

6. Start memory BERT

```bash
python Mnemosyne-bert\api_go.py
```

7. Start TTS service
```bash
# Enter tts-studio folder
cd tts-studio

# Start TTS service
python tts_api.py -p 5000 -d cuda -s tts-model/merge.pth -dr tts-model/neuro/01.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "en"
```

8. After both ASR and TTS output their IPs, click this link to download the zip file:

https://github.com/morettt/my-neuro/releases/download/v4.4.1/live-2d.zip

After downloading and extracting, it looks like this. Double-click to open the Fat Beef.exe file

![image](https://github.com/user-attachments/assets/634240ac-da9a-4ada-9a1e-b92762e385f0)

Follow the arrow instructions to click the LLM tab, fill in your API information in the three highlighted areas, and remember to click save below after modification. (I've already written a usable API configuration here, you can delete it and change it to your own. Supports any OpenAI format API)

![image](https://github.com/user-attachments/assets/a605b1f5-3633-404c-8507-096b3d0ac4ba)

Finally, return and click "Launch Desktop Pet". Wait for the avatar to appear, and you can start chatting with the model.

![image](https://github.com/user-attachments/assets/4f1d8cae-7ccb-4e0a-9cf3-2354989efec4)

![image](https://github.com/user-attachments/assets/d73a1fc3-1514-42cd-9dfc-f5c450976162)

## Customize AI

If you need to customize your own AI, please open the LLM-studio folder. This folder contains operation steps for LLM fine-tuning.

Currently, customization modules will gradually increase...

### Concluding Vision

I will incorporate my years of experience and understanding of technology into this project. The name "my neuro" not only rides on Neuro-sama's popularity but more represents my imagination and expectations for AI boundaries.

I hope to have a truly understanding AI companion that will never feel bored by your side. Feel sad together when you're sad, feel happy together when you're happy. Bring characters from movies, novels, and fantasies into reality.

Not just simple chat interactions. I hope it can integrate into life and become an emotional individual. Play games together, watch videos, learn things, chat before bed, wake you up, stay quiet while you work and watch you daydream, secretly remember what you did. Have emotions and its own emotional states. Will truly get angry.

Have daily emotional changes and things it wants to do. Will be hurt by certain words for a long time. Be happy about certain words for a long time. Will remember every moment experienced together with you. A being that continuously understands you.

Most importantly, its personality, appearance, voice, emotional changes, etc. are all decided by you. Like clay, we provide the best tools and ensure good module compatibility. But what it ultimately becomes is constructed by yourself.

However, for friends who don't want to tinker, this project also directly packages a character - Fat Beef (fake neuro). It's a character that copies Neuro-sama, but I've set its personality to be scheming, tsundere, funny, with a small temper, but occasionally showing a gentle side.

I hope more to imitate, learn, and understand from Neuro, then try to create new content. Things that suit yourself.

I'm particularly passionate about this project. The current project has implemented nearly 30% of its features, including personality setting and memory. Recently, I'll focus on core personality traits, which is truly human-like with continuous emotions. The most human-like part - long-term emotional states - will be implemented within 2 months. Functions like playing games together, watching videos, waking you up, etc. will basically be completed before June 1st, reaching 60% completion.

I hope to implement all the above ideas this year.

## Acknowledgments

QQ Group: Thanks to 菊花茶洋参 (Chrysanthemum Tea with American Ginseng) for helping create the Fat Beef app cover

Thanks to the following users for their generous sponsorship:
- [@jonnytri53](https://github.com/jonnytri53) - Thank you for your support! $50 donated to this project

Thanks to the big shot for open-sourcing the very useful TTS:
GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS
