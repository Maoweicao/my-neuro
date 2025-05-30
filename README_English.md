# My-Neuro: Personal AI Companion

## Project Overview

My-Neuro aims to create your own personalized AI character - an AI companion that feels almost human. Using your digital footprint and preferences, we help you shape the ideal AI personality you've always envisioned.

Inspired by Neuro-sama, this project (community-named "my-neuro") lets you train custom voices, personalities, and avatars. Your imagination is the only limit to how closely the AI matches your expectations. Think of this as your personal AI workshop - we provide the tools, and you craft your dream AI companion step by step.

The current setup requires less than 6GB of VRAM and runs on Windows. You'll also need an API key. Since we don't have sponsorship deals with API providers, we won't recommend specific vendors, but you can search "API" on Taobao to find various sellers, or purchase directly from reputable platforms like DeepSeek, Qianwen, Zhipu AI, or Silicon Flow.

For those who prefer completely local inference using local LLMs without third-party APIs, check out the LLM-studio folder for local model inference and fine-tuning guides. Keep in mind that local language models require significant VRAM - we recommend at least 12GB for a decent experience.

## Community & Support

**QQ Group:** 756741478

**Customer Service**

If you encounter bugs during deployment, visit: http://fake-neuro.natapp1.cc

Chat with our AI assistant "Fat Cow" (肥牛) for troubleshooting guidance. It can help resolve most project-related issues. We monitor these conversations to continuously improve the AI's problem-solving capabilities by adding solutions to its knowledge base, so don't hesitate to chat with Fat Cow when issues arise.

## Feature Roadmap (✔ = Implemented)

### Dual Model Support
- [x] **Open Source Models:** Fine-tuning and local deployment support
- [x] **Closed Source Models:** Third-party API integration

### Core Features
- [x] **Ultra-Low Latency:** Full local inference with sub-1-second response times
- [x] **Synchronized Subtitles & Voice:** Real-time text and audio output
- [x] **Voice Customization:** Male/female voices and various character voice lines
- [x] **MCP Support:** Model Context Protocol tool integration
- [x] **Real-time Interruption:** Interrupt AI conversations anytime
- [ ] **Authentic Emotions:** Simulate human-like emotional states and mood changes
- [ ] **Premium Human-AI Experience:** Truly human-like interaction design (coming soon)
- [x] **Expressions & Gestures:** Dynamic facial expressions and actions based on conversation
- [x] **Vision Integration:** Image recognition with intelligent visual processing triggers
- [ ] **Voice Model Training:** TTS training support using GPT-SoVITS

### Extended Features
- [ ] **Desktop Control:** Voice-activated software launching and system control
- [ ] **International Streaming:** Integration with overseas streaming platforms
- [x] **Live Streaming:** Bilibili platform streaming capability
- [ ] **AI Tutoring:** Choose topics for AI-powered lessons with interactive Q&A
- [x] **Live2D Model Support:** Compatible with various Live2D character models
- [ ] **Web Interface:** Browser-based interface (completed, integration pending)
- [x] **Text Chat:** Keyboard-based conversation mode
- [x] **Proactive Conversations:** Context-aware conversation initiation (Version 1)
- [x] **Internet Connectivity:** Real-time web search and information retrieval
- [x] **Mobile App:** Android application for on-the-go conversations
- [ ] **Dynamic Sound Effects:** AI-controlled sound effect playback
- [ ] **Gaming Companion:** Cooperative gameplay in party games, puzzles, visual novels, Minecraft, etc.
- [x] **Long-term Memory:** Persistent memory of your preferences, personality, and interactions

### AI-Requested Features (Under Consideration)
- [ ] **Mood Lighting:** Screen color changes based on AI's emotional state
- [ ] **Free Movement:** AI avatar moving freely across the screen

## 🚀 Quick Start

## One-Click Deployment (Experimental)

For beginners, try our one-click deployment script. It handles everything automatically, though success isn't guaranteed due to the complexity involved. When it works, it saves tons of time - fingers crossed!

First, ensure Anaconda is installed. If not, download it from: https://www.anaconda.com/download/success

