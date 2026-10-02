@echo off
REM %~dp0 = the folder this .bat lives in, WITH a trailing backslash.
REM Everything below is relative to it, so the launcher works from any drive or
REM folder (it used to hardcode the original author's G:\ paths).
set "VN_ROOT=%~dp0"
set "VN_HOME=%VN_ROOT%_video_nut"
set PATH=%VN_HOME%\python;%VN_HOME%\python\Scripts;%VN_HOME%\tools\bin;%APPDATA%\npm;%PATH%

:menu
cls
echo ====================================================
echo                 🎬 VideoNut Launcher 🎬
echo ====================================================
echo  Project Root: %VN_ROOT%
echo  Python Path : %VN_HOME%\python
echo  FFmpeg Path : %VN_HOME%\tools\bin
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
echo   [8] Render Narration (Narrator / TTS)
echo   [9] Exit
echo.
echo ====================================================
set /p choice="Enter option (1-9): "

if "%choice%"=="1" goto launch_gemini
if "%choice%"=="2" goto launch_claude
if "%choice%"=="3" goto launch_opencode
if "%choice%"=="4" goto launch_qwen
if "%choice%"=="5" goto launch_aider
if "%choice%"=="6" goto run_check
if "%choice%"=="7" goto run_setup
if "%choice%"=="8" goto run_voice
if "%choice%"=="9" goto end
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
python "%VN_HOME%\tools\check_env.py"
pause
goto menu

:run_setup
echo Launching Setup Script...
node "%VN_HOME%\setup.js"
pause
goto menu

:run_voice
set /p vnproj="Path to the project folder: "
echo Estimating narration cost (nothing is billed yet)...
python "%VN_HOME%\tools\audio\tts_engine.py" --project "%vnproj%" --dry-run
echo.
set /p vngo="Render the narration now? (Y/N): "
if /i "%vngo%"=="Y" python "%VN_HOME%\tools\audio\tts_engine.py" --project "%vnproj%" --mode final --yes
pause
goto menu

:end
echo Thank you for using VideoNut!
exit /b
