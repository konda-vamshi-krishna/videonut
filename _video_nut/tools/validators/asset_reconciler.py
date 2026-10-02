#!/usr/bin/env python3
"""
Reconcile AI-generated visuals against the asset manifest.

The gap this closes
-------------------
The Director tags shots it wants created rather than sourced:

    **Source:** [CREATE]

The Visionary turns each of those into a pasteable prompt in visual_prompts.md.
The user then generates the image or clip in Midjourney / Flux / Sora - an
external, manual step VideoNut does not automate.

And there the chain stopped. visual_prompts.md had no reader, generated files
had no agreed home, and asset_manifest.md only ever listed downloadable URLs.
So every AI shot was prompted, generated, and then silently dropped: the editor
received an asset folder missing all of them, with nothing recording the fact.

This tool reconciles the two sides mechanically:

    scenes declared in visual_prompts.md   vs   files present in assets/generated/

and reports matched, missing and orphaned files. With --write it folds the
matched ones into asset_manifest.md so the manifest finally describes the whole
edit, not just the downloadable half.

Usage
-----
    python asset_reconciler.py <project_path>
    python asset_reconciler.py <project_path> --write
    python asset_reconciler.py <project_path> --json

Exit codes
    0  every declared scene has a file
    1  at least one scene is missing its asset
    2  visual_prompts.md is absent or unreadable
"""

import json
import os
import re
import sys

# Files a generation tool plausibly produces. Anything else in the folder is
# reported as an orphan rather than silently ignored.
MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".mp4", ".mov", ".webm", ".mkv", ".avi",
}

GENERATED_DIRNAME = os.path.join("assets", "generated")

# "## Scene 3: The Vault (AI IMAGE)" - the brackets in the Visionary's template
# are placeholders, so tolerate both "Scene 3" and "Scene [3]".
SCENE_RE = re.compile(
    r"^#{1,4}\s*Scene\s*\[?\s*(\d+)\s*\]?\s*[:\-]?\s*(.*?)\s*$",
    re.IGNORECASE,
)
KIND_RE = re.compile(r"\((?:AI\s+)?(IMAGE|VIDEO)\)", re.IGNORECASE)

# A generated file belongs to a scene if it starts scene_<n>_ / scene<n>- / s<n>_
# NOTE: do not end this with \b. "_" is a word character, so \b never matches
# between the digits and the underscore in "scene_01_vault.png" - the common
# case. A negative lookahead for a further digit is what is actually meant.
FILE_SCENE_RE = re.compile(r"^(?:scene|s)[ _-]?0*(\d+)(?![0-9])", re.IGNORECASE)


def parse_visual_prompts(path):
    """Return [{scene, title, kind}] for every scene declared in visual_prompts.md."""
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    scenes, seen = [], set()
    for i, line in enumerate(lines):
        m = SCENE_RE.match(line)
        if not m:
            continue
        number = int(m.group(1))
        remainder = m.group(2) or ""

        kind_match = KIND_RE.search(remainder)
        # The kind can also sit on the "Target Tool" / "Duration" lines below.
        if not kind_match:
            lookahead = "\n".join(lines[i + 1:i + 8])
            if re.search(r"\*\*Duration\*\*\s*(?:\(If Video\))?\s*:\s*\S", lookahead):
                kind = "VIDEO"
            else:
                kind = "IMAGE"
        else:
            kind = kind_match.group(1).upper()

        title = KIND_RE.sub("", remainder).strip(" -:")
        # The Visionary's own template line is a placeholder, not a real scene.
        if title.startswith("[") and title.endswith("]"):
            title = title.strip("[]")
        if number in seen:
            continue
        seen.add(number)
        scenes.append({"scene": number, "title": title or f"Scene {number}", "kind": kind})

    return sorted(scenes, key=lambda s: s["scene"])


def scan_generated(project_path):
    """Return {scene_number: [relative paths]} plus a list of unmatched files."""
    folder = os.path.join(project_path, GENERATED_DIRNAME)
    by_scene, orphans = {}, []
    if not os.path.isdir(folder):
        return by_scene, orphans, folder

    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        if os.path.splitext(name)[1].lower() not in MEDIA_EXTENSIONS:
            continue
        # A zero-byte file is a failed export, not an asset.
        size = os.path.getsize(full)
        rel = os.path.join(GENERATED_DIRNAME, name).replace("\\", "/")
        m = FILE_SCENE_RE.match(name)
        if not m:
            orphans.append({"file": rel, "reason": "filename does not start with scene_<n>_",
                            "bytes": size})
            continue
        if size == 0:
            orphans.append({"file": rel, "reason": "file is 0 bytes (failed export)",
                            "bytes": 0})
            continue
        by_scene.setdefault(int(m.group(1)), []).append(rel)

    return by_scene, orphans, folder


