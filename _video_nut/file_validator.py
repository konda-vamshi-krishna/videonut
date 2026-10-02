#!/usr/bin/env python3
"""
DEPRECATED - kept only so existing commands and scripts keep working.

Use `tools/validators/output_validator.py` instead:

    python tools/validators/output_validator.py project <project_dir>
    python tools/validators/output_validator.py dossier <project_dir>/truth_dossier.md

Why this file no longer has its own logic
-----------------------------------------
VideoNut shipped two validators with two different, partly contradictory
contracts for the same files (audit finding F3). This one demanded headings the
agents never produced - it required `The Angle` and `The Conflict` sections in
truth_dossier.md, but investigator.md's MANDATORY dossier template has only ever
declared `## Investigation Questions` and `## Findings`. So it failed on
perfectly correct output, and because it was wired into the EIC's toolchain that
looked like the *pipeline* was broken rather than the checker.

It also checked structure by exact string match, which breaks the moment an
agent's template is reworded. The surviving validator checks substance - size,
citation count, question count, cue balance, narration coverage - which is what
those checks were actually trying to approximate.

Everything here now delegates. There is one implementation and one contract.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "validators"))

try:
    from output_validator import (  # noqa: E402
        validate_dossier,
        validate_script,
        validate_manifest,
        validate_master_script,
        validate_project,
    )
except ImportError as e:  # pragma: no cover - only if the package is broken
    print(f"[FAIL] Cannot load output_validator: {e}")
    print("       Expected at tools/validators/output_validator.py")
    sys.exit(1)


# Backwards-compatible aliases for anything importing the old names.
validate_truth_dossier = validate_dossier
validate_narrative_script = validate_script
validate_asset_manifest = validate_manifest


def validate_project_directory(project_dir):
    """Deprecated. Returns {filename: (ok, message)} as the old version did."""
    results = {}
    for filename, fn in (
        ("truth_dossier.md", validate_dossier),
        ("narrative_script.md", validate_script),
        ("master_script.md", validate_master_script),
        ("asset_manifest.md", validate_manifest),
    ):
        results[filename] = fn(os.path.join(project_dir, filename))
    return results


def _warn():
    print("[WARN] file_validator.py is deprecated and now just forwards to")
    print("       tools/validators/output_validator.py. Please switch to:")
    print("           python tools/validators/output_validator.py project <dir>")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python file_validator.py <project_directory> [specific_file]")
        print()
        print("DEPRECATED. Use instead:")
        print("    python tools/validators/output_validator.py project <project_directory>")
        sys.exit(1)

    _warn()
    project_dir = sys.argv[1]
    specific_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(project_dir):
        print(f"[FAIL] Project directory does not exist: {project_dir}")
        sys.exit(1)

    if specific_file:
        validators = {
            "truth_dossier.md": validate_dossier,
            "narrative_script.md": validate_script,
            "master_script.md": validate_master_script,
            "asset_manifest.md": validate_manifest,
        }
        if specific_file not in validators:
            print(f"[FAIL] Unknown file type: {specific_file}")
            print("Supported: " + ", ".join(validators))
            sys.exit(1)
        ok, msg = validators[specific_file](os.path.join(project_dir, specific_file))
        print(f"{'[OK]' if ok else '[FAIL]'} {specific_file}: {msg}")
        sys.exit(0 if ok else 1)

    ok, msg = validate_project(project_dir)
    print(f"[SCAN] Validating VideoNut project: {project_dir}")
    print("-" * 50)
    print(msg)
    print("-" * 50)
    print("[SUCCESS] All files validated successfully!" if ok
          else "[FAIL] Some files failed validation")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
