@echo off
REM Add local Python, FFmpeg, and AppData NPM prefix to PATH for this session
set PATH=G:\youtuber\work_space\AI _TEAM\_video_nut\python;G:\youtuber\work_space\AI _TEAM\_video_nut\python\Scripts;G:\youtuber\work_space\AI _TEAM\_video_nut\tools\bin;%APPDATA%\npm;%PATH%

:menu
cls
echo ====================================================
echo                 🎬 VideoNut Launcher 🎬
echo ====================================================
echo  Python Path: G:\youtuber\work_space\AI _TEAM\_video_nut\python
echo  FFmpeg Path: G:\youtuber\work_space\AI _TEAM\_video_nut\tools\bin
echo ====================================================
echo.
echo  Choose an AI CLI tool or utility to run:
echo.
echo   [1] Google Gemini CLI
echo   [2] Anthropic Claude Code
echo   [3] OpenCode CLI
echo   [4] Alibaba Qwen CLI
echo   [5] Aider CLI
echo   [6] Run Environment Check
echo   [7] Run Package Setup / CLI Installer
echo   [8] Exit
echo.
echo ====================================================
set /p choice="Enter option (1-8): "

if "%choice%"=="1" goto launch_gemini
if "%choice%"=="2" goto launch_claude
if "%choice%"=="3" goto launch_opencode
if "%choice%"=="4" goto launch_qwen
if "%choice%"=="5" goto launch_aider
if "%choice%"=="6" goto run_check
if "%choice%"=="7" goto run_setup
if "%choice%"=="8" goto end
goto menu

:launch_gemini
where gemini >nul 2>nul
if %errorlevel% neq 0 (
    echo Gemini CLI is not installed.
    set /p inst="Would you like to install it now? (Y/N): "
    if /i "%inst%"=="Y" (
        echo Installing Gemini CLI globally...
        npm install -g @google/gemini-cli
    ) else (
        pause
        goto menu
    )
)
echo Starting Gemini CLI...
gemini
pause
goto menu

:launch_claude
where claude >nul 2>nul
if %errorlevel% neq 0 (
    echo Claude Code is not installed.
    set /p inst="Would you like to install it now? (Y/N): "
    if /i "%inst%"=="Y" (
        echo Installing Claude Code globally...
        npm install -g @anthropic-ai/claude-code
    ) else (
        pause
        goto menu
    )
)
echo Starting Claude Code...
claude
pause
goto menu

:launch_opencode
where opencode >nul 2>nul
if %errorlevel% neq 0 (
    echo OpenCode CLI is not installed.
    set /p inst="Would you like to install it now? (Y/N): "
    if /i "%inst%"=="Y" (
        echo Installing OpenCode CLI globally...
        npm install -g opencode-ai
    ) else (
        pause
        goto menu
    )
)
echo Starting OpenCode CLI...
opencode
pause
goto menu

:launch_qwen
where qwen >nul 2>nul
if %errorlevel% neq 0 (
    echo Qwen CLI is not installed.
    set /p inst="Would you like to install it now? (Y/N): "
    if /i "%inst%"=="Y" (
        echo Installing Qwen CLI globally...
        npm install -g @qwen-code/qwen-code
    ) else (
        pause
        goto menu
    )
)
echo Starting Qwen CLI...
qwen
pause
goto menu

:launch_aider
where aider >nul 2>nul
if %errorlevel% neq 0 (
    echo Aider CLI is not installed in the environment.
    set /p inst="Would you like to install it now? (Y/N): "
    if /i "%inst%"=="Y" (
        echo Installing Aider CLI via pip...
        python -m pip install aider-chat
    ) else (
        pause
        goto menu
    )
)
echo Starting Aider CLI...
aider
pause
goto menu

:run_check
echo Running Environment Check...
python "G:/youtuber/work_space/AI _TEAM/_video_nut/tools/check_env.py"
pause
goto menu

:run_setup
echo Launching Setup Script...
node "G:/youtuber/work_space/AI _TEAM/_video_nut/setup.js"
pause
goto menu

:end
echo Thank you for using VideoNut!
exit /b
