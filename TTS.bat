@echo off
title 启动所有API服务
:: 使用脚本所在目录作为工作目录
cd %~dp0
start cmd /k "call conda activate my-neuro &&cd tts-studio &&python tts_api.py -p 5000 -d cuda -s tts-model/merge.pth -dr tts-model/neuro/01.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "en"
echo 所有API服务已启动!
