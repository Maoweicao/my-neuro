@echo off
REM MCP工具自动下载器启动脚本
REM 此脚本会自动下载和安装UV和Bun工具包管理器

echo MCP工具自动下载器
echo ===================
echo.
echo 此脚本将自动下载和安装以下工具：
echo - UV (Python包管理器)
echo - Bun (JavaScript运行时)
echo.
echo 安装过程可能需要一些时间，请耐心等待...
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python。请确保Python已安装并在PATH中。
    pause
    exit /b 1
)

echo 正在启动下载器...
python utils\mcp_tool_downloader.py

if errorlevel 1 (
    echo.
    echo 下载过程中出现错误。请检查网络连接并重试。
    pause
    exit /b 1
)

echo.
echo 安装完成！请按照上述说明更新PATH环境变量。
echo 然后重新启动应用程序以使用新的MCP工具。
echo.
pause
