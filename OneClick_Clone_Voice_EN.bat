@echo off
rem ================= One-Click Voice Clone (English) =================
rem This script mirrors "一键克隆音色.bat" but with English prompts/output.
rem 可选：通过环境变量跳过交互输入（UI可提前设置）：
rem   VC_LANG=en|zh      -> Language code
rem   VC_ROLE=<name>     -> Model name
rem   NO_PAUSE=1         -> 结束时不暂停

setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
chcp 65001 >nul

echo [Init] Preparing environment...

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: conda command not found. Please install Miniconda/Anaconda and reopen terminal.
    if not defined NO_PAUSE pause
    exit /b 1
)

call conda activate my-neuro
if %errorlevel% neq 0 (
    echo Error: failed to activate conda environment: my-neuro
    if not defined NO_PAUSE pause
    exit /b 1
)

set "current_dir=%~dp0"
set "package_path=%current_dir%fine_tuning"
set "PYTHONPATH=%PYTHONPATH%;%package_path%"
set "SKIP_UVR=%SKIP_UVR%"

set "outputDir=%current_dir%fine_tuning\output"
set "folders=asr sliced uvr5"

if not exist "%outputDir%" (
    echo Error: Output directory not found - %outputDir%
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [Clean] Resetting output folders...
set "outputBase=%outputDir%"
echo  - Reset: %outputBase%\asr
rd /s /q "%outputBase%\asr" >nul 2>&1
md "%outputBase%\asr" >nul 2>&1
echo  - Reset: %outputBase%\sliced
rd /s /q "%outputBase%\sliced" >nul 2>&1
md "%outputBase%\sliced" >nul 2>&1
echo  - Reset: %outputBase%\uvr5
rd /s /q "%outputBase%\uvr5" >nul 2>&1
md "%outputBase%\uvr5" >nul 2>&1

echo [Deps] Checking optional Python packages...
python -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('yaml') else 1)"
if %errorlevel% neq 0 (
    echo  - Installing PyYAML...
    python -m pip install -q PyYAML
)
python -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('transformers') else 1)"
if %errorlevel% neq 0 (
    echo  - Installing transformers...
    python -m pip install -q transformers
)
echo.

rem ---- Gather inputs (env vars preferred; non-interactive with safe defaults) ----
if defined VC_LANG (
    set "language=%VC_LANG%"
) else (
    set "language=zh"
    echo [Info] VC_LANG not set; defaulting to zh.
)

if /i not "%language%"=="en" if /i not "%language%"=="zh" (
    echo Error: Invalid language code "%language%". Allowed: en or zh.
    if not defined NO_PAUSE pause
    exit /b 1
)

if defined VC_ROLE (
    set "model_name=%VC_ROLE%"
) else (
    set "model_name=my-voice"
    echo [Info] VC_ROLE not set; defaulting to my-voice.
)

echo.
echo [Startup Params]
echo  - current_dir: %current_dir%
echo  - PYTHONPATH: %PYTHONPATH%
echo  - outputDir: %outputDir%
echo  - language: %language%
echo  - model_name: %model_name%
echo  - NO_PAUSE: %NO_PAUSE%
set "_src_state=NOT FOUND"
if exist "fine_tuning\input\audio.mp3" set "_src_state=found"
echo  - source_audio: fine_tuning\input\audio.mp3 (%_src_state%)
echo.

rem ---- Pipeline ----
echo [Step 1/6] UVR separation ...
if /i "%SKIP_UVR%"=="1" (
    echo  - SKIP_UVR=1, skipping UVR separation.
) else (
    python fine_tuning\tools\uvr5\uvr_pipe.py "cuda" True
    if %errorlevel% neq 0 (
        echo  - UVR failed with code %errorlevel%, will continue if vocal.wav exists.
    )
)
if not exist "%outputDir%\uvr5\vocal.wav" (
    echo  - vocal.wav not found; copying input audio as fallback.
    if exist "fine_tuning\input\audio.mp3" (
        ffmpeg -y -i "fine_tuning\input\audio.mp3" -vn -acodec pcm_s16le -ac 2 -ar 44100 "%outputDir%\uvr5\vocal.wav"
    ) else (
        echo  - Error: no input audio found.
        if not defined NO_PAUSE pause
        exit /b 1
    )
)

echo [Step 2/6] Running slicer_pipe.py ...
python fine_tuning\tools\slicer_pipe.py
if %errorlevel% neq 0 (
    echo slicer_pipe.py failed with error code: %errorlevel%
    if not defined NO_PAUSE pause
    exit /b %errorlevel%
)

echo [Step 3/6] Running asr_pipe.py ...
python fine_tuning\tools\asr_pipe.py -l %language%
if %errorlevel% neq 0 (
    echo asr_pipe.py failed with error code: %errorlevel%
    if not defined NO_PAUSE pause
    exit /b %errorlevel%
)

echo [Step 4/6] Running format_pipe.py ...
python fine_tuning\format_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo format_pipe.py failed with error code: %errorlevel%
    echo  - If this is the first run, ensure 'transformers' is installed and ASR produced texts in fine_tuning\logs\%model_name%.
    if not defined NO_PAUSE pause
    exit /b %errorlevel%
)

echo [Step 5/6] Running trainer_pipe.py ...
python fine_tuning\trainer_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo trainer_pipe.py failed with error code: %errorlevel%
    if not defined NO_PAUSE pause
    exit /b %errorlevel%
)

echo [Step 6/6] Running afterprocess_pipe.py ...
python fine_tuning\afterprocess_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo afterprocess_pipe.py failed with error code: %errorlevel%
    if not defined NO_PAUSE pause
    exit /b %errorlevel%
)

echo.
echo Completed: All steps finished successfully.
if not defined NO_PAUSE pause
exit /b 0
