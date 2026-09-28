#!/usr/bin/env python3
"""
VideoNut TTS Engine  -  "The Narrator" voice agent's hands
==========================================================

Takes the Scriptwriter's `voice_script.md` and produces a finished, editor-ready
narration track plus a timecoded cue sheet.

    python tts_engine.py --project ./Projects/my_doc --dry-run
    python tts_engine.py --project ./Projects/my_doc --mode draft  --provider edge
    python tts_engine.py --project ./Projects/my_doc --mode final --provider elevenlabs

What it guarantees
------------------
1.  **Nothing unspeakable reaches the API.** Markdown, section markers and stage
    directions are stripped by `script_normalizer` before billing a single
    character.
2.  **Pauses are exact.** `(pause 2s)` becomes two seconds of real digital
    silence, identical on every provider, instead of a hopeful ellipsis.
3.  **You never pay twice for the same sentence.** Every chunk is content-hashed
    and cached under `.tts_cache/`; reruns after a small script edit only
    re-synthesise what actually changed.
4.  **Cost is known before it is spent.** `--dry-run` prints characters,
    estimated runtime and estimated spend, and exits without calling anything.
5.  **The editor gets timecodes.** `narration_cues.md` maps every [HOOK]/[MEAT]/
    [CTA] beat to an exact `HH:MM:SS.mmm` offset in the master track, which is
    what the Director's shot list needs to lock picture to voice.

Outputs (inside the project folder)
-----------------------------------
    voiceover_report.md                          <- human/EIC-facing summary
    assets/audio/narration/narration_full.mp3    <- the master narration track
    assets/audio/narration/narration_cues.md     <- section -> timecode map
    assets/audio/narration/narration_manifest.json
    assets/audio/narration/segments/NNN_SECTION.wav
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Make `tools.*` importable whether this runs as a script or a module.
VN_ROOT = Path(__file__).resolve().parent.parent.parent      # .../_video_nut
sys.path.insert(0, str(VN_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from tools.audio import providers as P
    from tools.audio import script_normalizer as SN
except ImportError:  # running directly from tools/audio/
    import providers as P            # type: ignore
    import script_normalizer as SN   # type: ignore

try:
    from tools.logging import audit_logger
    HAS_AUDIT = True
except ImportError:
    HAS_AUDIT = False


DEFAULT_CONFIG_PATH = VN_ROOT / "config.yaml"
AUDIO_SUBDIR = os.path.join("assets", "audio", "narration")


# ──────────────────────────────────────────────────────────────────────────────
# Config + secrets
# ──────────────────────────────────────────────────────────────────────────────


def load_dotenv(start: Optional[Path] = None) -> None:
    """
    Load KEY=VALUE pairs from the nearest .env files without adding a dependency.

    API keys belong in .env (gitignored), never in config.yaml (committed).
    """
    start = start or VN_ROOT
    candidates = [start / ".env", start.parent / ".env", Path.cwd() / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


def _coerce(value: str):
    raw = value.strip()
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')) and len(raw) >= 2:
        return raw[1:-1]
    low = raw.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _mini_yaml(text: str) -> Dict:
    """
    Minimal indentation-aware YAML reader for the subset config.yaml uses
    (nested maps, scalars, `- ` lists). Used only when PyYAML is unavailable so
    that VideoNut keeps working on air-gapped installs.
    """
    root: Dict = {}
    stack: List[Tuple[int, object]] = [(-1, root)]
    for rawline in text.splitlines():
        if not rawline.strip() or rawline.lstrip().startswith("#"):
            continue
        indent = len(rawline) - len(rawline.lstrip(" "))
        line = rawline.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root

        if line.startswith("- "):
            item = _coerce(line[2:])
            if isinstance(parent, list):
                parent.append(item)
            continue

        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.split(" #")[0].strip() if "#" in value else value.strip()

        if value == "":
            container: Dict = {}
            if isinstance(parent, dict):
                parent[key] = container
            stack.append((indent, container))
        else:
            if isinstance(parent, dict):
                parent[key] = _coerce(value)
    return root


def load_config(path: Optional[str] = None) -> Dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        return {}
    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except Exception:
        return _mini_yaml(text)


def voice_config(config: Dict) -> Dict:
    """Merge config.yaml `voice:` block over engine defaults."""
    defaults = {
        "enabled": True,
        "provider": "auto",
        "draft_provider": "auto",
        "model": "",
        "voice": "",
        "pace": 1.0,
        "stability": 0.45,
        "similarity": 0.8,
        "style_prompt": "Authoritative investigative documentary narrator. Measured, "
                        "credible, never theatrical. Let the facts carry the weight.",
        "output_format": "mp3",
        "sample_rate": 44100,
        "loudness_lufs": -14.0,
        "normalize_loudness": True,
        "max_chars_per_request": 0,          # 0 = use the provider's own cap
        "concurrency": 3,
        "retries": 3,
        "cache": True,
        "draft_pass": True,
        "cost_ceiling_usd": 25.0,
        "fallback_chain": [],
    }
    user = (config or {}).get("voice") or {}
    if isinstance(user, dict):
        for key, value in user.items():
            if value not in (None, ""):
                defaults[key] = value
    return defaults


# ──────────────────────────────────────────────────────────────────────────────
# ffmpeg helpers
# ──────────────────────────────────────────────────────────────────────────────


def find_binary(name: str) -> Optional[str]:
    found = shutil.which(name)
    if found:
        return found
    exe = f"{name}.exe" if os.name == "nt" else name
    for candidate in (VN_ROOT / "tools" / "bin" / exe, VN_ROOT / "bin" / exe):
        if candidate.exists():
            return str(candidate)
    return None


def run_ffmpeg(args: List[str], ffmpeg: str) -> Tuple[bool, str]:
    result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args],
                            capture_output=True)
    return result.returncode == 0, result.stderr.decode("utf-8", "ignore")


def probe_duration(path: str, ffprobe: Optional[str]) -> float:
    """
    Exact duration in seconds.

    Segments are normalized to PCM WAV before measurement, so the stdlib `wave`
    module gives an exact answer with zero dependencies. ffprobe is only needed
    for non-WAV inputs, which keeps the cue sheet accurate even on installs
    where ffprobe was never shipped alongside ffmpeg.
    """
    if not os.path.exists(path):
        return 0.0
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as handle:
                rate = handle.getframerate() or 1
                return round(handle.getnframes() / float(rate), 3)
        except (wave.Error, EOFError, OSError):
            pass
    if not ffprobe:
        return 0.0
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True,
    )
    try:
        return round(float(result.stdout.decode().strip()), 3)
    except (ValueError, AttributeError):
        return 0.0


def timecode(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# ──────────────────────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────────────────────


class VoiceEngine:
    def __init__(self, project_path: str, config: Dict, overrides: Optional[Dict] = None):
        self.project_path = os.path.abspath(project_path)
        self.project_name = os.path.basename(self.project_path.rstrip(os.sep))
        self.config = config or {}
        self.vcfg = voice_config(self.config)
        if overrides:
            self.vcfg.update({k: v for k, v in overrides.items() if v not in (None, "")})

        self.language = str(self.config.get("audio_language") or "English").strip() or "English"
        self.audio_dir = os.path.join(self.project_path, AUDIO_SUBDIR)
        self.segments_dir = os.path.join(self.audio_dir, "segments")
        self.cache_dir = os.path.join(self.project_path, ".tts_cache")
        self.ffmpeg = find_binary("ffmpeg")
        self.ffprobe = find_binary("ffprobe")
        self.warnings: List[str] = []

    # -- provider resolution -------------------------------------------------
    def resolve_provider(self, mode: str, requested: Optional[str]) -> Tuple[str, str]:
        name = (requested or "").strip().lower()
        if not name:
            key = "draft_provider" if mode == "draft" else "provider"
            name = str(self.vcfg.get(key) or "auto").strip().lower()
        if name in ("", "auto"):
            chain = self.vcfg.get("fallback_chain") or None
            if mode == "draft" and not chain:
                chain = ["edge", "piper", "sarvam", "gemini", "openai", "elevenlabs", "mock"]
            return P.resolve_auto_provider(self.language, chain)
        ready, why = P.get_provider(name, P.ProviderSettings(language=self.language)).check_ready()
        if not ready:
            fallback, reason = P.resolve_auto_provider(
                self.language, self.vcfg.get("fallback_chain") or None
            )
            self.warnings.append(f"Provider '{name}' is not usable: {why}")
            return fallback, f"'{name}' unavailable ({why}); {reason}"
        return name, f"using requested provider '{name}'"

    def build_settings(self, provider_name: str) -> P.ProviderSettings:
        per_provider = (self.vcfg.get("providers") or {}).get(provider_name, {}) \
            if isinstance(self.vcfg.get("providers"), dict) else {}
        return P.ProviderSettings(
            language=self.language,
            voice=str(per_provider.get("voice") or self.vcfg.get("voice") or ""),
            model=str(per_provider.get("model") or self.vcfg.get("model") or ""),
            pace=float(per_provider.get("pace") or self.vcfg.get("pace") or 1.0),
            stability=float(self.vcfg.get("stability") or 0.45),
            similarity=float(self.vcfg.get("similarity") or 0.8),
            style_prompt=str(self.vcfg.get("style_prompt") or ""),
        )

    # -- planning ------------------------------------------------------------
    def plan(self, script_path: str, provider_name: str) -> Tuple[List[SN.Segment], SN.ScriptStats, Dict]:
        profile = P.PROFILES[provider_name]
        segments, stats = SN.parse_voice_script(script_path, self.language)
        max_chars = int(self.vcfg.get("max_chars_per_request") or 0) or profile.max_chars
        chunks = SN.merge_segments(segments, max_chars, profile.dialect)

        billable = sum(len(SN.render_text(c, profile.dialect)) for c in chunks if c.kind == "speech")
        price = float(
            ((self.vcfg.get("pricing") or {}).get(provider_name)
             if isinstance(self.vcfg.get("pricing"), dict) else None)
            or profile.usd_per_1k_chars
        )
        estimate = {
            "provider": provider_name,
            "dialect": profile.dialect,
            "max_chars_per_request": max_chars,
            "requests": len([c for c in chunks if c.kind == "speech"]),
            "billable_characters": billable,
            "usd_per_1k_chars": price,
            "estimated_cost_usd": round(billable / 1000.0 * price, 4),
            "estimated_minutes": stats.estimated_minutes,
        }
        return chunks, stats, estimate

    # -- synthesis -----------------------------------------------------------
    def _cache_key(self, provider_name: str, settings: P.ProviderSettings, text: str, style: str) -> str:
        blob = "|".join([
            provider_name, settings.model, settings.voice, settings.language,
            f"{settings.pace}", f"{settings.stability}", f"{settings.similarity}",
            style, text,
        ])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]

    def _silence_file(self, seconds: float, target: str) -> bool:
        if not self.ffmpeg:
            return False
        rate = int(self.vcfg.get("sample_rate") or 44100)
        ok, err = run_ffmpeg(
            ["-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=mono",
             "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", target],
            self.ffmpeg,
        )
        if not ok:
            self.warnings.append(f"ffmpeg could not render {seconds}s of silence: {err[:160]}")
        return ok

    def _normalize_segment(self, source: str, target: str) -> bool:
        """Transcode any provider output to a uniform PCM WAV so concat is safe."""
        if not self.ffmpeg:
            return False
        rate = int(self.vcfg.get("sample_rate") or 44100)
        ok, err = run_ffmpeg(
            ["-i", source, "-ar", str(rate), "-ac", "1", "-c:a", "pcm_s16le", target],
            self.ffmpeg,
        )
        if not ok:
            self.warnings.append(f"ffmpeg could not normalize {os.path.basename(source)}: {err[:160]}")
        return ok

    def synthesize(
        self,
        chunks: List[SN.Segment],
        provider_name: str,
        settings: P.ProviderSettings,
        force: bool = False,
    ) -> List[Dict]:
        provider = P.get_provider(provider_name, settings)
        ready, why = provider.check_ready()
        if not ready:
            raise P.ProviderError(f"{provider_name} is not ready: {why}")

        os.makedirs(self.segments_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        profile = P.PROFILES[provider_name]
        ext = profile.audio_ext
        base_style = settings.style_prompt if profile.dialect == "style_prompt" else ""

        jobs: List[Dict] = []
        for chunk in chunks:
            if chunk.kind == "silence":
                jobs.append({"kind": "silence", "index": chunk.index, "section": chunk.section,
                             "seconds": chunk.seconds})
                continue
            text = SN.render_text(chunk, profile.dialect)
            style = SN.style_instruction(chunk, base_style) if profile.dialect == "style_prompt" else ""
            key = self._cache_key(provider_name, settings, text, style)
            jobs.append({
                "kind": "speech", "index": chunk.index, "section": chunk.section,
                "text": text, "style": style, "chars": len(text), "cache_key": key,
                "cache_path": os.path.join(self.cache_dir, f"{key}.{ext}"),
            })

        # Render silence locally (cheap, serial).
        for job in jobs:
            if job["kind"] != "silence":
                continue
            target = os.path.join(self.segments_dir, f"{job['index']:03d}_SILENCE.wav")
            job["ok"] = self._silence_file(job["seconds"], target)
            job["file"] = target if job["ok"] else ""
            job["cache_hit"] = False

        speech_jobs = [j for j in jobs if j["kind"] == "speech"]
        workers = max(1, int(self.vcfg.get("concurrency") or 3))
        retries = max(1, int(self.vcfg.get("retries") or 3))
        use_cache = bool(self.vcfg.get("cache", True)) and not force

        def render(job: Dict) -> Dict:
            target = os.path.join(
                self.segments_dir,
                f"{job['index']:03d}_{re.sub(r'[^A-Za-z0-9]+', '', job['section'])[:12] or 'SPEECH'}.{ext}",
            )
            if use_cache and os.path.exists(job["cache_path"]) and os.path.getsize(job["cache_path"]) > 0:
                shutil.copyfile(job["cache_path"], target)
                job.update({"ok": True, "file": target, "cache_hit": True})
                return job
            try:
                P.retry(lambda: provider.synthesize(job["text"], job["style"], job["cache_path"]),
                        attempts=retries)
                shutil.copyfile(job["cache_path"], target)
                job.update({"ok": True, "file": target, "cache_hit": False})
            except Exception as exc:
                job.update({"ok": False, "file": "", "cache_hit": False, "error": str(exc)})
            return job

        total = len(speech_jobs)
        done = 0
        if total:
            print(f"[VOICE] Synthesizing {total} chunk(s) with '{provider_name}' "
                  f"(voice={settings.voice or 'default'}, model={settings.model or 'default'})")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for finished in concurrent.futures.as_completed([pool.submit(render, j) for j in speech_jobs]):
                job = finished.result()
                done += 1
                flag = "cache" if job.get("cache_hit") else ("ok" if job.get("ok") else "FAIL")
                print(f"  [{done}/{total}] #{job['index']:03d} {job['section']:<10} "
                      f"{job['chars']:>5} chars  [{flag}]")
                if not job.get("ok"):
                    print(f"        -> {job.get('error', 'unknown error')}")

        return sorted(jobs, key=lambda j: j["index"])

    # -- assembly ------------------------------------------------------------
    def stitch(self, jobs: List[Dict], out_basename: str) -> Tuple[Optional[str], List[Dict]]:
        """Normalize every segment, concatenate, loudness-normalize, and measure."""
        usable = [j for j in jobs if j.get("ok") and j.get("file")]
        if not usable:
            self.warnings.append("No renderable segments - nothing to stitch.")
            return None, []
        if not self.ffmpeg:
            self.warnings.append(
                "ffmpeg not found: segments were rendered but not stitched into a master track. "
                "Install ffmpeg or drop it in _video_nut/tools/bin/."
            )
            return None, usable

        work = tempfile.mkdtemp(prefix="vn_tts_", dir=self.cache_dir)
        try:
            normalized: List[str] = []
            for job in usable:
                norm = os.path.join(work, f"{job['index']:03d}.wav")
                if self._normalize_segment(job["file"], norm):
                    normalized.append(norm)
                    job["duration"] = probe_duration(norm, self.ffprobe)
                else:
                    job["ok"] = False
                    job["error"] = "normalization failed"

            normalized = [n for n in normalized if os.path.exists(n)]
            if not normalized:
                self.warnings.append("All segments failed normalization.")
                return None, usable

            list_file = os.path.join(work, "concat.txt")
            with open(list_file, "w", encoding="utf-8") as handle:
                for path in normalized:
                    handle.write(f"file '{path}'\n")

            fmt = str(self.vcfg.get("output_format") or "mp3").lower()
            master = os.path.join(self.audio_dir, f"{out_basename}.{fmt}")
            args = ["-f", "concat", "-safe", "0", "-i", list_file]
            if self.vcfg.get("normalize_loudness", True):
                lufs = float(self.vcfg.get("loudness_lufs") or -14.0)
                args += ["-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11"]
            if fmt == "mp3":
                args += ["-c:a", "libmp3lame", "-b:a", "192k"]
            elif fmt == "wav":
                args += ["-c:a", "pcm_s16le"]
            args += ["-ar", str(int(self.vcfg.get("sample_rate") or 44100)), "-ac", "1", master]

            ok, err = run_ffmpeg(args, self.ffmpeg)
            if not ok:
                self.warnings.append(f"ffmpeg concat failed: {err[:300]}")
                return None, usable

            # Accumulate start offsets for the cue sheet.
            cursor = 0.0
            for job in usable:
                if not job.get("ok"):
                    continue
                job["start"] = round(cursor, 3)
                cursor += float(job.get("duration") or 0.0)
                job["end"] = round(cursor, 3)
            return master, usable
        finally:
            shutil.rmtree(work, ignore_errors=True)

    # -- reporting -----------------------------------------------------------
    def write_outputs(
        self,
        jobs: List[Dict],
        master: Optional[str],
        stats: SN.ScriptStats,
        estimate: Dict,
        provider_name: str,
        settings: P.ProviderSettings,
        mode: str,
        script_path: str,
    ) -> Dict:
        os.makedirs(self.audio_dir, exist_ok=True)
        spoken = [j for j in jobs if j["kind"] == "speech"]
        failures = [j for j in jobs if not j.get("ok")]
        actual_seconds = round(sum(float(j.get("duration") or 0.0) for j in jobs if j.get("ok")), 2)
        billed = sum(j.get("chars", 0) for j in spoken if not j.get("cache_hit"))
        spend = round(billed / 1000.0 * estimate["usd_per_1k_chars"], 4)

        manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": self.project_name,
            "mode": mode,
            "source_script": os.path.relpath(script_path, self.project_path),
            "language": self.language,
            "provider": provider_name,
            "model": settings.model or "provider default",
            "voice": settings.voice or "provider default",
            "master_track": os.path.relpath(master, self.project_path) if master else None,
            "duration_seconds": actual_seconds,
            "duration_timecode": timecode(actual_seconds),
            "target_duration_minutes": self.config.get("target_duration"),
            "words": stats.words,
            "billable_characters_this_run": billed,
            "estimated_cost_usd_this_run": spend,
            "cache_hits": sum(1 for j in spoken if j.get("cache_hit")),
            "segments": [
                {
                    "index": j["index"],
                    "kind": j["kind"],
                    "section": j["section"],
                    "start": j.get("start"),
                    "end": j.get("end"),
                    "duration": j.get("duration"),
                    "chars": j.get("chars", 0),
                    "cache_hit": j.get("cache_hit", False),
                    "ok": bool(j.get("ok")),
                    "error": j.get("error"),
                    "file": os.path.relpath(j["file"], self.project_path) if j.get("file") else None,
                    "text": (j.get("text") or "")[:400],
                }
                for j in jobs
            ],
            "warnings": self.warnings + list(stats.warnings),
        }
        manifest_path = os.path.join(self.audio_dir, "narration_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

        # ---- cue sheet: what the editor and the Director actually need ----
        cues_path = os.path.join(self.audio_dir, "narration_cues.md")
        lines = [
            f"# Narration Cue Sheet - {self.project_name}",
            "",
            f"> Master track: `{manifest['master_track'] or 'NOT BUILT'}`  ",
            f"> Runtime: **{manifest['duration_timecode']}** "
            f"({actual_seconds / 60:.2f} min) | Target: {self.config.get('target_duration', '?')} min  ",
            f"> Voice: {provider_name} / {manifest['voice']} / {manifest['model']} | "
            f"Language: {self.language} | Mode: {mode}",
            "",
            "Drop `narration_full` on the timeline at 00:00:00.000 and these timecodes line up exactly.",
            "",
            "| # | Section | Start | End | Length | Narration |",
            "|---|---------|-------|-----|--------|-----------|",
        ]
        for job in jobs:
            if not job.get("ok"):
                continue
            preview = (job.get("text") or "").replace("|", "\\|")
            preview = (preview[:90] + "...") if len(preview) > 90 else preview
            label = "(silence)" if job["kind"] == "silence" else preview
            lines.append(
                f"| {job['index']:03d} | {job['section']} | {timecode(job.get('start', 0))} | "
                f"{timecode(job.get('end', 0))} | {float(job.get('duration') or 0):.2f}s | {label} |"
            )
        lines.append("")
        lines.append("## Section boundaries")
        lines.append("")
        lines.append("| Section | First frame | Last frame | Duration |")
        lines.append("|---------|-------------|------------|----------|")
        section_bounds: Dict[str, List[float]] = {}
        for job in jobs:
            if not job.get("ok") or job.get("start") is None:
                continue
            bounds = section_bounds.setdefault(job["section"], [job["start"], job["end"]])
            bounds[0] = min(bounds[0], job["start"])
            bounds[1] = max(bounds[1], job["end"])
        for section, (start, end) in section_bounds.items():
            lines.append(f"| {section} | {timecode(start)} | {timecode(end)} | {end - start:.2f}s |")
        with open(cues_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

        # ---- agent-facing report at the project root (EIC reads this) ----
        target_minutes = float(self.config.get("target_duration") or 0)
        drift = ""
        if target_minutes:
            delta = (actual_seconds / 60.0) - target_minutes
            pct = (delta / target_minutes) * 100 if target_minutes else 0
            verdict = "within tolerance" if abs(pct) <= 10 else "OUT OF TOLERANCE (>10%)"
            drift = (f"- **Duration vs target:** {actual_seconds / 60:.2f} min vs "
                     f"{target_minutes:.0f} min ({pct:+.1f}%) - {verdict}\n")

        report = [
            f"# Voiceover Report - {self.project_name}",
            "",
            f"**Generated:** {manifest['generated_at']}  ",
            f"**Mode:** {mode}  |  **Provider:** `{provider_name}`  |  "
            f"**Model:** `{manifest['model']}`  |  **Voice:** `{manifest['voice']}`  ",
            f"**Language:** {self.language}",
            "",
            "## Result",
            "",
            f"- **Master track:** `{manifest['master_track'] or 'NOT BUILT - see warnings'}`",
            f"- **Runtime:** {manifest['duration_timecode']} ({actual_seconds / 60:.2f} min)",
            drift.rstrip("\n") if drift else "",
            f"- **Words narrated:** {stats.words}",
            f"- **Chunks:** {len(spoken)} speech + "
            f"{len([j for j in jobs if j['kind'] == 'silence'])} silence",
            f"- **Cache hits:** {manifest['cache_hits']}/{len(spoken)} "
            f"(characters actually billed this run: {billed})",
            f"- **Estimated spend this run:** ${spend:.4f} "
            f"(at ${estimate['usd_per_1k_chars']:.4f}/1k chars)",
            f"- **Cue sheet:** `{os.path.relpath(cues_path, self.project_path)}`",
            f"- **Manifest:** `{os.path.relpath(manifest_path, self.project_path)}`",
            "",
        ]
        if failures:
            report += ["## ❌ Failed segments", ""]
            for job in failures:
                report.append(f"- `#{job['index']:03d}` [{job['section']}] {job.get('error', 'unknown')}")
            report.append("")
        all_warnings = manifest["warnings"]
        if all_warnings:
            report += ["## ⚠️ Warnings", ""] + [f"- {w}" for w in all_warnings] + [""]
        report += [
            "## Next steps",
            "",
            "1. Listen to the master track end-to-end before locking picture.",
            "2. Hand `narration_cues.md` to the Director / editor so shots match voice beats.",
            "3. If the runtime drifts more than 10% from target, adjust the script "
            "(not the playback speed) and re-run `/narrator`.",
            "",
        ]
        report_path = os.path.join(self.project_path, "voiceover_report.md")
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(line for line in report if line is not None))

        if HAS_AUDIT:
            try:
                audit_logger.log_action(
                    project_path=self.project_path,
                    category="download",
                    action=f"Generated narration ({mode}) via {provider_name}",
                    local_path=manifest["master_track"] or "",
                    status="ok" if master and not failures else "failed",
                    details=f"{stats.words} words, {actual_seconds}s, ${spend:.4f}",
                )
            except Exception:
                pass

        return manifest


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def resolve_script(project_path: str, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit if os.path.exists(explicit) else None
    for name in ("voice_script.md", "narrative_script.md"):
        candidate = os.path.join(project_path, name)
        if os.path.exists(candidate):
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VideoNut TTS engine: turn voice_script.md into a narration track."
    )
    parser.add_argument("--project", required=True, help="Path to the project folder")
    parser.add_argument("--script", help="Override the script path (default: voice_script.md)")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--provider", help="elevenlabs | sarvam | gemini | openai | piper | edge | mock | auto")
    parser.add_argument("--voice", help="Provider voice id / speaker name")
    parser.add_argument("--model", help="Provider model id")
    parser.add_argument("--language", help="Override audio_language from config.yaml")
    parser.add_argument("--mode", default="final", choices=["draft", "final"],
                        help="draft = cheap/local timing pass; final = production render")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost and runtime, call nothing")
    parser.add_argument("--force", action="store_true", help="Ignore the cache and re-synthesize")
    parser.add_argument("--yes", action="store_true", help="Skip the spend confirmation prompt")
    parser.add_argument("--json", action="store_true", help="Print the manifest as JSON")
    args = parser.parse_args()

    load_dotenv()

    if not os.path.isdir(args.project):
        print(f"[FAIL] Project directory does not exist: {args.project}")
        return 1

    config = load_config(args.config)
    if args.language:
        config["audio_language"] = args.language

    engine = VoiceEngine(args.project, config, overrides={
        "voice": args.voice, "model": args.model,
    })

    if not engine.vcfg.get("enabled", True):
        print("[SKIP] voice.enabled is false in config.yaml - narration stage disabled.")
        return 0

    script_path = resolve_script(engine.project_path, args.script)
    if not script_path:
        print("[FAIL] No voice_script.md (or narrative_script.md) found in the project folder.")
        print("       Run /scriptwriter first - the Narrator needs a script to read.")
        return 1

    provider_name, why = engine.resolve_provider(args.mode, args.provider)
    print(f"[VOICE] {why}")
    for warning in engine.warnings:
        print(f"  [WARN] {warning}")

    try:
        chunks, stats, estimate = engine.plan(script_path, provider_name)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("-" * 62)
    print(f"  Script          : {os.path.relpath(script_path, engine.project_path)}")
    print(f"  Language        : {engine.language}")
    print(f"  Words           : {stats.words}")
    print(f"  Requests        : {estimate['requests']} "
          f"(max {estimate['max_chars_per_request']} chars each)")
    print(f"  Billable chars  : {estimate['billable_characters']}")
    print(f"  Est. runtime    : {estimate['estimated_minutes']} min "
          f"(target {config.get('target_duration', '?')} min)")
    print(f"  Est. cost       : ${estimate['estimated_cost_usd']:.4f}")
    for warning in stats.warnings:
        print(f"  [WARN] {warning}")
    print("-" * 62)

    if args.dry_run:
        print("[DRY-RUN] No audio was generated and nothing was billed.")
        if args.json:
            print(json.dumps({"estimate": estimate, "stats": stats.to_dict()}, indent=2))
        return 0

    ceiling = float(engine.vcfg.get("cost_ceiling_usd") or 0)
    if ceiling and estimate["estimated_cost_usd"] > ceiling:
        print(f"[STOP] Estimated ${estimate['estimated_cost_usd']:.2f} exceeds "
              f"voice.cost_ceiling_usd (${ceiling:.2f}).")
        print("       Raise the ceiling in config.yaml, or use --mode draft / --provider edge.")
        return 2

    if estimate["estimated_cost_usd"] > 0 and not args.yes and sys.stdin.isatty():
        answer = input(f"Proceed and spend about ${estimate['estimated_cost_usd']:.2f}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("[ABORT] Cancelled by user.")
            return 130

    settings = engine.build_settings(provider_name)
    try:
        jobs = engine.synthesize(chunks, provider_name, settings, force=args.force)
    except P.ProviderError as exc:
        print(f"[FAIL] {exc}")
        return 1

    basename = "narration_full" if args.mode == "final" else "narration_draft"
    master, _ = engine.stitch(jobs, basename)
    manifest = engine.write_outputs(
        jobs, master, stats, estimate, provider_name, settings, args.mode, script_path
    )

    failed = [j for j in jobs if not j.get("ok")]
    print("-" * 62)
    if master:
        print(f"[OK] Master narration: {master}")
        print(f"     Runtime {manifest['duration_timecode']} | "
              f"cue sheet: {AUDIO_SUBDIR}/narration_cues.md")
    else:
        print("[WARN] Segments rendered but no master track was produced (see warnings).")
    print(f"     Report: voiceover_report.md | spent about "
          f"${manifest['estimated_cost_usd_this_run']:.4f} this run")
    for warning in manifest["warnings"]:
        print(f"     [WARN] {warning}")

    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))

    return 1 if failed or not master else 0


if __name__ == "__main__":
    sys.exit(main())
