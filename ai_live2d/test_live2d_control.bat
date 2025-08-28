@echo off
chcp 65001
echo ===========================================
echo        Live2D 控制功能测试
echo ===========================================
echo.
echo 本脚本将测试UI与Live2D桌宠之间的控制连接
echo.
echo 测试内容：
echo 1. 文件触发器控制（动作和表情）
echo 2. WebAPI控制（如果服务可用）
echo 3. 连接状态检查
echo.
echo 使用前请确保：
echo - Live2D桌宠服务已启动
echo - WebAPI服务已启动（可选）
echo.
pause
echo.
echo 开始测试...
python test_live2d_control.py
echo.
echo 测试完成！
pause
