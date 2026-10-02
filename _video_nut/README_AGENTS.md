# VideoNut Agent Rules & Workspace Structure Guide

This guide explains the directory layout of the custom AI agents configured in
this workspace, preventing accidental deletion or confusion.

---

## 📁 Workspace Directory Map

The workspace contains both **active CLI configurations** (at the root) and
**core source files** (inside `_video_nut/`):

```
<workspace root>/
├── .claude/
│   ├── commands/            <-- ACTIVE: Custom commands for Anthropic Claude Code
│   └── skills/              <-- ACTIVE: Claude Skills (one folder per agent)
├── .gemini/
│   └── commands/            <-- ACTIVE: Custom commands for Google Gemini CLI
├── .opencode/
│   └── agents/              <-- ACTIVE: Custom agents for OpenCode CLI
├── .qwen/
│   └── commands/            <-- ACTIVE: Custom commands for Qwen Code CLI
├── .hermes/
│   └── skills/              <-- ACTIVE: Skills for Nous Hermes
├── .codex/
│   └── AGENTS.md            <-- ACTIVE: Roster for OpenAI Codex
├── .antigravity/
│   └── config.toml          <-- ACTIVE: Rule mappings for Antigravity editor
├── .cursorrules             <-- ACTIVE: Rules for Cursor IDE
├── .clinerules              <-- ACTIVE: Rules for Cline IDE
├── .aider.conf.yml          <-- ACTIVE: Config for Aider CLI
├── CONVENTIONS.md           <-- ACTIVE: Conventions file for Aider CLI
├── .env                     <-- SECRETS: API keys (gitignored - see .env.example)
│
└── _video_nut/
    ├── agents/              <-- SOURCE OF TRUTH: Do NOT delete. Core agent personas
    │   ├── core/            eic, prompt_agent, self_review_protocol
    │   ├── creative/        scriptwriter, narrator, director, visionary, seo, thumbnail
    │   ├── research/        investigator, topic_scout
    │   └── technical/       archivist, scavenger
    ├── tools/
    │   ├── audio/           <-- TTS engine, provider adapters, script normalizer
    │   ├── downloaders/     <-- Asset fetchers used by the Scavenger
    │   └── validators/      <-- Quality gates (output, audio, staleness)
    ├── cli_templates/       <-- BACKUP TEMPLATES copied by setup.js
    └── config.yaml          <-- Settings. NEVER put API keys here.
```

---

## 🔁 Regenerating the CLI folders

Every root CLI folder is **compiled output**. The generator is:

```bash
python _video_nut/scratch/generate_agents.py
```

Edit personas in `_video_nut/agents/**` and re-run it. Hand-editing
`.claude/commands/*.md` (etc.) works until the next regeneration wipes it.
Note that `_video_nut/cli_templates/**` is *not* produced by the generator and
must be updated by hand when an agent is added or renamed.

---

## ⚠️ Crucial Safety Warnings for Developers

1.  **Do NOT delete the `_video_nut/agents/` folder.**
    Even though the agent personas are inlined into the root CLI folders for
    performance and compatibility, the Python orchestrator reads from
    `_video_nut/agents/` at runtime. Deleting it will crash the backend builder.
2.  **Do NOT delete the root `.claude`, `.gemini`, `.qwen` or `.opencode` folders.**
    They contain the slash-command templates loaded by the AI CLIs. Deleting them
    disables slash commands (like `/investigator`) inside your AI terminals.
3.  **Never commit `.env`.**
    The Narrator agent spends real money through TTS APIs. Keys belong in `.env`
    (gitignored); `config.yaml` is committed and shipped to every user.
4.  **Core Persona vs. Wrapper distinction:**
    *   **Root folders (e.g. `.claude/commands/`)**: self-contained configs parsed by CLIs.
    *   **Source folder (`_video_nut/agents/`)**: read by the backend Python code.
