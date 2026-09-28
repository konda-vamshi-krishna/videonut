#!/usr/bin/env python3
"""
VideoNut Narration Validator
============================

Quality gate for the Narrator (voiceover) stage. Runs after `tts_engine.py` and
answers the only questions that matter before a track goes on a timeline:

  1. Does the master track actually exist and contain audio?
  2. Did every segment render, or did the pipeline quietly skip lines?
  3. Is the runtime within tolerance of `target_duration` in config.yaml?
  4. Is the track silent / clipped / obviously broken?
  5. Does the cue sheet cover every section the script declared?

Exit code 0 = pass (the orchestrator continues), 1 = fail (gate blocks).

    python audio_validator.py ./Projects/my_doc
    python audio_validator.py ./Projects/my_doc --tolerance 15 --json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

MANIFEST_REL = os.path.join("assets", "audio", "narration", "narration_manifest.json")
MIN_TRACK_BYTES = 4096


def _find_ffprobe():
    found = shutil.which("ffprobe")
    if found:
        return found
    root = Path(__file__).resolve().parent.parent.parent
    exe = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    for candidate in (root / "tools" / "bin" / exe, root / "bin" / exe):
        if candidate.exists():
            return str(candidate)
    return None


def _measure(path: str):
    """(duration_seconds, mean_volume_db). Either may be None when tools are absent."""
    duration = None
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as handle:
                duration = handle.getnframes() / float(handle.getframerate() or 1)
        except Exception:
            duration = None

    ffprobe = _find_ffprobe()
    if duration is None and ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True,
        )
        try:
            duration = float(result.stdout.decode().strip())
        except (ValueError, AttributeError):
            duration = None

    mean_db = None
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
        )
        for line in result.stderr.decode("utf-8", "ignore").splitlines():
            if "mean_volume:" in line:
                try:
                    mean_db = float(line.split("mean_volume:")[1].split("dB")[0].strip())
                except (ValueError, IndexError):
                    pass
    return duration, mean_db


def validate_narration(project_path: str, tolerance_pct: float = 10.0, target_minutes=None):
    result = {"passed": True, "checks": [], "errors": [], "warnings": [], "summary": {}}

    def check(name, ok, detail, fatal=True):
        result["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            (result["errors"] if fatal else result["warnings"]).append(f"{name}: {detail}")
            if fatal:
                result["passed"] = False
        return ok

    manifest_path = os.path.join(project_path, MANIFEST_REL)
    if not check("manifest exists", os.path.exists(manifest_path),
                 f"{MANIFEST_REL} not found - run /narrator (tts_engine.py) first"):
        return result

    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        check("manifest readable", False, f"could not parse manifest: {exc}")
        return result

    result["summary"] = {
        "provider": manifest.get("provider"),
        "voice": manifest.get("voice"),
        "mode": manifest.get("mode"),
        "language": manifest.get("language"),
        "words": manifest.get("words"),
    }

    # 1. master track present and non-trivial
    rel_track = manifest.get("master_track")
    track = os.path.join(project_path, rel_track) if rel_track else None
    if not check("master track built", bool(track) and os.path.exists(track),
                 "no master narration track was produced"):
        return result
    size = os.path.getsize(track)
    check("master track non-empty", size > MIN_TRACK_BYTES,
          f"{os.path.basename(track)} is only {size} bytes")

    # 2. every segment rendered
    segments = manifest.get("segments") or []
    failed = [s for s in segments if not s.get("ok")]
    check("all segments rendered", not failed,
          f"{len(failed)} of {len(segments)} segments failed: "
          + ", ".join(f"#{s['index']}" for s in failed[:6]))

    # 3. runtime vs target
    duration, mean_db = _measure(track)
    duration = duration or manifest.get("duration_seconds") or 0
    result["summary"]["duration_seconds"] = round(duration, 2)
    result["summary"]["mean_volume_db"] = mean_db
    target = target_minutes if target_minutes is not None else manifest.get("target_duration_minutes")
    try:
        target = float(target or 0)
    except (TypeError, ValueError):
        target = 0.0
    if target > 0:
        drift_pct = ((duration / 60.0) - target) / target * 100.0
        result["summary"]["drift_pct"] = round(drift_pct, 1)
        check(
            "runtime within tolerance",
            abs(drift_pct) <= tolerance_pct,
            f"{duration / 60:.2f} min vs target {target:.0f} min ({drift_pct:+.1f}%, "
            f"tolerance +/-{tolerance_pct:.0f}%) - fix the script, not the playback speed",
        )
    else:
        result["warnings"].append(
            "target_duration is not set in config.yaml - runtime could not be validated."
        )

    # 4. not silent, not clipped (the `mock` provider is silent by design)
    if manifest.get("provider") == "mock":
        result["warnings"].append(
            "provider=mock: loudness checks skipped (mock renders deterministic silence)."
        )
    elif mean_db is not None:
        check("track is not silent", mean_db > -50.0,
              f"mean volume {mean_db} dB suggests a silent or broken render")
        check("track is not clipped", mean_db < -6.0,
              f"mean volume {mean_db} dB is hot; expect clipping on loud beats", fatal=False)
    elif mean_db is None:
        result["warnings"].append("ffmpeg not available - loudness checks were skipped.")

    # 5. cue sheet covers the script's sections
    cues_path = os.path.join(project_path, "assets", "audio", "narration", "narration_cues.md")
    check("cue sheet exists", os.path.exists(cues_path),
          "narration_cues.md missing - the editor has no timecode map", fatal=False)
    sections = {s.get("section") for s in segments if s.get("ok")}
    check("sections detected", bool(sections - {"UNSECTIONED", None}),
          "no [HOOK]/[MEAT]/[CTA] sections in the narration - timing map will be flat",
          fatal=False)

    for warning in manifest.get("warnings") or []:
        result["warnings"].append(f"engine: {warning}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated narration audio.")
    parser.add_argument("project", help="Path to the project folder")
    parser.add_argument("--tolerance", type=float, default=10.0,
                        help="Allowed runtime drift vs target_duration, in percent")
    parser.add_argument("--target-minutes", type=float, default=None,
                        help="Override target duration from the manifest")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if not os.path.isdir(args.project):
        print(f"[FAIL] Project directory does not exist: {args.project}")
        return 1

    result = validate_narration(args.project, args.tolerance, args.target_minutes)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["passed"] else 1

    print("[SCAN] Narration validation")
    print("-" * 56)
    for item in result["checks"]:
        icon = "[OK]  " if item["ok"] else "[FAIL]"
        detail = "ok" if item["ok"] else (item["detail"] or "failed")
        print(f"  {icon} {item['check']}: {detail}")
    summary = result["summary"]
    if summary:
        print("-" * 56)
        print(f"  provider={summary.get('provider')} voice={summary.get('voice')} "
              f"mode={summary.get('mode')} words={summary.get('words')}")
        print(f"  duration={summary.get('duration_seconds')}s "
              f"drift={summary.get('drift_pct', 'n/a')}% "
              f"mean_volume={summary.get('mean_volume_db', 'n/a')}dB")
    for warning in result["warnings"]:
        print(f"  [WARN] {warning}")
    print("-" * 56)
    print("[OK] Narration validation PASSED" if result["passed"]
          else "[FAIL] Narration validation FAILED")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
