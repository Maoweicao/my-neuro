@echo off
cd %~dp0
call conda activate my-neuro
chcp 65001 >nul

echo Data processing pipeline started...
echo.

set "current_dir=%~dp0"
set "package_path=%current_dir%fine_tuning"
set PYTHONPATH=%PYTHONPATH%;%package_path%
setlocal enabledelayedexpansion

set "outputDir=%current_dir%fine_tuning\output\"
set "folders=asr sliced uvr5"

if not exist "%outputDir%" (
    echo Error: Output directory not found - %outputDir%
    pause
    exit /b 1
)

for %%f in (%folders%) do (
    set "currentFolder=%outputDir%%%f\"
    if exist "!currentFolder!" (
        echo Cleaning folder: !currentFolder!
        del /q "!currentFolder!*" >nul 2>&1
        for /d %%d in ("!currentFolder!*") do (
            rd /s /q "%%d" >nul 2>&1
        )
        echo Cleaned !currentFolder!
    ) else (
        echo Warning: Folder not found - !currentFolder!
    )
)

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: conda command not found
    pause
    exit /b
)

:input_language
set /p language=Enter language code (en/zh): 
if "%language%"=="" (
    echo Language code cannot be empty!
    goto input_language
)
if not "%language%"=="en" if not "%language%"=="zh" (
    echo Invalid language code, please enter en or zh!
    goto input_language
)

:input_model
set /p model_name=Enter TTS model name: 
if "%model_name%"=="" (
    echo Model name cannot be empty!
    goto input_model
)

echo.
echo Parameters set:
echo Language: %language%
echo Model name: %model_name%
echo.
pause

echo Running uvr_pipe.py...
python fine_tuning\tools\uvr5\uvr_pipe.py "cuda" True
if %errorlevel% neq 0 (
    echo uvr_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Running slicer_pipe.py...
python fine_tuning\tools\slicer_pipe.py
if %errorlevel% neq 0 (
    echo slicer_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Running asr_pipe.py...
python fine_tuning\tools\asr_pipe.py -l %language%
if %errorlevel% neq 0 (
    echo asr_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Running format_pipe.py...
python fine_tuning\format_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo format_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Running trainer_pipe.py...
python fine_tuning\trainer_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo trainer_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Running afterprocess_pipe.py...
python fine_tuning\afterprocess_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo afterprocess_pipe.py failed with error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo All scripts completed successfully!
pause