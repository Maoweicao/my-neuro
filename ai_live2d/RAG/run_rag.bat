@echo off
chcp 65001
cd /d %~dp0
uv run rag_api.py
pause