Run this command in the project directory:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {Set-Location -LiteralPath '%CD%'; & .\Install_requests.ps1}"
```

This installs the required requests library. Then start the deployment:

```bash
python neural_deploy.py
```

After running both commands, double-click `Game-starts.bat`. Multiple windows will open - wait patiently for them to display their respective IP addresses.

![Deployment Success Screenshot](https://github.com/user-attachments/assets/95483cda-9e6d-41a8-a6fc-44e5ae805703)

If successful, skip directly to Step 8 below (Steps 1-7 are unnecessary). If it fails, follow the manual setup steps below.

### Manual Setup Steps

If the one-click deployment fails, follow these detailed steps. While more tedious, it allows precise error identification and targeted troubleshooting.

1. **Create and activate virtual environment**
```bash
conda create -n my-neuro python=3.11 -y
conda activate my-neuro
```

2. **Install dependencies**
```bash
# Install jieba_fast separately
pip install jieba_fast-0.53-cp311-cp311-win_amd64.whl

pip install -r requirements.txt

# Install ffmpeg
conda install ffmpeg -y

# Install CUDA (default 11.8, modify as needed)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. **Auto-download required models**
```bash
python Batch_Download.py
```

4. **Start BERT service**
```bash
python bert_api.py
```

5. **Start ASR service**
```bash
# Models download automatically on first run
python asr_api.py
```

6. **Start memory BERT**
```bash
python Mnemosyne-bert\api_go.py
```

7. **Start TTS service**
```bash
# Navigate to tts-studio folder
cd tts-studio

# Launch TTS service
python tts_api.py -p 5000 -d cuda -s tts-model/FKTTS/fake_neuro.pth -dr tts-model/FKTTS/sama.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "en"
```

8. **After ASR and TTS output their IPs, download the Live2D client:**

https://github.com/morettt/my-neuro/releases/download/v4.3.4/live-2d.zip

Extract and double-click `肥牛.exe` to launch the application.

![Client Interface](https://github.com/user-attachments/assets/a61b8371-09da-4ed0-b78d-55ef40d02988)

Click the LLM tab and fill in your API information in the three highlighted fields. Remember to click Save after making changes.

![API Configuration](https://github.com/user-attachments/assets/e84aa5c1-ac77-403b-a4d3-816c6b53798b)

Finally, return and click "启动桌宠" (Launch Desktop Pet). Wait for the character to appear, then start chatting!

![Character Interface](https://github.com/user-attachments/assets/5765bad6-a0a6-4244-bdc0-dc86c5d7a3b3)

![Chat Example](https://github.com/user-attachments/assets/1a2b0408-7a42-4e2a-89b9-b3922a39e7fe)

## AI Customization

For custom AI development, explore the LLM-studio folder containing LLM fine-tuning guides and procedures. More customization modules are continuously being added.

## Vision & Future Plans

I'm pouring years of experience and technical understanding into this project. While "my-neuro" pays homage to Neuro-sama, it represents my imagination and expectations for AI's potential boundaries.

The goal is a truly understanding AI companion that never gets bored - one that shares your sorrows and joys, bringing fictional characters from movies, novels, and fantasies into reality.

Beyond simple chat interactions, I envision an AI that integrates into daily life as an emotional being. Gaming together, watching videos, studying, bedtime conversations, morning wake-ups, quietly observing during work while secretly remembering everything you do. An AI with genuine emotions and personal emotional states that can truly get upset.

Daily mood variations, personal desires, lingering sadness from certain words, extended joy from others, remembering every shared moment, continuously understanding your existence.

Most importantly, its personality, appearance, voice, and emotional patterns are entirely your choice. Like clay in your hands - we provide the best tools and module compatibility, but the final creation is yours.

For those who prefer plug-and-play, we've included "Fat Cow" (Fake Neuro) - a character inspired by Neuro-sama but with a mischievous, tsundere, funny personality with occasional temper flashes and rare gentle moments.

The hope is to learn from Neuro, understand, then create something new and personally suitable.

I'm incredibly passionate about this project. We've achieved roughly 30% of planned features, including personality definition and memory systems. Upcoming development focuses on core personality traits - making it truly human-like with persistent emotional states. The most human-like aspects (long-term emotional states) will be implemented within two months. Gaming together, video watching, wake-up calls, and similar features will be largely complete by June 1st, reaching 60% completion.

The goal is implementing all envisioned features this year.

## Acknowledgments

**QQ Group:** Thanks to 菊花茶洋参 for creating the Fat Cow app cover

**TTS Integration Credit:**
GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS