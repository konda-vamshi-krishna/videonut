#!/usr/bin/env node

/**
 * VideoNut Setup Script
 * Run this after cloning from GitHub to install all dependencies
 * 
 * Usage: node setup.js
 * Or:    npm run setup
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const https = require('https');
const readline = require('readline');

// Colors for console
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m',
    cyan: '\x1b[36m'
};

function log(msg, color = 'reset') {
    console.log(`${colors[color]}${msg}${colors.reset}`);
}

function header(msg) {
    console.log('\n' + '═'.repeat(60));
    log(`🎬 ${msg}`, 'bright');
    console.log('═'.repeat(60) + '\n');
}

function success(msg) { log(`✅ ${msg}`, 'green'); }
function warning(msg) { log(`⚠️  ${msg}`, 'yellow'); }
function error(msg) { log(`❌ ${msg}`, 'red'); }
function info(msg) { log(`ℹ️  ${msg}`, 'cyan'); }
function progress(msg) { process.stdout.write(`\r⏳ ${msg}`); }

function commandExists(cmd) {
    try {
        const isWindows = process.platform === 'win32';
        const checkCmd = isWindows ? `where ${cmd}` : `which ${cmd}`;
        execSync(checkCmd, { stdio: 'pipe' });
        return true;
    } catch {
        return false;
    }
}

function ask(question) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    return new Promise(resolve => {
        rl.question(question, answer => {
            rl.close();
            resolve(answer.trim());
        });
    });
}

function downloadFile(url, dest, description = 'Downloading') {
    return new Promise((resolve, reject) => {
        const request = (currentUrl) => {
            const protocol = currentUrl.startsWith('https') ? require('https') : require('http');
            protocol.get(currentUrl, response => {
                if (response.statusCode === 302 || response.statusCode === 301) {
                    request(response.headers.location);
                    return;
                }
                if (response.statusCode !== 200) {
                    reject(new Error(`Download failed: ${response.statusCode}`));
                    return;
                }

                const totalSize = parseInt(response.headers['content-length'], 10);
                let downloadedSize = 0;
                const file = fs.createWriteStream(dest);

                response.on('data', chunk => {
                    downloadedSize += chunk.length;
                    if (totalSize) {
                        const percent = Math.round((downloadedSize / totalSize) * 100);
                        const mb = (downloadedSize / 1024 / 1024).toFixed(1);
                        const totalMb = (totalSize / 1024 / 1024).toFixed(1);
                        progress(`${description}: ${mb}MB / ${totalMb}MB (${percent}%)`);
                    }
                });

                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    console.log('');
                    resolve();
                });
                file.on('error', reject);
            }).on('error', reject);
        };
        request(url);
    });
}

async function extractZip(zipPath, destDir) {
    const isWindows = process.platform === 'win32';
    if (isWindows) {
        execSync(`powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`, { stdio: 'pipe' });
    } else {
        execSync(`unzip -o "${zipPath}" -d "${destDir}"`, { stdio: 'pipe' });
    }
}

async function main() {
    const projectDir = path.resolve(__dirname);
    const isWindows = process.platform === 'win32';

    header('VideoNut Setup - GitHub Clone Edition');
    info(`Setting up in: ${projectDir}\n`);

    // ═══════════════════════════════════════════════════════════════
    // STEP 1: Check/Install Python
    // ═══════════════════════════════════════════════════════════════
    header('Step 1/4: Checking Python');

    let pythonCmd = null;

    // Check for system Python (must actually work, not just exist)
    // Windows has a fake 'python' command that opens Microsoft Store
    function isPythonWorking(cmd) {
        try {
            const result = execSync(`"${cmd}" --version`, { stdio: 'pipe', timeout: 5000 });
            return result.toString().toLowerCase().includes('python');
        } catch {
            return false;
        }
    }

    if (isPythonWorking('python3')) {
        pythonCmd = 'python3';
        success('Found Python3');
    } else if (isPythonWorking('python')) {
        pythonCmd = 'python';
        success('Found Python');
    } else {
        info('No working Python found on system');
    }

    if (!pythonCmd && isWindows) {
        info('Python not found. Downloading embedded Python...');

        const pythonDir = path.join(projectDir, 'python');
        const pythonVersion = '3.12.1';
        const pythonZipUrl = `https://www.python.org/ftp/python/${pythonVersion}/python-${pythonVersion}-embed-amd64.zip`;
        const pythonZipPath = path.join(projectDir, 'python.zip');

        try {
            fs.mkdirSync(pythonDir, { recursive: true });
            await downloadFile(pythonZipUrl, pythonZipPath, 'Downloading Python');

            info('Extracting Python...');
            await extractZip(pythonZipPath, pythonDir);
            fs.unlinkSync(pythonZipPath);

            // Download get-pip.py
            const getPipPath = path.join(pythonDir, 'get-pip.py');
            await downloadFile('https://bootstrap.pypa.io/get-pip.py', getPipPath, 'Downloading pip');

            // Enable pip
            const pthFile = path.join(pythonDir, 'python312._pth');
            if (fs.existsSync(pthFile)) {
                let content = fs.readFileSync(pthFile, 'utf8');
                content = content.replace('#import site', 'import site');
                fs.writeFileSync(pthFile, content);
            }

            // Install pip
            info('Installing pip...');
            execSync(`"${path.join(pythonDir, 'python.exe')}" "${getPipPath}"`, { stdio: 'inherit' });

            pythonCmd = path.join(pythonDir, 'python.exe');
            success('Python installed locally!');
        } catch (e) {
            warning(`Could not auto-install Python: ${e.message}`);
            console.log('Please install Python from: https://python.org/downloads');
        }
    } else if (!pythonCmd) {
        warning('Python not found. Please install manually.');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 2: Check/Install FFmpeg
    // ═══════════════════════════════════════════════════════════════
    header('Step 2/4: Checking FFmpeg');

    const toolsBinDir = path.join(projectDir, 'tools', 'bin');
    const ffmpegPath = path.join(toolsBinDir, isWindows ? 'ffmpeg.exe' : 'ffmpeg');
    const ffprobePath = path.join(toolsBinDir, isWindows ? 'ffprobe.exe' : 'ffprobe');

    if (fs.existsSync(ffmpegPath) && fs.existsSync(ffprobePath)) {
        success('FFmpeg already in tools/bin/');
    } else if (commandExists('ffmpeg')) {
        success('FFmpeg found in system PATH');
    } else if (isWindows) {
        info('Downloading FFmpeg...');

        const ffmpegUrl = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip';
        const ffmpegZipPath = path.join(projectDir, 'ffmpeg.zip');
        const ffmpegTempDir = path.join(projectDir, 'ffmpeg_temp');

        try {
            fs.mkdirSync(toolsBinDir, { recursive: true });
            await downloadFile(ffmpegUrl, ffmpegZipPath, 'Downloading FFmpeg');

            info('Extracting FFmpeg...');
            fs.mkdirSync(ffmpegTempDir, { recursive: true });
            await extractZip(ffmpegZipPath, ffmpegTempDir);

            // Find and copy ffmpeg binaries
            const dirs = fs.readdirSync(ffmpegTempDir);
            const ffmpegDir = dirs.find(d => d.startsWith('ffmpeg'));
            if (ffmpegDir) {
                const binDir = path.join(ffmpegTempDir, ffmpegDir, 'bin');
                if (fs.existsSync(path.join(binDir, 'ffmpeg.exe'))) {
                    fs.copyFileSync(path.join(binDir, 'ffmpeg.exe'), ffmpegPath);
                    fs.copyFileSync(path.join(binDir, 'ffprobe.exe'), ffprobePath);
                    success('FFmpeg installed to tools/bin/');
                }
            }

            // Cleanup
            fs.unlinkSync(ffmpegZipPath);
            fs.rmSync(ffmpegTempDir, { recursive: true, force: true });
        } catch (e) {
            warning(`Could not auto-install FFmpeg: ${e.message}`);
        }
    } else {
        warning('FFmpeg not found. Install with: brew install ffmpeg (Mac) or apt install ffmpeg (Linux)');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 3: Install Python Requirements
    // ═══════════════════════════════════════════════════════════════
    header('Step 3/4: Installing Python Libraries');

    if (pythonCmd) {
        const reqPath = path.join(projectDir, 'requirements.txt');
        if (fs.existsSync(reqPath)) {
            try {
                info('Installing Python requirements...');
                execSync(`"${pythonCmd}" -m pip install -r "${reqPath}"`, { stdio: 'inherit' });
                success('Python requirements installed!');

                // Install Playwright browsers (needed for screenshot tools)
                try {
                    info('Installing Playwright browsers (for screenshots)...');
                    execSync(`"${pythonCmd}" -m playwright install chromium`, { stdio: 'inherit' });
                    success('Playwright browsers installed!');
                } catch (e) {
                    warning('Could not install Playwright browsers');
                    info('Run manually: python -m playwright install chromium');
                }
            } catch (e) {
                warning('Could not install requirements. Try: pip install -r requirements.txt');
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 4: Check/Install AI CLI
    // ═══════════════════════════════════════════════════════════════
    header('Step 4/4: Checking AI CLI');

    // Verify CLI actually works (not just exists in PATH)
    function isCliWorking(cmd) {
        try {
            execSync(`${cmd} --version`, { stdio: 'pipe', timeout: 5000 });
            return true;
        } catch {
            return false;
        }
    }

    const hasGemini = isCliWorking('gemini');
    const hasQwen = isCliWorking('qwen');
    const hasClaude = isCliWorking('claude');
    const hasOpenCode = isCliWorking('opencode');
    const hasAider = isCliWorking('aider');

    let selectedCli = null;

    // Show what's detected
    console.log('Checking installed CLIs...');
    if (hasGemini) { success('  Gemini CLI - Installed'); } else { info('  Gemini CLI - Not found'); }
    if (hasQwen) { success('  Qwen CLI - Installed'); } else { info('  Qwen CLI - Not found'); }
    if (hasClaude) { success('  Claude CLI - Installed'); } else { info('  Claude CLI - Not found'); }
    if (hasOpenCode) { success('  OpenCode CLI - Installed'); } else { info('  OpenCode CLI - Not found'); }
    if (hasAider) { success('  Aider CLI - Installed'); } else { info('  Aider CLI - Not found'); }

    // Always offer installation choice
    console.log('\n📦 Choose AI CLI Tools to install/update:');
    console.log('  1. Claude Code (npm install -g @anthropic-ai/claude-code)');
    console.log('  2. OpenCode CLI (npm install -g opencode-ai)');
    console.log('  3. Gemini CLI (npm install -g @google/gemini-cli)');
    console.log('  4. Qwen CLI (npm install -g @qwen-code/qwen-code)');
    console.log('  5. Aider CLI (pip install aider-chat)');
    console.log('  6. Install ALL tools');
    console.log('  7. Skip / Skip installation');

    const choicesInput = await ask('\nEnter choice(s) comma-separated (e.g. 1,2,5 or 6 for ALL or press Enter to skip): ');
    
    let installAll = false;
    let selectedIndices = [];

    if (choicesInput.trim() === '6') {
        installAll = true;
    } else if (choicesInput.trim() && choicesInput.trim() !== '7') {
        selectedIndices = choicesInput.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n >= 1 && n <= 5);
    }

    if (installAll || selectedIndices.includes(1)) {
        try {
            info('Installing Claude Code globally...');
            execSync('npm install -g @anthropic-ai/claude-code', { stdio: 'inherit' });
            success('Claude Code installed successfully!');
            if (!selectedCli) selectedCli = 'claude';
        } catch (e) {
            error('Failed to install Claude Code.');
        }
    }

    if (installAll || selectedIndices.includes(2)) {
        try {
            info('Installing OpenCode CLI globally...');
            execSync('npm install -g opencode-ai', { stdio: 'inherit' });
            success('OpenCode CLI installed successfully!');
            if (!selectedCli) selectedCli = 'opencode';
        } catch (e) {
            error('Failed to install OpenCode CLI.');
        }
    }

    if (installAll || selectedIndices.includes(3)) {
        try {
            info('Installing Gemini CLI globally...');
            execSync('npm install -g @google/gemini-cli', { stdio: 'inherit' });
            success('Gemini CLI installed successfully!');
            if (!selectedCli) selectedCli = 'gemini';
        } catch (e) {
            error('Failed to install Gemini CLI.');
        }
    }

    if (installAll || selectedIndices.includes(4)) {
        try {
            info('Installing Qwen CLI globally...');
            execSync('npm install -g @qwen-code/qwen-code', { stdio: 'inherit' });
            success('Qwen CLI installed successfully!');
            if (!selectedCli) selectedCli = 'qwen';
        } catch (e) {
            error('Failed to install Qwen CLI.');
        }
    }

    if (installAll || selectedIndices.includes(5)) {
        if (pythonCmd) {
            try {
                info('Installing Aider CLI via pip...');
                execSync(`"${pythonCmd}" -m pip install aider-chat`, { stdio: 'inherit' });
                success('Aider CLI installed successfully!');
                if (!selectedCli) selectedCli = 'aider';
            } catch (e) {
                error('Failed to install Aider CLI.');
            }
        } else {
            warning('Aider CLI installation skipped (Python not available).');
        }
    }

    // Determine fallback selectedCli if none was newly installed
    if (!selectedCli) {
        if (isCliWorking('gemini')) selectedCli = 'gemini';
        else if (isCliWorking('claude')) selectedCli = 'claude';
        else if (isCliWorking('opencode')) selectedCli = 'opencode';
        else if (isCliWorking('qwen')) selectedCli = 'qwen';
        else if (isCliWorking('aider')) selectedCli = 'aider';
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 5: Create Launcher Script
    // ═══════════════════════════════════════════════════════════════
    header('Creating Launcher Script');

    const targetDir = fs.existsSync(path.join(projectDir, '..', '_video_nut')) ? path.join(projectDir, '..') : projectDir;
    const videoNutDir = fs.existsSync(path.join(projectDir, '..', '_video_nut')) ? path.join(projectDir, '..', '_video_nut') : projectDir;
    const localPythonPath = path.join(videoNutDir, 'python');
    const localToolsPath = path.join(videoNutDir, 'tools', 'bin');

    const launchScriptContent = isWindows
        ? `@echo off
REM Add local Python, FFmpeg, and AppData NPM prefix to PATH for this session
set PATH=${localPythonPath};${localPythonPath}\\Scripts;${localToolsPath};%APPDATA%\\npm;%PATH%

:menu
cls
echo ====================================================
echo                 🎬 VideoNut Launcher 🎬
echo ====================================================
echo  Python Path: ${localPythonPath}
echo  FFmpeg Path: ${localToolsPath}
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
python "${videoNutDir.replace(/\\/g, '/')}/tools/check_env.py"
pause
goto menu

:run_setup
echo Launching Setup Script...
node "${videoNutDir.replace(/\\/g, '/')}/setup.js"
pause
goto menu

:end
echo Thank you for using VideoNut!
exit /b
`
        : `#!/bin/bash
# Add local Python, FFmpeg, and global npm bin path to PATH
export PATH="${localPythonPath}:${localPythonPath}/bin:${localToolsPath}:$(npm config get prefix 2>/dev/null)/bin:$PATH"

show_menu() {
    clear
    echo "===================================================="
    echo "                 🎬 VideoNut Launcher 🎬"
    echo "===================================================="
    echo "  Python Path: ${localPythonPath}"
    echo "  FFmpeg Path: ${localToolsPath}"
    echo "===================================================="
    echo ""
    echo "  Choose an AI CLI tool or utility to run:"
    echo ""
    echo "   [1] Google Gemini CLI"
    echo "   [2] Anthropic Claude Code"
    echo "   [3] OpenCode CLI"
    echo "   [4] Alibaba Qwen CLI"
    echo "   [5] Aider CLI"
    echo "   [6] Run Environment Check"
    echo "   [7] Run Package Setup / CLI Installer"
    echo "   [8] Exit"
    echo ""
    echo "===================================================="
    read -p "Enter option (1-8): " choice

    case $choice in
        1)
            if ! command -v gemini &> /dev/null; then
                echo "Gemini CLI is not installed."
                read -p "Would you like to install it now? (y/n): " inst
                if [[ $inst == "y" || $inst == "Y" ]]; then
                    npm install -g @google/gemini-cli
                else
                    read -p "Press Enter to return..."
                    show_menu
                    return
                fi
            fi
            gemini
            read -p "Press Enter to return..."
            show_menu
            ;;
        2)
            if ! command -v claude &> /dev/null; then
                echo "Claude Code is not installed."
                read -p "Would you like to install it now? (y/n): " inst
                if [[ $inst == "y" || $inst == "Y" ]]; then
                    npm install -g @anthropic-ai/claude-code
                else
                    read -p "Press Enter to return..."
                    show_menu
                    return
                fi
            fi
            claude
            read -p "Press Enter to return..."
            show_menu
            ;;
        3)
            if ! command -v opencode &> /dev/null; then
                echo "OpenCode CLI is not installed."
                read -p "Would you like to install it now? (y/n): " inst
                if [[ $inst == "y" || $inst == "Y" ]]; then
                    npm install -g opencode-ai
                else
                    read -p "Press Enter to return..."
                    show_menu
                    return
                fi
            fi
            opencode
            read -p "Press Enter to return..."
            show_menu
            ;;
        4)
            if ! command -v qwen &> /dev/null; then
                echo "Qwen CLI is not installed."
                read -p "Would you like to install it now? (y/n): " inst
                if [[ $inst == "y" || $inst == "Y" ]]; then
                    npm install -g @qwen-code/qwen-code
                else
                    read -p "Press Enter to return..."
                    show_menu
                    return
                fi
            fi
            qwen
            read -p "Press Enter to return..."
            show_menu
            ;;
        5)
            if ! command -v aider &> /dev/null; then
                echo "Aider CLI is not installed."
                read -p "Would you like to install it now? (y/n): " inst
                if [[ $inst == "y" || $inst == "Y" ]]; then
                    python3 -m pip install aider-chat
                else
                    read -p "Press Enter to return..."
                    show_menu
                    return
                fi
            fi
            aider
            read -p "Press Enter to return..."
            show_menu
            ;;
        6)
            python3 "${videoNutDir}/tools/check_env.py"
            read -p "Press Enter to return..."
            show_menu
            ;;
        7)
            node "${videoNutDir}/setup.js"
            read -p "Press Enter to return..."
            show_menu
            ;;
        8)
            echo "Thank you for using VideoNut!"
            exit 0
            ;;
        *)
            show_menu
            ;;
    esac
}

show_menu
`;

    const launchScriptPath = path.join(targetDir, isWindows ? 'start_videonut.bat' : 'start_videonut.sh');
    fs.writeFileSync(launchScriptPath, launchScriptContent);
    if (!isWindows) {
        execSync(`chmod +x "${launchScriptPath}"`);
    }
    success(`Created launch script: ${path.basename(launchScriptPath)}`);

    // ═══════════════════════════════════════════════════════════════
    // DONE!
    // ═══════════════════════════════════════════════════════════════
    header('🎉 Setup Complete!');

    console.log('📁 Your project is ready:');
    console.log(`   ${targetDir}/`);
    console.log('   ├── agents/         (AI agent prompts)');
    console.log('   ├── tools/          (downloaders, validators)');
    console.log('   ├── .gemini/        (CLI commands)');
    console.log('   └── Projects/       (create this for your work)');

    console.log('\n🚀 Quick Start:');
    if (selectedCli) {
        console.log(`   1. Run: ${isWindows ? 'start_videonut.bat' : './start_videonut.sh'}`);
        console.log('   2. Choose your preferred CLI and start using the agents!');
    } else {
        console.log('   1. Run the launcher script to configure and launch.');
    }

    console.log('\n' + '═'.repeat(60));
    log('🎬 Happy Documentary Making!', 'bright');
    console.log('═'.repeat(60) + '\n');
}

main().catch(console.error);
