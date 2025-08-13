chcp 65001
@echo off
title 启动所有API服务
:: 使用脚本所在目录作为工作目录
cd %~dp0

echo 正在启动API服务...
start cmd /k "call conda activate my-neuro && python run_server.py -a '012'"
