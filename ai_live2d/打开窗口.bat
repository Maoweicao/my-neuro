@echo off
chcp 65001
title 打开窗口
:: 肥牛保佑，永无bug
cd %~dp0
uv run UI.py
pause