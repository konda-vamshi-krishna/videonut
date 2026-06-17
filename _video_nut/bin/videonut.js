#!/usr/bin/env node

/**
 * VideoNut - Complete Installation Script
 * 
 * This script installs VideoNut and ALL its requirements:
 * 1. Copies all VideoNut files to current directory
 * 2. Creates Projects folder
 * 3. Downloads & installs Python (if needed) - to _video_nut/python/
 * 4. Downloads FFmpeg & FFprobe - to _video_nut/tools/bin/
 * 5. Runs pip install -r requirements.txt
 * 6. Installs Gemini CLI (or user's choice) globally
 * 7. Launches the CLI tool
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const https = require('https');
const http = require('http');
const readline = require('readline');
const { createWriteStream, mkdirSync, existsSync } = require('fs');

// Colors for console
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
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

// Check if command exists
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

// Get user input
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

// Download file with progress
function downloadFile(url, dest, description = 'Downloading') {
    return new Promise((resolve, reject) => {
        const protocol = url.startsWith('https') ? https : http;

        const request = (currentUrl) => {
            protocol.get(currentUrl, response => {
                // Handle redirects
                if (response.statusCode === 302 || response.statusCode === 301) {
                    request(response.headers.location);
                    return;
                }

                if (response.statusCode !== 200) {
                    reject(new Error(`Failed to download: ${response.statusCode}`));
                    return;
                }

                const totalSize = parseInt(response.headers['content-length'], 10);
                let downloadedSize = 0;

                const file = createWriteStream(dest);

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
                    console.log(''); // New line after progress
                    resolve();
                });

                file.on('error', err => {
                    fs.unlink(dest, () => { });
                    reject(err);
                });
            }).on('error', reject);
        };

        request(url);
    });
}

// Extract zip file
async function extractZip(zipPath, destDir) {
    const isWindows = process.platform === 'win32';

    if (isWindows) {
        // Use PowerShell to extract
        try {
            execSync(`powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`, { stdio: 'pipe' });
        } catch (e) {
            throw new Error(`Failed to extract zip: ${e.message}`);
        }
    } else {
        // Use unzip command on Unix
        try {
            execSync(`unzip -o "${zipPath}" -d "${destDir}"`, { stdio: 'pipe' });
        } catch (e) {
            throw new Error(`Failed to extract zip: ${e.message}`);
        }
    }
}

// Copy directory recursively
function copyDir(src, dest) {
    mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            // Skip certain directories
            if (['node_modules', '.git', 'Projects', 'output', 'assets', '__pycache__'].includes(entry.name)) {
                continue;
            }
            // Skip tools/bin (we'll download fresh ffmpeg)
            if (entry.name === 'bin' && srcPath.includes('tools')) {
                continue;
            }
            copyDir(srcPath, destPath);
        } else {
            // Skip compiled python files
            if (entry.name.endsWith('.pyc')) continue;
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];

    header('VideoNut - AI-Powered Documentary Pipeline');
    console.log('Complete Installation - Everything You Need!\n');

    if (command === 'init') {
        await runInit();
    } else {
        showHelp();
    }
}

async function runInit() {
    const targetDir = process.cwd();
    const isWindows = process.platform === 'win32';

    info(`Installing VideoNut in: ${targetDir}\n`);

    // ═══════════════════════════════════════════════════════════════
    // STEP 1: Copy VideoNut Files
    // ═══════════════════════════════════════════════════════════════
    header('Step 1/6: Copying VideoNut Files');

    const packageRoot = path.join(__dirname, '..');

    // Copy CLI command folders to target root
    const cliFolders = ['.gemini', '.qwen', '.claude', '.opencode', '.antigravity'];
    for (const folder of cliFolders) {
        const src = path.join(packageRoot, folder);
        const dest = path.join(targetDir, folder);

        if (existsSync(src)) {
            copyDir(src, dest);
            success(`Copied ${folder}/`);
        }
    }

    // Copy IDE configuration/rules files to target root
    const rootFiles = ['.cursorrules', '.clinerules', '.aider.conf.yml', 'CONVENTIONS.md', 'README_AGENTS.md'];
    for (const file of rootFiles) {
        const src = path.join(packageRoot, file);
        const dest = path.join(targetDir, file);

        if (existsSync(src)) {
            fs.copyFileSync(src, dest);
            success(`Copied ${file} to project root`);
        }
    }

    // Create _video_nut folder structure
    const videoNutDir = path.join(targetDir, '_video_nut');
    mkdirSync(videoNutDir, { recursive: true });

    // Copy content folders
    const contentFolders = ['agents', 'tools', 'workflows', 'docs', 'memory', 'scripts'];
    for (const folder of contentFolders) {
        const src = path.join(packageRoot, folder);
        const dest = path.join(videoNutDir, folder);
        if (existsSync(src)) {
            copyDir(src, dest);
        }
    }

    // Copy individual files
    const files = ['config.yaml', 'requirements.txt', 'workflow_orchestrator.py', 'file_validator.py', 'README.md', 'USER_GUIDE.md'];
    for (const file of files) {
        const src = path.join(packageRoot, file);
        const dest = path.join(videoNutDir, file);
        if (existsSync(src)) {
            fs.copyFileSync(src, dest);
        }
    }
    success('Copied _video_nut/ (agents, tools, workflows)');

    // Create Projects folder
    const projectsDir = path.join(targetDir, 'Projects');
    mkdirSync(projectsDir, { recursive: true });
    success('Created Projects/ folder');

    // Create necessary subdirectories
    const toolsBinDir = path.join(videoNutDir, 'tools', 'bin');
    mkdirSync(toolsBinDir, { recursive: true });

    // ═══════════════════════════════════════════════════════════════
    // STEP 2: Install/Download Python
    // ═══════════════════════════════════════════════════════════════
    header('Step 2/6: Setting Up Python');

    let pythonCmd = null;
    const localPythonDir = path.join(videoNutDir, 'python');
    const localPythonExe = isWindows
        ? path.join(localPythonDir, 'python.exe')
        : path.join(localPythonDir, 'bin', 'python3');

    // Check for system Python first (must actually work, not just exist)
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
        success('Found system Python3');
    } else if (isPythonWorking('python')) {
        pythonCmd = 'python';
        success('Found system Python');
    } else {
        info('No working Python found on system');
    }

    // If no Python found, download it (Windows only for now)
    if (!pythonCmd && isWindows) {
        info('Python not found. Downloading Python...');

        const pythonVersion = '3.12.1';
        const pythonZipUrl = `https://www.python.org/ftp/python/${pythonVersion}/python-${pythonVersion}-embed-amd64.zip`;
        const pythonZipPath = path.join(videoNutDir, 'python.zip');

        try {
            mkdirSync(localPythonDir, { recursive: true });

            await downloadFile(pythonZipUrl, pythonZipPath, 'Downloading Python');

            info('Extracting Python...');
            await extractZip(pythonZipPath, localPythonDir);

            // Clean up zip
            fs.unlinkSync(pythonZipPath);

            // Download get-pip.py
            const getPipUrl = 'https://bootstrap.pypa.io/get-pip.py';
            const getPipPath = path.join(localPythonDir, 'get-pip.py');
            await downloadFile(getPipUrl, getPipPath, 'Downloading pip installer');

            // Enable pip in embedded Python by modifying python312._pth
            const pthFile = path.join(localPythonDir, `python312._pth`);
            if (existsSync(pthFile)) {
                let content = fs.readFileSync(pthFile, 'utf8');
                content = content.replace('#import site', 'import site');
                fs.writeFileSync(pthFile, content);
            }

            // Install pip
            info('Installing pip...');
            execSync(`"${path.join(localPythonDir, 'python.exe')}" "${getPipPath}"`, {
                stdio: 'inherit',
                cwd: localPythonDir
            });

            pythonCmd = path.join(localPythonDir, 'python.exe');
            success(`Python installed to: ${localPythonDir}`);

        } catch (e) {
            warning(`Could not auto-install Python: ${e.message}`);
            console.log('\nPlease install Python manually:');
            console.log('  https://www.python.org/downloads/');
        }
    } else if (!pythonCmd) {
        warning('Python not found!');
        console.log('\nPlease install Python:');
        console.log('  Mac: brew install python3');
        console.log('  Linux: sudo apt install python3 python3-pip');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 3: Download FFmpeg
    // ═══════════════════════════════════════════════════════════════
    header('Step 3/6: Setting Up FFmpeg');

    const ffmpegPath = path.join(toolsBinDir, isWindows ? 'ffmpeg.exe' : 'ffmpeg');
    const ffprobePath = path.join(toolsBinDir, isWindows ? 'ffprobe.exe' : 'ffprobe');

    if (existsSync(ffmpegPath) && existsSync(ffprobePath)) {
        success('FFmpeg already exists in tools/bin/');
    } else if (commandExists('ffmpeg') && commandExists('ffprobe')) {
        success('FFmpeg found in system PATH');
    } else if (isWindows) {
        info('Downloading FFmpeg...');

        // Using BtbN builds (more reliable)
        const ffmpegUrl = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip';
        const ffmpegZipPath = path.join(videoNutDir, 'ffmpeg.zip');
        const ffmpegExtractDir = path.join(videoNutDir, 'ffmpeg_temp');

        try {
            await downloadFile(ffmpegUrl, ffmpegZipPath, 'Downloading FFmpeg');

            info('Extracting FFmpeg...');
            mkdirSync(ffmpegExtractDir, { recursive: true });
            await extractZip(ffmpegZipPath, ffmpegExtractDir);

            // Find the bin folder inside extracted directory
            const extractedDirs = fs.readdirSync(ffmpegExtractDir);
            const ffmpegDir = extractedDirs.find(d => d.startsWith('ffmpeg'));

            if (ffmpegDir) {
                const binDir = path.join(ffmpegExtractDir, ffmpegDir, 'bin');

                // Copy ffmpeg and ffprobe
                if (existsSync(path.join(binDir, 'ffmpeg.exe'))) {
                    fs.copyFileSync(path.join(binDir, 'ffmpeg.exe'), ffmpegPath);
                    fs.copyFileSync(path.join(binDir, 'ffprobe.exe'), ffprobePath);
                    success(`FFmpeg installed to: ${toolsBinDir}`);
                }
            }

            // Clean up
            fs.unlinkSync(ffmpegZipPath);
            fs.rmSync(ffmpegExtractDir, { recursive: true, force: true });

        } catch (e) {
            warning(`Could not auto-install FFmpeg: ${e.message}`);
            console.log('\nPlease download manually:');
            console.log('  https://www.gyan.dev/ffmpeg/builds/');
            console.log(`  Extract ffmpeg.exe and ffprobe.exe to: ${toolsBinDir}`);
        }
    } else {
        warning('FFmpeg not found!');
        console.log('\nPlease install FFmpeg:');
        console.log('  Mac: brew install ffmpeg');
        console.log('  Linux: sudo apt install ffmpeg');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 4: Install Python Requirements
    // ═══════════════════════════════════════════════════════════════
    header('Step 4/6: Installing Python Libraries');

    if (pythonCmd) {
        const reqPath = path.join(videoNutDir, 'requirements.txt');

        if (existsSync(reqPath)) {
            try {
                info('Installing Python requirements...');
                execSync(`"${pythonCmd}" -m pip install -r "${reqPath}"`, {
                    stdio: 'inherit'
                });
                success('Python requirements installed');

                // Install Playwright browsers (needed for screenshot tools)
                try {
                    info('Installing Playwright browsers (for screenshots)...');
                    execSync(`"${pythonCmd}" -m playwright install chromium`, {
                        stdio: 'inherit'
                    });
                    success('Playwright browsers installed');
                } catch (e) {
                    warning('Could not install Playwright browsers');
                    info('Run manually: python -m playwright install chromium');
                }
            } catch (e) {
                warning('Could not install Python requirements automatically');
                info(`Please run: ${pythonCmd} -m pip install -r ${reqPath}`);
            }
        }
    } else {
        warning('Skipped - Python not available');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 5: Install AI CLI Tool
    // ═══════════════════════════════════════════════════════════════
    header('Step 5/6: Setting Up AI CLI');

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
    // STEP 6: Final Setup & Launch
    // ═══════════════════════════════════════════════════════════════
    header('Step 6/6: Final Setup');

    // Create paths for local tools
    const localPythonPath = path.join(videoNutDir, 'python');
    const localToolsPath = path.join(videoNutDir, 'tools', 'bin');

    // Create a launcher script (start_videonut.bat) with interactive tool selection and auto-installation
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
            python3 "\${videoNutDir}/tools/check_env.py"
            read -p "Press Enter to return..."
            show_menu
            ;;
        7)
            node "\${videoNutDir}/setup.js"
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
    info('Use this script to start with Python & FFmpeg in PATH!');

    // ═══════════════════════════════════════════════════════════════
    // INSTALLATION COMPLETE!
    // ═══════════════════════════════════════════════════════════════
    header('🎉 Installation Complete!');

    console.log('📁 Folder Structure:');
    console.log(`   ${targetDir}/`);
    console.log('   ├── _video_nut/');
    console.log('   │   ├── agents/        (AI agent prompts)');
    console.log('   │   ├── tools/');
    console.log('   │   │   └── bin/       (ffmpeg, ffprobe)');
    console.log('   │   ├── python/        (embedded Python)');
    console.log('   │   └── workflows/     (workflow definitions)');
    console.log('   ├── .gemini/           (Gemini CLI commands)');
    console.log('   ├── .qwen/             (Qwen CLI commands)');
    console.log('   ├── .claude/           (Claude CLI commands)');
    console.log('   └── Projects/          (your video projects)');

    console.log('\n🚀 Quick Start:');
    if (selectedCli) {
        console.log(`   1. Run: ${selectedCli}`);
        console.log('   2. Type: /topic_scout');
        console.log('   3. Follow the agent pipeline!');
    } else {
        console.log('   1. Install your preferred AI CLI');
        console.log('   2. Open the CLI in this folder');
        console.log('   3. Type: /topic_scout');
    }

    console.log('\n📖 Documentation:');
    console.log('   https://github.com/konda-vamshi-krishna/videonut');

    // Ask to launch CLI
    if (selectedCli) {
        console.log('');
        const launch = await ask(`\n🚀 Launch ${selectedCli} now? [Y/n]: `);

        if (launch.toLowerCase() !== 'n') {
            console.log(`\nStarting ${selectedCli}...\n`);

            // Spawn the CLI
            const cli = spawn(selectedCli, [], {
                stdio: 'inherit',
                shell: true,
                cwd: targetDir
            });

            cli.on('close', () => {
                console.log('\n👋 Thanks for using VideoNut!');
            });
        }
    }

    console.log('\n' + '═'.repeat(60));
    log('🎬 Happy Documentary Making!', 'bright');
    console.log('═'.repeat(60) + '\n');
}

function showHelp() {
    console.log('Usage: npx videonut <command>\n');
    console.log('Commands:');
    console.log('  init    Install VideoNut with ALL dependencies\n');
    console.log('This will automatically install:');
    console.log('  ✓ VideoNut agents and tools');
    console.log('  ✓ Python (if not installed)');
    console.log('  ✓ FFmpeg & FFprobe');
    console.log('  ✓ Python libraries (yt-dlp, etc.)');
    console.log('  ✓ Gemini CLI (or your choice)');
    console.log('');
    console.log('Example:');
    console.log('  mkdir my-youtube-project');
    console.log('  cd my-youtube-project');
    console.log('  npx videonut init');
    console.log('');
}

main().catch(console.error);
