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
    const cliFolders = ['.gemini', '.qwen', '.claude', '.antigravity'];
    for (const folder of cliFolders) {
        const src = path.join(packageRoot, folder);
        const dest = path.join(targetDir, folder);

        if (existsSync(src)) {
            copyDir(src, dest);
            success(`Copied ${folder}/`);
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
            execSync(`${cmd} --version`, { stdio: 'pipe', timeout: 10000 });
            return true;
        } catch {
            return false;
        }
    }

    const hasGemini = isCliWorking('gemini');
    const hasQwen = isCliWorking('qwen');
    const hasClaude = isCliWorking('claude');

    let selectedCli = null;

    // Show what's detected
    console.log('Checking installed CLIs...');
    if (hasGemini) { success('  Gemini CLI - Installed'); }
    if (hasQwen) { success('  Qwen CLI - Installed'); }
    if (hasClaude) { success('  Claude CLI - Installed'); }
    if (!hasGemini && !hasQwen && !hasClaude) {
        info('  No AI CLI currently installed');
    }

    // Always offer installation choice
    console.log('\n📦 CLI Installation:');
    console.log('  1. Install BOTH Gemini + Qwen (⭐ RECOMMENDED)');
    console.log('     → Gemini: Best for content writing & creativity');
    console.log('     → Qwen: Best for instruction following & agent tasks');
    console.log('  2. Install Gemini CLI only (by Google)');
    console.log('  3. Install Qwen CLI only (by Alibaba)');
    if (hasGemini || hasQwen || hasClaude) {
        console.log('  4. Skip - Use existing CLI\n');
    } else {
        console.log('  4. Skip - I will install manually\n');
    }

    const choice = await ask('Enter choice [1 for BOTH]: ');

    if (choice === '2') {
        // Install Gemini CLI only
        try {
            info('Installing Gemini CLI globally...');
            execSync('npm install -g @google/gemini-cli', { stdio: 'inherit' });
            success('Gemini CLI installed successfully!');
            info('Run "gemini" to start - Best for content writing');
            selectedCli = 'gemini';
        } catch (e) {
            error('Failed to install Gemini CLI');
            info('Please install manually: npm install -g @google/gemini-cli');
        }
    } else if (choice === '3') {
        // Install Qwen CLI only
        try {
            info('Installing Qwen CLI globally...');
            execSync('npm install -g @qwen-code/qwen-code', { stdio: 'inherit' });
            success('Qwen CLI installed successfully!');
            info('Run "qwen" to start - Best for instruction following');
            selectedCli = 'qwen';
        } catch (e) {
            error('Failed to install Qwen CLI');
            info('Please install manually: npm install -g @qwen-code/qwen-code');
        }
    } else if (choice === '4') {
        // Skip - use existing or none
        if (hasGemini) selectedCli = 'gemini';
        else if (hasQwen) selectedCli = 'qwen';
        else if (hasClaude) selectedCli = 'claude';
        info('Skipped CLI installation');
    } else {
        // Install BOTH Gemini + Qwen (default for choice 1 or empty)
        info('Installing BOTH Gemini CLI and Qwen CLI...\n');

        // Install Gemini
        try {
            info('Installing Gemini CLI globally...');
            execSync('npm install -g @google/gemini-cli', { stdio: 'inherit' });
            success('Gemini CLI installed! (Best for content writing)');
        } catch (e) {
            warning('Could not install Gemini CLI');
        }

        // Install Qwen
        try {
            info('Installing Qwen CLI globally...');
            execSync('npm install -g @qwen-code/qwen-code', { stdio: 'inherit' });
            success('Qwen CLI installed! (Best for instruction following)');
        } catch (e) {
            warning('Could not install Qwen CLI');
        }

        selectedCli = 'gemini'; // Default to Gemini for launch
        console.log('\n✅ Both CLIs installed!');
        console.log('   Use "gemini" for creative content');
        console.log('   Use "qwen" for agent/instruction tasks');
    }

    // ═══════════════════════════════════════════════════════════════
    // STEP 6: Final Setup & Launch
    // ═══════════════════════════════════════════════════════════════
    header('Step 6/6: Final Setup');

    // Create paths for local tools
    const localPythonPath = path.join(videoNutDir, 'python');
    const localToolsPath = path.join(videoNutDir, 'tools', 'bin');

    // Create a launch script that adds local Python and FFmpeg to PATH
    const launchScriptContent = isWindows
        ? `@echo off
REM Add local Python and FFmpeg to PATH for this session
set PATH=${localPythonPath};${localPythonPath}\\Scripts;${localToolsPath};%PATH%

echo.
echo ====================================
echo   VideoNut Environment Ready!
echo   Python: ${localPythonPath}
echo   FFmpeg: ${localToolsPath}
echo ====================================
echo.
echo Starting ${selectedCli || 'your CLI'}...
${selectedCli || 'gemini'}
`
        : `#!/bin/bash
# Add local Python and FFmpeg to PATH for this session
export PATH="${localPythonPath}:${localPythonPath}/bin:${localToolsPath}:$PATH"

echo ""
echo "===================================="
echo "  VideoNut Environment Ready!"
echo "  Python: ${localPythonPath}"
echo "  FFmpeg: ${localToolsPath}"
echo "===================================="
echo ""
echo "Starting ${selectedCli || 'your CLI'}..."
${selectedCli || 'gemini'}
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
