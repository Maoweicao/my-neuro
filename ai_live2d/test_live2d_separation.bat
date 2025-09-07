@echo off
chcp 65001 >nul
title Live2D预览进程分离测试

echo ========================================
echo    Live2D预览进程分离功能测试
echo ========================================
echo.

echo 正在启动测试...
python test_live2d_process_separation.py

echo.
echo 测试完成！
pause