def reconcile(project_path):
    prompts_path = os.path.join(project_path, "visual_prompts.md")
    if not os.path.exists(prompts_path):
        return None, f"No visual_prompts.md in {project_path}. Run /visionary first."

    try:
        scenes = parse_visual_prompts(prompts_path)
    except Exception as e:  # noqa: BLE001
        return None, f"Could not parse visual_prompts.md: {type(e).__name__}: {e}"

    by_scene, orphans, folder = scan_generated(project_path)

    matched, missing = [], []
    for s in scenes:
        files = by_scene.get(s["scene"], [])
        if files:
            matched.append({**s, "files": files})
        else:
            missing.append(s)

    declared = {s["scene"] for s in scenes}
    for number, files in sorted(by_scene.items()):
        if number not in declared:
            for f in files:
                orphans.append({"file": f, "bytes": os.path.getsize(os.path.join(project_path, f)),
                                "reason": f"scene {number} is not declared in visual_prompts.md"})

    return {
        "project": project_path,
        "generated_folder": folder,
        "declared": len(scenes),
        "matched": matched,
        "missing": missing,
        "orphans": orphans,
        "complete": not missing,
    }, None


MANIFEST_HEADING = "## 🎨 AI-Generated Assets"


def write_manifest_section(project_path, result):
    """Insert/replace the AI-generated section of asset_manifest.md."""
    manifest = os.path.join(project_path, "asset_manifest.md")

    rows = ["| Scene | Description | Type | File | Status |",
            "|-------|-------------|------|------|--------|"]
    for m in result["matched"]:
        for f in m["files"]:
            rows.append(f"| {m['scene']} | {m['title']} | AI {m['kind']} | `{f}` | ✅ Present |")
    for m in result["missing"]:
        rows.append(f"| {m['scene']} | {m['title']} | AI {m['kind']} | — | ❌ NOT GENERATED |")

    section = [MANIFEST_HEADING, "",
               "Generated from `visual_prompts.md` by `asset_reconciler.py`. "
               "Files live in `assets/generated/` and are named `scene_<n>_*`.", ""]
    section += rows
    if result["orphans"]:
        section += ["", "**Unmatched files in `assets/generated/`:**", ""]
        for o in result["orphans"]:
            section.append(f"- `{o['file']}` — {o['reason']}")
    section_text = "\n".join(section) + "\n"

    if os.path.exists(manifest):
        with open(manifest, "r", encoding="utf-8") as fh:
            content = fh.read()
    else:
        content = "# Asset Manifest\n\n"

    if MANIFEST_HEADING in content:
        # Replace from our heading up to the next same-level heading.
        pattern = re.compile(
            re.escape(MANIFEST_HEADING) + r".*?(?=\n## (?!🎨)|\Z)", re.S)
        content = pattern.sub(section_text.rstrip("\n") + "\n", content, count=1)
    else:
        content = content.rstrip("\n") + "\n\n" + section_text

    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write(content)
    return manifest


def write_manual_required(project_path, result):
    """Append missing generations to MANUAL_REQUIRED.txt, the Archivist's convention."""
    if not result["missing"]:
        return None
    path = os.path.join(project_path, "MANUAL_REQUIRED.txt")
    lines = ["", "=== AI generations still missing (asset_reconciler) ==="]
    for m in result["missing"]:
        lines.append(
            f"Scene {m['scene']} ({m['kind']}): {m['title']} - "
            f"generate from visual_prompts.md and save as "
            f"assets/generated/scene_{m['scene']:02d}_<name>")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    if not args:
        print("Usage: python asset_reconciler.py <project_path> [--write] [--json]")
        sys.exit(2)

    project_path = args[0]
    result, error = reconcile(project_path)
    if error:
        if "--json" in flags:
            print(json.dumps({"ok": False, "error": error}, indent=2))
        else:
            print(f"[FAIL] {error}")
        sys.exit(2)

    if "--json" in flags:
        print(json.dumps(result, indent=2))
    else:
        print(f"[SCAN] AI asset reconciliation: {project_path}")
        print("-" * 58)
        print(f"  Declared in visual_prompts.md : {result['declared']}")
        print(f"  Present in assets/generated   : {len(result['matched'])}")
        print(f"  Missing                       : {len(result['missing'])}")
        print(f"  Unmatched files               : {len(result['orphans'])}")
        print("-" * 58)
        for m in result["matched"]:
            print(f"  [OK]   Scene {m['scene']:>2} ({m['kind']:<5}) {m['title'][:34]:<34} "
                  f"{', '.join(os.path.basename(f) for f in m['files'])}")
        for m in result["missing"]:
            print(f"  [MISS] Scene {m['scene']:>2} ({m['kind']:<5}) {m['title'][:34]:<34} "
                  f"expected assets/generated/scene_{m['scene']:02d}_*")
        for o in result["orphans"]:
            print(f"  [ORPH] {o['file']} - {o['reason']}")
        print("-" * 58)

    if "--write" in flags:
        manifest = write_manifest_section(project_path, result)
        print(f"[OK] Updated {manifest}")
        mr = write_manual_required(project_path, result)
        if mr:
            print(f"[OK] Logged {len(result['missing'])} missing generation(s) to {mr}")

    if result["missing"]:
        print(f"[FAIL] {len(result['missing'])} AI shot(s) have no generated file. "
              f"The edit would be missing them.")
        sys.exit(1)

    print("[SUCCESS] Every AI shot declared in visual_prompts.md has an asset.")
    sys.exit(0)


if __name__ == "__main__":
    main()
