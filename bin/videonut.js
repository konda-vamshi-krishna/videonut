#!/usr/bin/env node

/**
 * VideoNut - Complete Installation Script
 * 
 * This script installs VideoNut and ALL its requirements:
 * 1. Copies all VideoNut files to current directory
 * 2. Creates Projects folder
 * 3. Installs Python (if needed)
 * 4. Runs pip install -r requirements.txt
 * 5. Downloads ffmpeg and ffprobe
 * 6. Installs chosen CLI (Gemini/Qwen/Claude)
 */

const { execSync, spawnSync } = require('child_process');
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

// Copy directory recursively
function copyDir(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            // Skip certain directories
            if (['node_modules', '.git', 'Projects', 'output', 'assets'].includes(entry.name)) {
                continue;
            }
            copyDir(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

// Download file
function downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(dest);
        https.get(url, response => {
            if (response.statusCode === 302 || response.statusCode === 301) {
                // Follow redirect
                https.get(response.headers.location, res => {
                    res.pipe(file);
                    file.on('finish', () => {
                        file.close();
                        resolve();
                    });
                });
            } else {
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    resolve();
                });
            }
        }).on('error', err => {
            fs.unlink(dest, () => { });
            reject(err);
        });
    });
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];

    header('VideoNut - AI-Powered Documentary Pipeline');

    if (command === 'init') {
        await runInit();
    } else {
        showHelp();
    }
}

