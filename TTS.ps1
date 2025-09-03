# 设置输出编码为UTF-8以支持UTF-8语音
Write-Host "步骤 1: 设置输出编码为UTF-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 使用脚本所在目录作为工作目录
Write-Host "步骤 2: 设置工作目录为脚本所在目录"
Set-Location $PSScriptRoot

# 激活conda环境
Write-Host "步骤 3: 激活conda环境 my-neuro-tts"
& conda activate my-neuro-tts

# 设置环境变量以解决OpenMP冲突
Write-Host "步骤 4: 设置环境变量 KMP_DUPLICATE_LIB_OK"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"

# 切换到tts-studio目录
Write-Host "步骤 5: 切换到tts-studio目录"
Set-Location tts-studio

# 运行move_nltk.py
Write-Host "步骤 6: 运行move_nltk.py"
& python move_nltk.py

# 运行tts_api.py
Write-Host "步骤 7: 运行tts_api.py"
& python tts_api.py -p 5000 -d cuda -s tts-model/merge.pth -dr tts-model/neuro/01.wav -dt 'Hold on please, I''m busy. Okay, I think I heard him say he wants me to stream Hollow Knight on Tuesday and Thursday.' -dl "en"

# 暂停
Write-Host "步骤 8: 脚本执行完成，等待用户输入"
Read-Host "Press Enter to exit"
