# VideoNut Agent Rules & Workspace Structure Guide

This guide explains the directory layout of the custom AI agents configured in this workspace, preventing accidental deletion or confusion.

---

## 📁 Workspace Directory Map

The workspace contains both **active CLI configurations** (at the root) and **core source files** (inside `_video_nut/`):

```
AI _TEAM/
├── .claude/
│   └── commands/            <-- ACTIVE: Custom commands for Anthropic Claude Code
├── .gemini/
│   └── commands/            <-- ACTIVE: Custom commands for Google Gemini CLI
├── .opencode/
│   └── agents/              <-- ACTIVE: Custom agents for OpenCode CLI
├── .qwen/
│   └── commands/            <-- ACTIVE: Custom commands for Qwen Code CLI
├── .antigravity/
│   └── config.toml          <-- ACTIVE: Rule mappings for Antigravity editor integration
├── .cursorrules             <-- ACTIVE: Rules for Cursor IDE editor
├── .clinerules              <-- ACTIVE: Rules for Cline IDE editor
├── .aider.conf.yml          <-- ACTIVE: Config for Aider CLI
├── CONVENTIONS.md           <-- ACTIVE: Conventions file for Aider CLI
│
└── _video_nut/
    ├── agents/              <-- SOURCE OF TRUTH: Do NOT delete. Core agent personas
    │   ├── core/            
    │   ├── creative/        
    │   ├── research/        
    │   └── technical/       
    ├── .claude/             <-- BACKUP TEMPLATE: Original Claude templates
    └── .opencode/           <-- BACKUP TEMPLATE: Original OpenCode templates
```

---

## ⚠️ Crucial Safety Warnings for Developers

1.  **Do NOT delete the `_video_nut/agents/` folder:**
    Even though the agent personas have been inlined into the root CLI folders for performance and compatibility, the Python orchestrator and pipeline scripts open and read from `_video_nut/agents/` at runtime. Deleting this folder will crash the backend documentary builder.
2.  **Do NOT delete the root `.claude`, `.gemini`, or `.opencode` folders:**
    These folders contain the actual slash command templates loaded by the AI CLIs. Deleting them will disable slash commands (like `/investigator`) inside your AI terminals.
3.  **Core Persona vs. Wrapper distinction:**
    *   **Root Folders (e.g. `.claude/commands/`)**: Self-contained configurations parsed by CLIs.
    *   **Source Folders (`_video_nut/agents/`)**: Read by the backend Python code.
