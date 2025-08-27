@echo off
:: TTS服务启动脚本 - 专门为终端控制室使用
:: 使用脚本所在目录作为工作目录
cd %~dp0

echo 正在激活conda环境...
call conda activate my-neuro
if errorlevel 1 (
    echo 错误: 无法激活conda环境 my-neuro
    pause
    exit /b 1
)

echo 切换到TTS目录...
cd tts-studio
if errorlevel 1 (
    echo 错误: 找不到tts-studio目录
    pause
    exit /b 1
)

echo 移动NLTK数据...
python move_nltk.py

echo 启动TTS API服务器（带默认参考音频）...
python tts_api.py -p 5000 -d cuda -s tts-model/merge.pth -dr tts-model/neuro/01.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "en"
if errorlevel 1 (
    echo 错误: TTS服务启动失败
    pause
    exit /b 1
)
