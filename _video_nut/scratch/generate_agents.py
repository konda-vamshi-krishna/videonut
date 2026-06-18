#!/usr/bin/env python3
import os
import re
import sys
import json

# Ensure UTF-8 output encoding for terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    print("🎬 VideoNut Agent Configuration Compiler/Sync Script")
    print("====================================================")
    
    # Resolve paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_nut_dir = os.path.dirname(script_dir)
    workspace_root = os.path.dirname(video_nut_dir)
    
    agents_dir = os.path.join(video_nut_dir, "agents")
    
    # Target configurations paths
    dest_claude = os.path.join(workspace_root, ".claude", "commands")
    dest_claude_skills = os.path.join(workspace_root, ".claude", "skills")
    dest_qwen = os.path.join(workspace_root, ".qwen", "commands")
    dest_opencode = os.path.join(workspace_root, ".opencode", "agents")
    dest_gemini = os.path.join(workspace_root, ".gemini", "commands")
    dest_codex = os.path.join(workspace_root, ".codex")
    dest_hermes = os.path.join(workspace_root, ".hermes")
    dest_hermes_skills = os.path.join(dest_hermes, "skills")
    
    # Verify sources exist
    if not os.path.exists(agents_dir):
        print(f"❌ Source agents directory not found: {agents_dir}")
        sys.exit(1)
        
    print(f"📍 Workspace Root: {workspace_root}")
    print(f"📍 Source Agents: {agents_dir}")
    print("----------------------------------------------------")
    
    agent_mappings = {
        "core/eic.md": "eic",
        "core/prompt_agent.md": "prompt",
        "creative/director.md": "director",
        "creative/scriptwriter.md": "scriptwriter",
        "creative/seo.md": "seo",
        "creative/thumbnail.md": "thumbnail",
        "creative/visionary.md": "visionary",
        "research/investigator.md": "investigator",
        "research/topic_scout.md": "topic_scout",
        "technical/archivist.md": "archivist",
        "technical/scavenger.md": "scavenger"
    }
    
    # Ensure all target folders exist
    target_folders = [
        dest_claude,
        dest_claude_skills,
        dest_qwen,
        dest_opencode,
        dest_gemini,
        dest_codex,
        dest_hermes,
        dest_hermes_skills
    ]
    for d in target_folders:
        os.makedirs(d, exist_ok=True)
        
    # We will accumulate agents content for the Codex multi-agent prompt file
    codex_agents_content = []
    
    compiled_count = 0
    
    for rel_path, mapped_name in agent_mappings.items():
        src_path = os.path.join(agents_dir, rel_path.replace("/", os.sep))
        if not os.path.exists(src_path):
            print(f"⚠️ Source agent file not found: {src_path}")
            continue
            
        print(f"Parsing {rel_path}...")
        
        # Read source content
        with open(src_path, "r", encoding="utf-8") as f:
            src_content = f.read()
            
        # Parse frontmatter and body
        parts = re.split(r'^---\s*$', src_content, flags=re.MULTILINE)
        if len(parts) >= 3:
            body = "---".join(parts[2:]).strip()
            # parse metadata
            fm_lines = parts[1].strip().split('\n')
            metadata = {}
            for line in fm_lines:
                if ':' in line:
                    k, v = line.split(':', 1)
                    metadata[k.strip()] = v.strip().strip('"').strip("'")
        else:
            body = src_content.strip()
            metadata = {}
            
        source_description = metadata.get("description", f"VideoNut Agent: {mapped_name}")
        
        # Add to Codex agents document accumulator
        codex_agents_content.append(f"# Agent: {mapped_name}\n> {source_description}\n\n{body}\n\n---\n")
        
        # 1. Write Claude Command (Legacy)
        claude_path = os.path.join(dest_claude, f"{mapped_name}.md")
        with open(claude_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # 2. Write Claude Skill (Modern)
        claude_skill_dir = os.path.join(dest_claude_skills, mapped_name)
        os.makedirs(claude_skill_dir, exist_ok=True)
        claude_skill_path = os.path.join(claude_skill_dir, "SKILL.md")
        with open(claude_skill_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # 3. Write Qwen Command
        qwen_path = os.path.join(dest_qwen, f"{mapped_name}.md")
        with open(qwen_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # 4. Write OpenCode Agent with frontmatter preservation
        opencode_path = os.path.join(dest_opencode, f"{mapped_name}.md")
        fallback_opencode_fm = f"""---
description: "VideoNut Agent: {mapped_name} - {source_description}"
mode: "primary"
model: "anthropic/claude-3.5-sonnet"
permissions:
  - bash
  - read
  - edit
  - websearch
---
"""
        opencode_fm = fallback_opencode_fm
        if os.path.exists(opencode_path):
            with open(opencode_path, "r", encoding="utf-8") as f:
                target_content = f.read()
            parts_target = re.split(r'^---\s*$', target_content, flags=re.MULTILINE)
            if len(parts_target) >= 3:
                opencode_fm = "---" + parts_target[1] + "---\n"
                
        with open(opencode_path, "w", encoding="utf-8") as f:
            f.write(opencode_fm + body + "\n")
            
        # 5. Write Hermes Skill
        hermes_skill_path = os.path.join(dest_hermes_skills, f"{mapped_name}.md")
        with open(hermes_skill_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # 6. Write Gemini TOML Command with description preservation
        gemini_path = os.path.join(dest_gemini, f"{mapped_name}.toml")
        fallback_toml_desc = source_description
        toml_desc = fallback_toml_desc
        if os.path.exists(gemini_path):
            try:
                with open(gemini_path, "r", encoding="utf-8") as f:
                    gemini_content = f.read()
                match = re.search(r'description\s*=\s*"(.*?)"', gemini_content)
                if match:
                    toml_desc = match.group(1)
            except Exception:
                pass
                
        # Escape triple quotes and backslashes in multi-line TOML strings
        escaped_body = body.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
        gemini_toml_content = f'description = "{toml_desc}"\nprompt = """\n{escaped_body}\n"""\n'
        with open(gemini_path, "w", encoding="utf-8") as f:
            f.write(gemini_toml_content)
            
        print(f"  └─ ✅ Compiled {mapped_name} successfully")
        compiled_count += 1
        
    print("----------------------------------------------------")
    print("Generating Desktop Manifests & Configurations...")
    
    # 7. Write Codex agents library
    codex_agents_path = os.path.join(dest_codex, "AGENTS.md")
    with open(codex_agents_path, "w", encoding="utf-8") as f:
        f.write("# VideoNut Agent Persona Library\n\n" + "\n".join(codex_agents_content))
    print("  ├─ ✅ Generated .codex/AGENTS.md")
    
    # 8. Write Codex project config (if missing)
    codex_config_path = os.path.join(dest_codex, "config.toml")
    if not os.path.exists(codex_config_path):
        codex_config = """# OpenAI Codex Desktop App Project Configuration
[project]
name = "videonut"
trusted = true
default_model = "gpt-4o"

[sandbox]
allow_bash = true
allow_read = true
allow_edit = true
allow_websearch = true
"""
        with open(codex_config_path, "w", encoding="utf-8") as f:
            f.write(codex_config)
        print("  ├─ ✅ Generated default .codex/config.toml")
    else:
        print("  ├─ ℹ️  Preserved existing .codex/config.toml")
        
    # 9. Write OpenCode Desktop manifest
    opencode_manifest_path = os.path.join(workspace_root, ".opencode.json")
    opencode_manifest = {
        "project": "videonut",
        "version": "1.3.9",
        "agent_dir": ".opencode/agents",
        "permissions": [
            "bash",
            "read",
            "edit",
            "websearch"
        ],
        "default_model": "anthropic/claude-3.5-sonnet"
    }
    with open(opencode_manifest_path, "w", encoding="utf-8") as f:
        json.dump(opencode_manifest, f, indent=2)
    print("  ├─ ✅ Generated .opencode.json manifest")
    
    # 10. Write Hermes configuration (if missing)
    hermes_config_path = os.path.join(dest_hermes, "config.toml")
    if not os.path.exists(hermes_config_path):
        hermes_config = """# Nous Research Hermes Agents Configuration
[agent]
name = "hermes-videonut"
model = "nousresearch/hermes-3-llama-3.1-405b"

[sandbox]
permissions = ["terminal", "fs-read", "fs-write", "web"]
"""
        with open(hermes_config_path, "w", encoding="utf-8") as f:
            f.write(hermes_config)
        print("  └─ ✅ Generated default .hermes/config.toml")
    else:
        print("  └─ ℹ️  Preserved existing .hermes/config.toml")
        
    print("----------------------------------------------------")
    print(f"🎉 Done! Successfully compiled/synced {compiled_count} agents to all CLIs and Desktop apps.")
    print("====================================================")

if __name__ == "__main__":
    main()
