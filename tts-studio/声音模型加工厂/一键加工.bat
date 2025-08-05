@echo off
chcp 65001
echo 正在开始...
cd /d %~dp0
call conda activate my-neuro
python 处理.py
echo 执行完成
pause
