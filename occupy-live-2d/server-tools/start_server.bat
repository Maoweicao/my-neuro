@echo off
cd /d %~dp0
echo 正在启动MCP服务器...
"..\node\node.exe" server.js
if %ERRORLEVEL% NEQ 0 pause
exit
