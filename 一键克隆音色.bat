@echo off
chcp 65001 >nul 2>&1
echo Data processing pipeline starting...
echo.

:: Check if conda is available
echo Checking conda installation...
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: conda command not found
    echo Please check:
    echo 1. Anaconda/Miniconda is installed
    echo 2. conda is added to PATH
    echo 3. Try running: conda init cmd.exe
    pause
    exit /b 1
)
echo conda found: OK

:: Initialize conda for current session
echo Initializing conda for current session...

:: First, find conda installation path
echo Detecting conda installation...
for /f "tokens=*" %%i in ('where conda 2^>nul') do set "CONDA_EXE=%%i"
if not defined CONDA_EXE (
    echo ERROR: conda not found in PATH
    pause
    exit /b 1
)

:: Extract conda base directory
for %%i in ("%CONDA_EXE%") do set "CONDA_BASE=%%~dpi"
set "CONDA_BASE=%CONDA_BASE:~0,-1%"
echo Found conda at: %CONDA_BASE%

:: Define environment name (you can change this)
set "ENV_NAME=my-neuro"

:: Try to activate conda environment using different methods
echo Attempting to activate conda environment: %ENV_NAME%

:: Method 1: Standard conda activate
call conda activate %ENV_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo Successfully activated using method 1: conda activate
    goto env_activated
)

:: Method 2: Initialize conda first, then activate
echo Method 1 failed, trying with conda init...
call conda init cmd.exe >nul 2>&1
call conda activate %ENV_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo Successfully activated using method 2: conda init + activate
    goto env_activated
)

:: Method 3: Try with conda.bat
echo Method 2 failed, trying conda.bat...
if exist "%CONDA_BASE%\Scripts\conda.bat" (
    call "%CONDA_BASE%\Scripts\conda.bat" activate %ENV_NAME% >nul 2>&1
    if %errorlevel% equ 0 (
        echo Successfully activated using method 3: conda.bat
        goto env_activated
    )
)

:: Method 4: Try activating base first, then target environment
echo Method 3 failed, trying base activation first...
if exist "%CONDA_BASE%\Scripts\activate.bat" (
    call "%CONDA_BASE%\Scripts\activate.bat" >nul 2>&1
    call conda activate %ENV_NAME% >nul 2>&1
    if %errorlevel% equ 0 (
        echo Successfully activated using method 4: base then %ENV_NAME%
        goto env_activated
    )
)

:: Method 5: Auto-detect environment path and set directly
echo All conda methods failed, trying direct path method...
set "ENV_PATH="
if exist "%CONDA_BASE%\envs\%ENV_NAME%" (
    set "ENV_PATH=%CONDA_BASE%\envs\%ENV_NAME%"
) else (
    :: Try to find environment in conda env list
    for /f "tokens=1,2" %%a in ('conda env list 2^>nul ^| findstr /C:"%ENV_NAME%"') do (
        if "%%a"=="%ENV_NAME%" set "ENV_PATH=%%b"
    )
)

if defined ENV_PATH (
    echo Using direct python path from: %ENV_PATH%
    set "CONDA_PREFIX=%ENV_PATH%"
    set "PATH=%ENV_PATH%;%ENV_PATH%\Scripts;%ENV_PATH%\Library\bin;%PATH%"
    goto env_activated
) else (
    echo ERROR: Could not find environment %ENV_NAME%
    goto env_failed
)

:env_failed
echo ERROR: All activation methods failed
echo Available environments:
conda env list 2>nul || echo Could not list environments
echo.
echo Please check:
echo 1. Environment name is correct (currently looking for: %ENV_NAME%)
echo 2. Conda is properly installed
echo 3. Environment exists
pause
exit /b 1

:env_activated

:: Verify current environment
echo Current Python path:
where python 2>nul || echo Python not found in PATH
echo Current conda environment: %CONDA_DEFAULT_ENV%
echo.

:: Get current bat file directory
set "current_dir=%~dp0"

:: Construct fine_tuning path
set "package_path=%current_dir%fine_tuning"

:: Add to PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%package_path%

setlocal enabledelayedexpansion

:: Get current script directory
set "scriptDir=%~dp0"

:: Define output folder paths to clear
set "outputDir=%current_dir%fine_tuning\output\"
set "folders=asr sliced uvr5"

:: Check if output directory exists
if not exist "%outputDir%" (
    echo ERROR: Directory does not exist - %outputDir%
    pause
    exit /b 1
)

:: Clear each subfolder
for %%f in (%folders%) do (
    set "currentFolder=%outputDir%%%f\"

    if exist "!currentFolder!" (
        echo Clearing folder: !currentFolder!

        :: Delete all files and subfolders
        del /q "!currentFolder!*" >nul 2>&1
        for /d %%d in ("!currentFolder!*") do (
            rd /s /q "%%d" >nul 2>&1
        )

        echo Cleared !currentFolder!
    ) else (
        echo WARNING: Folder does not exist - !currentFolder!
    )
)

REM 2. Get language parameter
:input_language
set /p language=Please enter language code (en/zh): 
if "%language%"=="" (
    echo Language code cannot be empty!
    goto input_language
)
if not "%language%"=="en" if not "%language%"=="zh" (
    echo Invalid language code, please enter en or zh!
    goto input_language
)

REM 3. Get model name parameter
:input_model
set /p model_name=Please enter TTS model name: 
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

REM 4. Run uvr_pipe.py
echo Running uvr_pipe.py...
python fine_tuning/tools/uvr5/uvr_pipe.py "cuda" True
if %errorlevel% neq 0 (
    echo uvr_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 5. Run slicer_pipe.py
echo Running slicer_pipe.py...
python fine_tuning/tools/slicer_pipe.py
if %errorlevel% neq 0 (
    echo slicer_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 6. Run asr_pipe.py
echo Running asr_pipe.py (language: %language%)...
python fine_tuning/tools/asr_pipe.py -l %language%
if %errorlevel% neq 0 (
    echo asr_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 7. Run format_pipe.py
echo Running format_pipe.py (model: %model_name%)...
python fine_tuning/format_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo format_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 8. Run trainer_pipe.py
echo Running trainer_pipe.py (model: %model_name%)...
python fine_tuning/trainer_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo trainer_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 9. Run afterprocess_pipe.py
echo Running afterprocess_pipe.py (model: %model_name%)...
python fine_tuning/afterprocess_pipe.py -n "%model_name%"
if %errorlevel% neq 0 (
    echo afterprocess_pipe.py execution failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo All scripts completed successfully!
pause
