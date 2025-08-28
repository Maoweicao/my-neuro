@echo off
chcp 65001
echo.
echo ==========================================
echo       WebAPI 功能测试工具
echo ==========================================
echo.
echo 请选择要执行的操作：
echo.
echo 1. 启动 UI 程序（配置和启动WebAPI服务）
echo 2. 运行完整 WebAPI 测试脚本
echo 3. 运行快速测试脚本
echo 4. 运行 cURL 样式测试
echo 5. 启动交互式 WebAPI 客户端
echo 6. 查看使用说明
echo 7. 退出
echo.

:menu
set /p choice="请输入选项 (1-7): "

if "%choice%"=="1" (
    echo.
    echo 启动 UI 程序...
    python UI.py
    goto end
)

if "%choice%"=="2" (
    echo.
    echo 运行完整 WebAPI 测试脚本...
    python webapi_test_script.py
    pause
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo 运行快速测试脚本...
    python quick_test.py
    pause
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo 运行 cURL 样式测试...
    echo 示例用法：
    echo   python curl_test.py --message "你好"
    echo   python curl_test.py --status
    echo.
    python curl_test.py
    pause
    goto menu
)

if "%choice%"=="5" (
    echo.
    echo 启动交互式客户端...
    python webapi_client.py
    pause
    goto menu
)

if "%choice%"=="6" (
    echo.
    echo 查看使用说明...
    if exist WebAPI_Usage.md (
        start notepad WebAPI_Usage.md
    ) else (
        echo 使用说明文件不存在！
    )
    goto menu
)

if "%choice%"=="7" (
    goto end
)

echo 无效选项，请重新选择！
goto menu

:end
echo.
echo 感谢使用！
pause
