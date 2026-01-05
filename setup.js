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

    if (commandExists('python3')) {
        pythonCmd = 'python3';
        success('Found Python3');
    } else if (commandExists('python')) {
        pythonCmd = 'python';
        success('Found Python');
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

    const hasGemini = commandExists('gemini');
    const hasQwen = commandExists('qwen');
    const hasClaude = commandExists('claude');

    if (hasGemini || hasQwen || hasClaude) {
        if (hasGemini) success('Gemini CLI found');
        if (hasQwen) success('Qwen CLI found');
        if (hasClaude) success('Claude CLI found');
    } else {
        warning('No AI CLI found.');
        console.log('\nWhich CLI would you like to install?');
        console.log('  1. Gemini CLI (recommended - by Google)');
        console.log('  2. Claude CLI (by Anthropic)');
        console.log('  3. Qwen CLI (by Alibaba)');
        console.log('  4. Skip - I will install manually\n');

        const answer = await ask('Enter choice [1]: ');

        if (answer === '2') {
            try {
                info('Installing Claude CLI globally...');
                execSync('npm install -g @anthropic-ai/claude-code', { stdio: 'inherit' });
                success('Claude CLI installed! Run "claude" to start.');
            } catch (e) {
                warning('Could not install CLI.');
                info('Install manually: npm install -g @anthropic-ai/claude-code');
            }
        } else if (answer === '3') {
            try {
                info('Installing Qwen CLI globally...');
                execSync('npm install -g @qwen-code/qwen-code', { stdio: 'inherit' });
                success('Qwen CLI installed! Run "qwen" to start.');
            } catch (e) {
                warning('Could not install CLI.');
                info('Install manually: npm install -g @qwen-code/qwen-code');
            }
        } else if (answer !== '4') {
            try {
                info('Installing Gemini CLI globally...');
                execSync('npm install -g @google/gemini-cli', { stdio: 'inherit' });
                success('Gemini CLI installed! Run "gemini" to start.');
            } catch (e) {
                warning('Could not install CLI.');
                info('Install manually: npm install -g @google/gemini-cli');
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // DONE!
    // ═══════════════════════════════════════════════════════════════
    header('🎉 Setup Complete!');

    console.log('📁 Your project is ready:');
    console.log(`   ${projectDir}/`);
    console.log('   ├── agents/         (AI agent prompts)');
    console.log('   ├── tools/          (downloaders, validators)');
    console.log('   ├── .gemini/        (CLI commands)');
    console.log('   └── Projects/       (create this for your work)');

    console.log('\n🚀 Quick Start:');
    console.log('   1. Run: gemini (or your preferred CLI)');
    console.log('   2. Type: /topic_scout');
    console.log('   3. Follow the agent pipeline!');

    console.log('\n' + '═'.repeat(60));
    log('🎬 Happy Documentary Making!', 'bright');
    console.log('═'.repeat(60) + '\n');
}

main().catch(console.error);
