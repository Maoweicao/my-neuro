# TTS启动脚本
# 用于启动TTS服务和相关组件

param(
    [string]$ConfigPath = "config.json",
    [string]$LogPath = "logs\tts_service.log",
    [switch]$Verbose
)

# 设置编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置错误处理
$ErrorActionPreference = "Stop"

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== AI桌宠TTS服务启动脚本 ===" -ForegroundColor Green
Write-Host "脚本目录: $ScriptDir" -ForegroundColor Gray
Write-Host "配置文件: $ConfigPath" -ForegroundColor Gray
Write-Host "日志文件: $LogPath" -ForegroundColor Gray
Write-Host ""

# 检查配置文件是否存在
if (-not (Test-Path $ConfigPath)) {
    Write-Error "配置文件不存在: $ConfigPath"
    exit 1
}

# 检查Python环境
Write-Host "检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "未找到Python环境，请确保Python已正确安装"
    exit 1
}

# 检查虚拟环境
Write-Host "检查虚拟环境..." -ForegroundColor Yellow
$venvPath = ".venv"
if (Test-Path $venvPath) {
    Write-Host "找到虚拟环境: $venvPath" -ForegroundColor Green
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "激活虚拟环境..." -ForegroundColor Yellow
        & $activateScript
    }
} elseif (Test-Path "uv") {
    Write-Host "使用uv包管理器..." -ForegroundColor Green
    # uv环境通常不需要显式激活
} else {
    Write-Warning "未找到虚拟环境，将使用系统Python环境"
}

# 检查必要的Python包
Write-Host "检查必要的Python包..." -ForegroundColor Yellow
$requiredPackages = @("PyQt5", "aiohttp", "websockets", "sounddevice", "numpy")
foreach ($package in $requiredPackages) {
    try {
        python -c "import $package" 2>$null
        if ($Verbose) {
            Write-Host "✓ $package" -ForegroundColor Green
        }
    } catch {
        Write-Warning "可能缺少包: $package"
    }
}

# 创建日志目录
$logDir = Split-Path -Parent $LogPath
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "创建日志目录: $logDir" -ForegroundColor Green
}

# 设置环境变量
Write-Host "设置环境变量..." -ForegroundColor Yellow
$env:PYTHONPATH = $ScriptDir
$env:QT_QPA_PLATFORM = "windows:fontengine=freetype"
$env:PYTHONIOENCODING = "utf-8"

# 启动TTS服务
Write-Host "启动TTS服务..." -ForegroundColor Green
Write-Host "日志将输出到: $LogPath" -ForegroundColor Gray
Write-Host ""

# 构建启动命令
$pythonCmd = "python"
$scriptPath = "main.py"

# 检查是否使用uv
if (Test-Path "uv") {
    $pythonCmd = "uv run python"
    Write-Host "使用uv运行环境" -ForegroundColor Cyan
}

# 启动命令
$startCommand = "$pythonCmd $scriptPath --tts-only --config $ConfigPath"

Write-Host "执行命令: $startCommand" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

try {
    # 执行启动命令
    Invoke-Expression $startCommand
} catch {
    Write-Error "启动TTS服务失败: $($_.Exception.Message)"
    exit 1
} finally {
    Write-Host ""
    Write-Host "TTS服务已停止" -ForegroundColor Yellow
}
