@echo off
title 设置虚拟环境地址
:: 改为本机python地址
python set_venv_path.py
uv add pyqt5-tools "PyQt-Fluent-Widgets[full]"
pause