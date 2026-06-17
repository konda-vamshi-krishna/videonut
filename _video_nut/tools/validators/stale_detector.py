import os
import sys

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def detect_stale_stages(project_path):
    """
    Checks modification times of pipeline deliverables to determine if any downstream files are stale.
    Pipeline flow:
    topic_brief.md -> truth_dossier.md -> narrative_script.md -> master_script.md -> (asset_manifest.md & visual_prompts.md) -> assets/
    
    Returns:
        dict: A mapping of stage_name -> boolean (True if stale, False otherwise)
    """
    brief_path = os.path.join(project_path, "topic_brief.md")
    dossier_path = os.path.join(project_path, "truth_dossier.md")
    script_path = os.path.join(project_path, "narrative_script.md")
    master_path = os.path.join(project_path, "master_script.md")
    manifest_path = os.path.join(project_path, "asset_manifest.md")
    prompts_path = os.path.join(project_path, "visual_prompts.md")
    assets_dir = os.path.join(project_path, "assets")

    # Helper to get mtime, returns 0 if doesn't exist
    def get_mtime(path):
        if os.path.exists(path):
            return os.path.getmtime(path)
        return 0

    t_brief = get_mtime(brief_path)
    t_dossier = get_mtime(dossier_path)
    t_script = get_mtime(script_path)
    t_master = get_mtime(master_path)
    t_manifest = get_mtime(manifest_path)
    t_prompts = get_mtime(prompts_path)
    
    stale_stages = {
        "investigation": False,
        "scriptwriting": False,
        "direction": False,
        "scavenging": False,
        "visionary": False,
        "archiving": False
    }

    # 1. Investigation is stale if topic_brief.md is newer than truth_dossier.md
    if t_brief > 0 and t_dossier > 0 and t_brief > t_dossier:
        stale_stages["investigation"] = True
        
    # 2. Scriptwriting is stale if truth_dossier.md is newer than narrative_script.md, or if investigation is stale
    if (t_dossier > 0 and t_script > 0 and t_dossier > t_script) or stale_stages["investigation"]:
        stale_stages["scriptwriting"] = True

    # 3. Direction is stale if narrative_script.md is newer than master_script.md, or if scriptwriting is stale
    if (t_script > 0 and t_master > 0 and t_script > t_master) or stale_stages["scriptwriting"]:
        stale_stages["direction"] = True

    # 4. Scavenging is stale if master_script.md is newer than asset_manifest.md, or if direction is stale
    if (t_master > 0 and t_manifest > 0 and t_master > t_manifest) or stale_stages["direction"]:
        stale_stages["scavenging"] = True

    # 5. Visionary is stale if master_script.md is newer than visual_prompts.md, or if direction is stale
    if (t_master > 0 and t_prompts > 0 and t_master > t_prompts) or stale_stages["direction"]:
        stale_stages["visionary"] = True

    # 6. Archiving is stale if asset_manifest.md is newer than the assets directory (or if scavenging is stale)
    # Since assets is a directory, we can check if its creation/modification is older than asset_manifest.md
    t_assets = get_mtime(assets_dir)
    if (t_manifest > 0 and t_assets > 0 and t_manifest > t_assets) or stale_stages["scavenging"]:
        stale_stages["archiving"] = True

    return stale_stages

def main():
    if len(sys.argv) < 2:
        print("Usage: python stale_detector.py <project_path>")
        sys.exit(1)
        
    project_path = sys.argv[1]
    if not os.path.exists(project_path):
        print(f"❌ Project path '{project_path}' does not exist.")
        sys.exit(1)
        
    stale = detect_stale_stages(project_path)
    
    print("📋 Stale Stages Report:")
    for stage, is_stale in stale.items():
        status = "⚠️  STALE (needs re-run)" if is_stale else "✅ Up-to-date"
        print(f"  - {stage}: {status}")
        
    # Output JSON representation for orchestrator parsing
    import json
    print("STALE_JSON:" + json.dumps(stale))

if __name__ == "__main__":
    main()
