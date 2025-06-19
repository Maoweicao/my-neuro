@echo off
title 启动所有API服务
:: 使用脚本所在目录作为工作目录
cd %~dp0

echo 正在启动第一个API服务...
:: 启动第一个API
start cmd /k "call conda activate my-neuro && python asr_api.py"
timeout /t 2 /nobreak >nul

echo 正在启动第二个API服务...
:: 启动第二个API
start cmd /k "call conda activate my-neuro &&cd tts-studio &&python tts_api.py -p 5000 -d cuda -s tts-model/merge.pth -dr tts-model/neuro/01.wav -dt "Hold on please, I'm busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday." -dl "en"
timeout /t 1 /nobreak >nul

echo 正在启动第三个API服务...
:: 启动第三个API (BERT)
start cmd /k "call conda activate my-neuro && python bert_api.py"
timeout /t 1 /nobreak >nul

echo 正在启动第四个API服务...
:: 启动第四个API (Mnemosyne-bert)
start cmd /k "call conda activate my-neuro && python Mnemosyne-bert\api_go.py"

echo 所有API服务已启动!
