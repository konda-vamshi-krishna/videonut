#!/usr/bin/env python3
import os
import re
import sys

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
    
    dest_claude = os.path.join(workspace_root, ".claude", "commands")
    dest_qwen = os.path.join(workspace_root, ".qwen", "commands")
    dest_opencode = os.path.join(workspace_root, ".opencode", "agents")
    dest_gemini = os.path.join(workspace_root, ".gemini", "commands")
    
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
    
    # Ensure destination directories exist
    for d in [dest_claude, dest_qwen, dest_opencode, dest_gemini]:
        os.makedirs(d, exist_ok=True)
        
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
        
        # Write Claude Command
        claude_path = os.path.join(dest_claude, f"{mapped_name}.md")
        with open(claude_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # Write Qwen Command
        qwen_path = os.path.join(dest_qwen, f"{mapped_name}.md")
        with open(qwen_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
            
        # Write OpenCode Agent with frontmatter preservation
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
        # Read existing frontmatter if possible
        opencode_fm = fallback_opencode_fm
        if os.path.exists(opencode_path):
            with open(opencode_path, "r", encoding="utf-8") as f:
                target_content = f.read()
            parts_target = re.split(r'^---\s*$', target_content, flags=re.MULTILINE)
            if len(parts_target) >= 3:
                opencode_fm = "---" + parts_target[1] + "---\n"
                
        with open(opencode_path, "w", encoding="utf-8") as f:
            f.write(opencode_fm + body + "\n")
            
        # Write Gemini TOML Command with description preservation
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
        # Double backslashes in prompt string to avoid escaping issues in TOML
        escaped_body = body.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
        gemini_toml_content = f'description = "{toml_desc}"\nprompt = """\n{escaped_body}\n"""\n'
        with open(gemini_path, "w", encoding="utf-8") as f:
            f.write(gemini_toml_content)
            
        print(f"  └─ ✅ Compiled {mapped_name} successfully")
        compiled_count += 1
        
    print("----------------------------------------------------")
    print(f"🎉 Done! Successfully compiled/synced {compiled_count} agents.")
    print("====================================================")

if __name__ == "__main__":
    main()
