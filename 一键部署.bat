@echo off
title 启动所有API服务
:: 使用脚本所在目录作为工作目录
cd /d %~dp0
pip install modelscope requests
start cmd /k "python neural_deploy.py"
echo 所有API服务已启动!