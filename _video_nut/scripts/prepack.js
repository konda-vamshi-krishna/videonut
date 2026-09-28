#!/usr/bin/env node
/**
 * prepack.js - stage root-level assets into the publishable package.
 *
 * WHY THIS EXISTS
 * ---------------
 * npm publishes from `_video_nut/` (that is where package.json lives), but the
 * agent command folders (.gemini/, .claude/, .qwen/, .opencode/, .antigravity/,
 * .hermes/, .codex/) plus LICENSE and CONTRIBUTING.md are generated into the
 * REPOSITORY ROOT by scratch/generate_agents.py.
 *
 * package.json `files[]` already lists those paths, and bin/videonut.js copies
 * them from the package root at install time - but nothing ever put them there.
 * Result: `npx videonut init` shipped a tarball with ZERO agent command files
 * and failed silently, because the copy loop is guarded by `if (existsSync)`.
 *
 * This script closes that gap. It runs automatically on `npm pack` / `npm publish`
 * via the "prepack" lifecycle hook, and can be run by hand:
 *
 *     node scripts/prepack.js            # stage
 *     node scripts/prepack.js --verify   # stage, then fail loudly if anything is missing
 *     node scripts/prepack.js --clean    # remove the staged copies again
 *
 * Staged copies are listed in .gitignore so they never get committed twice.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const PKG_ROOT = path.join(__dirname, '..');        // _video_nut/
const REPO_ROOT = path.join(PKG_ROOT, '..');        // repository root

// Directories that live at the repo root but must ship inside the package.
const STAGED_DIRS = [
    '.gemini',
    '.qwen',
    '.claude',
    '.opencode',
    '.antigravity',
    '.hermes',
    '.codex',
];

// Files that live at the repo root but must ship inside the package.
const STAGED_FILES = [
    'LICENSE',
    'CONTRIBUTING.md',
    '.env.example',
];

// Things package.json promises but that may legitimately be absent.
const OPTIONAL = new Set(['CONTRIBUTING.md', '.codex', '.hermes']);

const SKIP_NAMES = new Set(['__pycache__', 'node_modules', '.git', '.DS_Store']);

function copyDir(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
        if (SKIP_NAMES.has(entry.name) || entry.name.endsWith('.pyc')) continue;
        const s = path.join(src, entry.name);
        const d = path.join(dest, entry.name);
        if (entry.isDirectory()) copyDir(s, d);
        else fs.copyFileSync(s, d);
    }
}

function rmrf(target) {
    if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
}

function main() {
    const args = process.argv.slice(2);
    const clean = args.includes('--clean');
    const verify = args.includes('--verify');

    if (clean) {
        for (const name of [...STAGED_DIRS, ...STAGED_FILES]) rmrf(path.join(PKG_ROOT, name));
        console.log('[prepack] Removed staged copies from _video_nut/.');
        return;
    }

    // npm's `files[]` whitelist beats .npmignore for whitelisted directories, so
    // compiled bytecode inside tools/ would still be published. Purge it here -
    // v1.4.0 shipped 11 .pyc files this way.
    const purged = purgePycache(PKG_ROOT);
    if (purged) console.log(`[prepack] Purged ${purged} __pycache__ folder(s).`);

    console.log('[prepack] Staging root assets into the publishable package...');
    const missing = [];

    for (const name of STAGED_DIRS) {
        const src = path.join(REPO_ROOT, name);
        const dest = path.join(PKG_ROOT, name);
        if (!fs.existsSync(src)) {
            if (!OPTIONAL.has(name)) missing.push(name + '/');
            continue;
        }
        rmrf(dest);
        copyDir(src, dest);
        const count = countFiles(dest);
        console.log(`  + ${name}/ (${count} file${count === 1 ? '' : 's'})`);
        if (count === 0) missing.push(`${name}/ (empty)`);
    }

    for (const name of STAGED_FILES) {
        const src = path.join(REPO_ROOT, name);
        const dest = path.join(PKG_ROOT, name);
        if (!fs.existsSync(src)) {
            if (!OPTIONAL.has(name)) missing.push(name);
            continue;
        }
        fs.copyFileSync(src, dest);
        console.log(`  + ${name}`);
    }

    // `workflows/` is referenced by package.json and bin/videonut.js but has
    // never existed. Create it with a placeholder rather than shipping a
    // dangling reference that silently copies nothing.
    const workflows = path.join(PKG_ROOT, 'workflows');
    if (!fs.existsSync(workflows)) {
        fs.mkdirSync(workflows, { recursive: true });
        fs.writeFileSync(
            path.join(workflows, 'README.md'),
            '# Workflows\n\nReserved for saved pipeline presets.\n' +
            'The orchestrator does not read this folder yet; it exists so the\n' +
            'installer copy step has a real target.\n'
        );
        console.log('  + workflows/ (placeholder created)');
    }

    if (missing.length) {
        console.error('\n[prepack] MISSING required package assets:');
        for (const m of missing) console.error(`    - ${m}`);
        console.error('\n  Run `python _video_nut/scratch/generate_agents.py` from the repo root');
        console.error('  to regenerate the CLI command folders, then try again.');
        if (verify) process.exit(1);
        process.exit(1);
    }

    console.log('[prepack] OK - package is complete and safe to publish.');
}

function purgePycache(dir) {
    let n = 0;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        if (entry.name === 'node_modules' || entry.name === '.git') continue;
        const full = path.join(dir, entry.name);
        if (entry.name === '__pycache__') {
            rmrf(full);
            n += 1;
        } else {
            n += purgePycache(full);
        }
    }
    return n;
}

function countFiles(dir) {
    let n = 0;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) n += countFiles(path.join(dir, entry.name));
        else n += 1;
    }
    return n;
}

main();
