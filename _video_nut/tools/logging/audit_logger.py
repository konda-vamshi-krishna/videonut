#!/usr/bin/env python3
"""
Audit Logger for VideoNut

Logs all tool actions (search, download, screenshot, validation, read) to both
a machine-readable JSONL log and a beautifully formatted human-readable markdown log
in the project directory.

Usage:
    # Python import
    from tools.logging.audit_logger import log_action
    log_action("projects/my_project", "download", "Downloaded audio stream", url="...", status="ok")

    # Command line usage
    python audit_logger.py --project "projects/my_project" --category "download" --action "Downloaded video" --url "..." --status "ok"
"""

import sys
import os
import argparse
import json
import threading
from datetime import datetime
from pathlib import Path

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Thread lock for in-process thread safety
_log_lock = threading.Lock()


def log_action(project_path: str, category: str, action: str, url: str = "", 
               local_path: str = "", status: str = "ok", details: str = "") -> None:
    """
    Logs an action to both project_path/audit_log.json and project_path/audit_log.md.
    
    Args:
        project_path: The root directory of the current project (e.g. project folder)
        category: "search" | "download" | "screenshot" | "validate" | "read"
        action: Human-readable description of the action
        url: Optional source URL
        local_path: Optional local file saved path
        status: "ok" | "failed" | "skipped" | "fallback"
        details: Optional additional metadata or error message
    """
    if not project_path:
        # Fallback if no project path is specified
        project_path = "."
        
    proj_dir = Path(project_path)
    try:
        proj_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[AuditLogger Error] Could not create directory {project_path}: {e}", file=sys.stderr)
        return

    json_path = proj_dir / "audit_log.json"
    md_path = proj_dir / "audit_log.md"

    timestamp = datetime.now().isoformat()
    
    # Normalize path strings to use forward slashes for cross-platform compatibility
    normalized_local_path = local_path.replace("\\", "/") if local_path else ""
    
    entry = {
        "timestamp": timestamp,
        "category": category,
        "action": action,
        "url": url,
        "local_path": normalized_local_path,
        "status": status,
        "details": details
    }

    # Thread safety for appending to JSON and writing to MD
    with _log_lock:
        # 1. Write to JSONL (append-only)
        try:
            # Simple file lock mechanism using dynamic lock file could be added, 
            # but standard append is atomic for small writes on most systems.
            with open(json_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AuditLogger Error] Could not write to {json_path}: {e}", file=sys.stderr)

        # 2. Update/Write to MD (regenerated or appended intelligently)
        # To maintain a nice grouped-by-category UI, we will read all entries from the JSONL
        # and rebuild the markdown summary report.
        try:
            all_entries = []
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                all_entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            
            # Rebuild MD content
            md_content = []
            md_content.append(f"# 📋 VideoNut Audit Log")
            md_content.append(f"> **Project**: `{proj_dir.resolve().name}`  ")
            md_content.append(f"> **Last Activity**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ")
            md_content.append("\n---\n")
            
            # Summary Metrics
            status_counts = {"ok": 0, "failed": 0, "skipped": 0, "fallback": 0}
            cat_counts = {}
            for ent in all_entries:
                st = ent.get("status", "ok").lower()
                status_counts[st] = status_counts.get(st, 0) + 1
                cat = ent.get("category", "other").lower()
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            
            md_content.append("## 📈 Pipeline Summary")
            md_content.append(f"- **Total Actions Logged**: {len(all_entries)}")
            md_content.append("- **Status Breakdown**: " + ", ".join([f"`{k.upper()}`: {v}" for k, v in status_counts.items() if v > 0]))
            md_content.append("- **Category Breakdown**: " + ", ".join([f"`{k.capitalize()}`: {v}" for k, v in cat_counts.items() if v > 0]))
            md_content.append("\n---\n")

            # Group entries by category
            categories = ["search", "download", "screenshot", "validate", "read"]
            grouped = {cat: [] for cat in categories}
            grouped["other"] = []
            
            for ent in all_entries:
                cat = ent.get("category", "other").lower()
                if cat in grouped:
                    grouped[cat].append(ent)
                else:
                    grouped["other"].append(ent)

            # Define emojis for each category
            emojis = {
                "search": "🔍",
                "download": "📥",
                "screenshot": "📸",
                "validate": "✅",
                "read": "📖",
                "other": "⚙️"
            }

            status_emojis = {
                "ok": "🟢",
                "failed": "🔴",
                "skipped": "🟡",
                "fallback": "🟠"
            }

            md_content.append("## 🗂️ Audit Details by Category\n")
            
            for cat in categories + ["other"]:
                ents = grouped[cat]
                if not ents:
                    continue
                
                emoji = emojis.get(cat, "⚙️")
                md_content.append(f"### {emoji} {cat.capitalize()} ({len(ents)})")
                
                # Write table for this category
                md_content.append("| Status | Timestamp | Action Description | Resource / URL | Saved Asset |")
                md_content.append("| :---: | :--- | :--- | :--- | :--- |")
                
                for ent in ents:
                    st_emoji = status_emojis.get(ent.get("status", "ok").lower(), "⚪")
                    ts = ent.get("timestamp", "")
                    if ts:
                        # Reformat timestamp for readability
                        try:
                            ts_dt = datetime.fromisoformat(ts)
                            ts_str = ts_dt.strftime("%H:%M:%S")
                        except ValueError:
                            ts_str = ts[:19]
                    else:
                        ts_str = "N/A"
                        
                    act = ent.get("action", "")
                    res_url = ent.get("url", "")
                    if res_url:
                        # Shorten URL for table readability
                        short_url = res_url
                        if len(short_url) > 40:
                            short_url = short_url[:37] + "..."
                        res_str = f"[{short_url}]({res_url})"
                    else:
                        res_str = "-"
                        
                    asset = ent.get("local_path", "")
                    if asset:
                        # Make a relative link if possible
                        try:
                            # Path(asset) can be absolute or relative. Make relative to project directory if possible
                            asset_path = Path(asset)
                            if asset_path.is_absolute():
                                try:
                                    rel_path = asset_path.relative_to(proj_dir.resolve())
                                    asset_str = f"[{rel_path.name}](file:///{asset_path.as_posix()})"
                                except ValueError:
                                    asset_str = f"[{asset_path.name}](file:///{asset_path.as_posix()})"
                            else:
                                # It's already relative
                                asset_str = f"[{asset_path.name}](file:///{proj_dir.resolve().joinpath(asset_path).as_posix()})"
                        except Exception:
                            asset_str = f"`{asset}`"
                    else:
                        asset_str = "-"
                        
                    # Handle markdown character escaping
                    act_escaped = act.replace("|", "\\|")
                    md_content.append(f"| {st_emoji} | {ts_str} | {act_escaped} | {res_str} | {asset_str} |")
                    
                    # If there are details, add them as a sub-bullet under the table or inside details?
                    # Since markdown tables can't easily have multi-line, we just omit detail logs from the table 
                    # but we can list details or errors at the end of the section if failed
                    
                md_content.append("") # Spacer
                
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))
                
        except Exception as e:
            print(f"[AuditLogger Error] Could not write to {md_path}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Log actions to the VideoNut audit log.")
    parser.add_argument("--project", "-p", required=True, help="Path to the project directory")
    parser.add_argument("--category", "-c", required=True, 
                        choices=["search", "download", "screenshot", "validate", "read"], 
                        help="Action category")
    parser.add_argument("--action", "-a", required=True, help="Description of the action")
    parser.add_argument("--url", "-u", default="", help="Resource URL involved")
    parser.add_argument("--local-path", "-l", default="", help="Local path of the downloaded/saved file")
    parser.add_argument("--status", "-s", default="ok", 
                        choices=["ok", "failed", "skipped", "fallback"], 
                        help="Status of the action")
    parser.add_argument("--details", "-d", default="", help="Extra details or error messages")

    args = parser.parse_args()

    log_action(
        project_path=args.project,
        category=args.category,
        action=args.action,
        url=args.url,
        local_path=args.local_path,
        status=args.status,
        details=args.details
    )
    print(f"Logged: {args.category} - {args.action}")


if __name__ == "__main__":
    main()