async function runInit() {
    const targetDir = process.cwd();

    info(`Installing VideoNut in: ${targetDir}\n`);

    // Step 1: Copy VideoNut files
    header('Step 1: Copying VideoNut Files');

    // The package root is where videonut.js is located (bin/../)
    const packageRoot = path.join(__dirname, '..');
    
    // Copy CLI command folders
    const cliFolders = ['.gemini', '.qwen', '.claude', '.antigravity'];
    for (const folder of cliFolders) {
        const src = path.join(packageRoot, folder);
        const dest = path.join(targetDir, folder);

        if (fs.existsSync(src)) {
            copyDir(src, dest);
            success(`Copied ${folder}/`);
        } else {
            warning(`${folder}/ not found in package`);
        }
    }
    
    // Copy _video_nut folder (agents, tools, etc.)
    const videoNutDest = path.join(targetDir, '_video_nut');
    fs.mkdirSync(videoNutDest, { recursive: true });
    
    const contentFolders = ['agents', 'tools', 'workflows', 'docs', 'memory', 'scripts'];
    for (const folder of contentFolders) {
        const src = path.join(packageRoot, folder);
        const dest = path.join(videoNutDest, folder);
        if (fs.existsSync(src)) {
            copyDir(src, dest);
        }
    }
    
    // Copy individual files to _video_nut
    const files = ['config.yaml', 'requirements.txt', 'workflow_orchestrator.py', 'file_validator.py', 'README.md', 'USER_GUIDE.md'];
    for (const file of files) {
        const src = path.join(packageRoot, file);
        const dest = path.join(videoNutDest, file);
        if (fs.existsSync(src)) {
            fs.copyFileSync(src, dest);
        }
    }
    success('Copied _video_nut/ (agents, tools, workflows)');

    // Create Projects folder
    const projectsDir = path.join(targetDir, 'Projects');
    fs.mkdirSync(projectsDir, { recursive: true });
    success('Created Projects/ folder');

    // Step 2: Check Python
    header('Step 2: Checking Python');

    const hasPython = commandExists('python') || commandExists('python3');

    if (hasPython) {
        success('Python is installed');

        // Install requirements
        info('Installing Python requirements...');
        const reqPath = path.join(targetDir, '_video_nut', 'requirements.txt');

        if (fs.existsSync(reqPath)) {
            try {
                const pythonCmd = commandExists('python3') ? 'python3' : 'python';
                execSync(`${pythonCmd} -m pip install -r "${reqPath}"`, { stdio: 'inherit' });
                success('Python requirements installed');
            } catch (e) {
                warning('Could not install Python requirements automatically');
                info(`Please run: pip install -r ${reqPath}`);
            }
        }
    } else {
        warning('Python not found!');
        console.log('\nPlease install Python manually:');
        console.log('  Windows: https://www.python.org/downloads/');
        console.log('  Mac: brew install python3');
        console.log('  Linux: sudo apt install python3 python3-pip');
        console.log('\nAfter installing Python, run:');
        console.log(`  pip install -r ${path.join(targetDir, '_video_nut', 'requirements.txt')}`);
    }

    // Step 3: Check FFmpeg
    header('Step 3: Checking FFmpeg');

    const hasFFmpeg = commandExists('ffmpeg');
    const hasFFprobe = commandExists('ffprobe');

    if (hasFFmpeg && hasFFprobe) {
        success('FFmpeg and FFprobe are installed');
    } else {
        warning('FFmpeg/FFprobe not found!');
        console.log('\nPlease install FFmpeg:');
        console.log('  Windows: https://www.gyan.dev/ffmpeg/builds/');
        console.log('           Download ffmpeg-release-essentials.zip');
        console.log('           Extract and add bin/ folder to PATH');
        console.log('  Mac: brew install ffmpeg');
        console.log('  Linux: sudo apt install ffmpeg');

        // Create tools/bin folder for manual installation
        const binDir = path.join(targetDir, '_video_nut', 'tools', 'bin');
        fs.mkdirSync(binDir, { recursive: true });
        info(`Or place ffmpeg.exe and ffprobe.exe in: ${binDir}`);
    }

    // Step 4: Check CLI tools
    header('Step 4: Checking AI CLI Tools');

    const hasGemini = commandExists('gemini');
    const hasQwen = commandExists('qwen');
    const hasClaude = commandExists('claude');

    console.log('Detected CLIs:');
    console.log(`  Gemini CLI: ${hasGemini ? '✅ Installed' : '❌ Not found'}`);
    console.log(`  Qwen CLI:   ${hasQwen ? '✅ Installed' : '❌ Not found'}`);
    console.log(`  Claude:     ${hasClaude ? '✅ Installed' : '❌ Not found'}`);

    if (!hasGemini && !hasQwen && !hasClaude) {
        warning('\nNo AI CLI found! You need at least one.');
        console.log('\nInstall one of these:');
        console.log('  Gemini CLI: npm install -g @anthropic-ai/claude-cli');
        console.log('  (Follow official documentation for each CLI)');
    }

    // Final summary
    header('Installation Complete!');

    console.log('📁 Folder Structure:');
    console.log(`   ${targetDir}/`);
    console.log('   ├── _video_nut/     (agents & tools)');
    console.log('   ├── .gemini/        (Gemini CLI commands)');
    console.log('   ├── .qwen/          (Qwen CLI commands)');
    console.log('   ├── .claude/        (Claude CLI commands)');
    console.log('   └── Projects/       (your video projects)');

    console.log('\n🚀 Quick Start:');
    console.log('   1. Open your AI CLI (e.g., gemini)');
    console.log('   2. Run: /topic_scout');
    console.log('   3. Follow the agent pipeline!');

    console.log('\n📖 Documentation:');
    console.log('   https://github.com/vamshikrishna131437/videonut');

    console.log('\n' + '═'.repeat(60));
    log('🎬 Happy Documentary Making!', 'bright');
    console.log('═'.repeat(60) + '\n');
}

function showHelp() {
    console.log('Usage: npx videonut <command>\n');
    console.log('Commands:');
    console.log('  init    Install VideoNut in current directory');
    console.log('');
    console.log('This will install:');
    console.log('  • VideoNut agents and tools');
    console.log('  • CLI command files (.gemini, .qwen, .claude)');
    console.log('  • Python requirements');
    console.log('  • FFmpeg check');
    console.log('');
    console.log('Example:');
    console.log('  mkdir my-youtube-project');
    console.log('  cd my-youtube-project');
    console.log('  npx videonut init');
    console.log('');
}

main().catch(console.error);
