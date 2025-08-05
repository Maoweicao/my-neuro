@echo off
title 启动所有API服务
:: 使用脚本所在目录作为工作目录
cd /d %~dp0
start cmd /k "call conda activate my-ai & python test.py"
echo 所有API服务已启动!