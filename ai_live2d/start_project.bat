@echo off
chcp 65001
cd /d %~dp0
echo 正在启动桌宠应用...

REM 记录当前脚本的PID
echo Main Script PID: %PID% > process_info.txt

REM 使用PowerShell启动主程序并记录PID
powershell -Command "& { try { $process = Start-Process -FilePath 'uv' -ArgumentList 'run main.py' -PassThru -NoNewWindow; $process.Id | Out-File -FilePath 'main_pid.txt' -Encoding UTF8; Write-Host 'Main process PID:' $process.Id; Wait-Process -Id $process.Id } catch { Write-Host 'Error starting process:' $_.Exception.Message } }"

REM 清理PID文件
if exist main_pid.txt del main_pid.txt
if exist process_info.txt del process_info.txt

pause