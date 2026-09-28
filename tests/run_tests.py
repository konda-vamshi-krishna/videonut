#!/usr/bin/env python3
"""
VideoNut regression suite.

The repository had no tests before v1.5. This suite is intentionally
dependency-free (stdlib only) and safe to run anywhere: every test renders
audio with the `mock` TTS provider, so it never touches the network and never
spends money.

    python tests/run_tests.py            # run everything
    python tests/run_tests.py -v         # show each assertion
    python tests/run_tests.py voice      # run only tests whose name contains "voice"

Exit code 0 = all green.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VN = os.path.join(REPO_ROOT, "_video_nut")
AUDIO = os.path.join(VN, "tools", "audio")
VALIDATORS = os.path.join(VN, "tools", "validators")

sys.path.insert(0, AUDIO)

VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv
FILTER = next((a for a in sys.argv[1:] if not a.startswith("-")), None)

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    GREEN = RED = YELLOW = DIM = RESET = ""

_REGISTRY = []
_results = {"pass": 0, "fail": 0, "skip": 0}


def test(name):
    def deco(fn):
        _REGISTRY.append((name, fn))
        return fn
    return deco


class Skip(Exception):
    pass


def eq(actual, expected, what):
    if actual != expected:
        raise AssertionError(f"{what}: expected {expected!r}, got {actual!r}")
    if VERBOSE:
        print(f"    {DIM}. {what} == {expected!r}{RESET}")


def ok(cond, what):
    if not cond:
        raise AssertionError(what)
    if VERBOSE:
        print(f"    {DIM}. {what}{RESET}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SCRIPT = """# Sample Voice Script
**Topic:** The eight pages nobody read
**Target Duration:** 2 minutes

[HOOK]
(modulation pitch: low speed: slow tone: grave) In 2017, eight researchers published a paper. (end modulation)
(pause 2s)
(emphasis) Eight pages. (end emphasis) That is all it took.

[BRIDGE]
To understand what happened next, you have to understand what everyone missed. (pause 1s)

[MEAT]
The paper was called Attention Is All You Need.
It described an architecture the authors named the Transformer.
(pause 1.5s) (modulation pitch: high speed: fast tone: questioning) So why did nobody see it coming? (end modulation)
The answer is mundane. It was filed under machine translation.

[HUMAN BEAT]
(breath)
One of the authors later described the moment the scale became undeniable.

[VERDICT]
(modulation pitch: low speed: slow tone: grave) They did not lose because the research was weak. (end modulation)
(pause 2s)

[CTA]
(modulation tone: excited) If this changed how you think, subscribe. (end modulation)

**Total Words:** 140
"""


def make_project(tmp, script=SAMPLE_SCRIPT):
    path = os.path.join(tmp, "proj")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "voice_script.md"), "w", encoding="utf-8") as f:
        f.write(script)
    return path


def run(args, **kw):
    return subprocess.run(args, capture_output=True, encoding="utf-8",
                          errors="replace", **kw)


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# 1. Script normalizer
# ---------------------------------------------------------------------------

@test("normalizer: parses sections, cues and pauses")
def t_normalizer_basic():
    from script_normalizer import parse_voice_text

    segments, stats = parse_voice_text(SAMPLE_SCRIPT)
    sections = {s.section for s in segments}
    for marker in ("HOOK", "BRIDGE", "MEAT", "HUMAN BEAT", "VERDICT", "CTA"):
        ok(marker in sections, f"section {marker} detected")
    ok(80 < stats.words < 200, f"word count is plausible ({stats.words})")
    ok(stats.silence_segments >= 4, f"pauses captured ({stats.silence_segments})")
    ok(abs(stats.silence_seconds - 6.5) < 0.01,
       f"total silence is 6.5s (got {stats.silence_seconds})")
    for cue in ("pause", "emphasis", "grave", "questioning", "excited", "breath"):
        ok(cue in stats.cues_found, f"cue '{cue}' recognised")


@test("normalizer: front matter above the first marker is never narrated")
def t_normalizer_frontmatter():
    from script_normalizer import parse_voice_text

    segments, stats = parse_voice_text(SAMPLE_SCRIPT)
    spoken = " ".join(s.text for s in segments if s.kind == "speech").lower()
    ok("target duration" not in spoken, "metadata line is not spoken")
    ok("sample voice script" not in spoken, "title is not spoken")
    ok("total words" not in spoken, "footer is not spoken")
    ok(any("Skipped" in w for w in stats.warnings),
       f"skipped front matter is reported ({stats.warnings})")


@test("normalizer: a cue that opens and closes on one line still applies")
def t_normalizer_inline_span():
    # Regression: cues used to be line-level flags, so `(emphasis) X (end emphasis)`
    # was set and cleared before the text was emitted - silently dropping the cue.
    from script_normalizer import parse_voice_text

    segments, _ = parse_voice_text("[HOOK]\n(emphasis) Eight pages. (end emphasis) That is all.\n")
    emphasized = [s for s in segments if "emphasis" in s.cues]
    ok(emphasized, "inline (emphasis) span survived tokenization")
    ok(any("Eight pages" in s.text for s in emphasized),
       "the emphasized words are the ones carrying the cue")
    plain = [s for s in segments if s.kind == "speech" and "emphasis" not in s.cues]
    ok(any("That is all" in s.text for s in plain),
       "text after (end emphasis) is no longer emphasized")


@test("normalizer: a standalone cue line carries onto the next sentence")
def t_normalizer_pending_cue():
    from script_normalizer import parse_voice_text

    segments, _ = parse_voice_text("[HOOK]\n(breath)\nHe paused before answering.\n")
    carriers = [s for s in segments if "breath" in s.cues]
    ok(carriers, "(breath) on its own line is not dropped")
    ok(any("paused before answering" in s.text for s in carriers),
       "the cue attaches to the following sentence")


@test("normalizer: markdown chrome and stray visual directions never reach the API")
def t_normalizer_strips_noise():
    from script_normalizer import parse_voice_text

    raw = ("[HOOK]\n"
           "## A heading nobody should hear\n"
           "[Visual: archival footage of the office]\n"
           "**Bold** narration with _emphasis_ markup and a [link](https://x.com).\n")
    segments, _ = parse_voice_text(raw)
    spoken = " ".join(s.text for s in segments if s.kind == "speech")
    ok("heading nobody" not in spoken, "markdown heading dropped")
    ok("archival footage" not in spoken, "visual direction dropped")
    ok("https" not in spoken, "link target dropped")
    ok("**" not in spoken and "_" not in spoken, "markdown emphasis characters stripped")


# ---------------------------------------------------------------------------
# 2. Providers
# ---------------------------------------------------------------------------

@test("providers: every registered provider reports readiness without crashing")
def t_provider_registry():
    from providers import REGISTRY, available_providers

    for expected in ("elevenlabs", "sarvam", "gemini", "openai", "piper", "edge", "mock"):
        ok(expected in REGISTRY, f"provider '{expected}' is registered")

    status = available_providers("English")
    eq(len(status), len(REGISTRY), "readiness probe covers every provider")
    for name, (ready, reason) in status.items():
        ok(isinstance(ready, bool), f"{name}: readiness is a bool")
        ok(bool(reason), f"{name}: readiness has a human-readable reason")


@test("providers: mock is always ready so the pipeline never hard-blocks")
def t_provider_mock_ready():
    from providers import available_providers

    ready, _ = available_providers("English")["mock"]
    ok(ready, "mock provider is ready with no credentials")


@test("providers: Indic scripts route to Sarvam ahead of ElevenLabs")
def t_provider_indic_routing():
    from providers import is_indic, resolve_auto_provider

    for lang in ("Hindi", "Telugu", "Tamil", "hi-IN", "Kannada"):
        ok(is_indic(lang), f"{lang} is detected as Indic")
    for lang in ("English", "en-US", "Spanish"):
        ok(not is_indic(lang), f"{lang} is not treated as Indic")

    # With no API keys present, auto-resolution must still terminate on a free
    # provider rather than raising.
    name, reason = resolve_auto_provider("Hindi")
    ok(name in ("sarvam", "elevenlabs", "gemini", "edge", "piper", "mock"),
       f"Hindi resolved to a known provider ({name})")
    ok(bool(reason), "resolution explains itself")


@test("providers: chunk limits respect each vendor's real per-request cap")
def t_provider_chunk_limits():
    from providers import PROFILES

    caps = {
        "elevenlabs": 3000,   # eleven_v3 documented safe limit
        "sarvam": 2500,       # hard API limit
    }
    for name, expected_max in caps.items():
        profile = PROFILES[name]
        ok(profile.max_chars <= expected_max,
           f"{name} max_chars ({profile.max_chars}) is within the vendor limit ({expected_max})")


# ---------------------------------------------------------------------------
# 3. TTS engine (end to end, mock provider)
# ---------------------------------------------------------------------------

@test("engine: dry run prices the job without writing audio")
def t_engine_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        r = run([sys.executable, os.path.join(AUDIO, "tts_engine.py"),
                 "--project", proj, "--provider", "mock", "--dry-run"])
        eq(r.returncode, 0, "dry run exits 0")
        ok("Billable chars" in r.stdout, "dry run reports billable characters")
        ok("Est. cost" in r.stdout, "dry run reports an estimated cost")
        ok(not os.path.exists(os.path.join(proj, "assets", "audio", "narration")),
           "dry run wrote no audio")


@test("engine: final render produces a master track, segments and a manifest")
def t_engine_render():
    if not have_ffmpeg():
        raise Skip("ffmpeg not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        r = run([sys.executable, os.path.join(AUDIO, "tts_engine.py"),
                 "--project", proj, "--provider", "mock", "--mode", "final", "--yes"])
        eq(r.returncode, 0, f"render exits 0 (stderr: {r.stderr[:300]})")

        narration = os.path.join(proj, "assets", "audio", "narration")
        master = os.path.join(narration, "narration_full.mp3")
        ok(os.path.exists(master), "narration_full.mp3 exists")
        ok(os.path.getsize(master) > 1000, "master track is not a stub")
        ok(os.path.exists(os.path.join(narration, "narration_cues.md")), "cue sheet written")
        ok(os.path.exists(os.path.join(proj, "voiceover_report.md")), "EIC report written")

        with open(os.path.join(narration, "narration_manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        ok(manifest["duration_seconds"] > 30, "manifest records a real runtime")
        eq(manifest["provider"], "mock", "manifest records the provider used")
        segs = manifest["segments"]
        ok(len(segs) >= 10, f"segments recorded ({len(segs)})")

        # Timeline must be contiguous: every segment starts where the last ended.
        cursor = 0.0
        for seg in segs:
            ok(abs(seg["start"] - cursor) < 0.02,
               f"segment {seg['index']} starts at the previous end")
            cursor = seg["end"]
        ok(abs(cursor - manifest["duration_seconds"]) < 0.25,
           "last segment ends at the reported total duration")


@test("engine: identical text is billed once (cache hit on re-render)")
def t_engine_cache():
    if not have_ffmpeg():
        raise Skip("ffmpeg not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        cmd = [sys.executable, os.path.join(AUDIO, "tts_engine.py"),
               "--project", proj, "--provider", "mock", "--mode", "final", "--yes"]
        first = run(cmd)
        eq(first.returncode, 0, "first render succeeds")
        second = run(cmd)
        eq(second.returncode, 0, "second render succeeds")
        ok("[cache]" in second.stdout, "second render reports cache hits")
        ok(second.stdout.count("[cache]") >= first.stdout.count("[new]"),
           "every chunk came from cache the second time")


@test("engine: pauses become real silence, not a shorter track")
def t_engine_silence():
    if not have_ffmpeg():
        raise Skip("ffmpeg not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        run([sys.executable, os.path.join(AUDIO, "tts_engine.py"),
             "--project", proj, "--provider", "mock", "--mode", "final", "--yes"])
        narration = os.path.join(proj, "assets", "audio", "narration")
        with open(os.path.join(narration, "narration_manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        silences = [s for s in manifest["segments"] if s["kind"] == "silence"]
        ok(len(silences) >= 4, f"silence segments present ({len(silences)})")
        total = sum(s["end"] - s["start"] for s in silences)
        ok(abs(total - 6.5) < 0.2, f"silence totals the scripted 6.5s (got {total:.2f})")


# ---------------------------------------------------------------------------
# 4. Validators
# ---------------------------------------------------------------------------

@test("validator: a clean voice script passes the 'voice' gate")
def t_validate_voice_ok():
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        r = run([sys.executable, os.path.join(VALIDATORS, "output_validator.py"),
                 "voice", os.path.join(proj, "voice_script.md")])
        eq(r.returncode, 0, f"voice gate passes (out: {r.stdout[:300]})")


@test("validator: the 'voice' gate rejects URLs and visual directions")
def t_validate_voice_rejects():
    bad = """[HOOK]
Go read https://example.com/paper for the details.
[SHOT: wide drone shot over the campus]
[B-ROLL: server racks]
[CUT TO: interview]
[MEAT]
Some narration.
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "voice_script.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(bad)
        r = run([sys.executable, os.path.join(VALIDATORS, "output_validator.py"), "voice", path])
        ok(r.returncode != 0, "gate fails on a script full of visual directions")
        ok("http" in r.stdout.lower() or "url" in r.stdout.lower(),
           "failure names the URL problem")


@test("validator: narration gate passes on a freshly rendered project")
def t_validate_narration():
    if not have_ffmpeg():
        raise Skip("ffmpeg not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        run([sys.executable, os.path.join(AUDIO, "tts_engine.py"),
             "--project", proj, "--provider", "mock", "--mode", "final", "--yes"])
        r = run([sys.executable, os.path.join(VALIDATORS, "audio_validator.py"), proj])
        eq(r.returncode, 0, f"narration gate passes (out: {r.stdout[-400:]})")


@test("validator: narration gate fails when no audio was rendered")
def t_validate_narration_missing():
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        r = run([sys.executable, os.path.join(VALIDATORS, "audio_validator.py"), proj])
        ok(r.returncode != 0, "gate fails when narration_manifest.json is absent")


@test("validator: stale detector flags narration older than the script")
def t_stale_detection():
    if not have_ffmpeg():
        raise Skip("ffmpeg not on PATH")
    import time
    with tempfile.TemporaryDirectory() as tmp:
        proj = make_project(tmp)
        run([sys.executable, os.path.join(AUDIO, "tts_engine.py"),
             "--project", proj, "--provider", "mock", "--mode", "final", "--yes"])

        r = run([sys.executable, os.path.join(VALIDATORS, "stale_detector.py"), proj])
        payload = json.loads(r.stdout.split("STALE_JSON:")[1].strip())
        eq(payload["voiceover"], False, "fresh narration is not stale")

        time.sleep(1.1)
        with open(os.path.join(proj, "voice_script.md"), "a", encoding="utf-8") as f:
            f.write("\n[CTA]\nOne more line the audio has never heard.\n")

        r = run([sys.executable, os.path.join(VALIDATORS, "stale_detector.py"), proj])
        payload = json.loads(r.stdout.split("STALE_JSON:")[1].strip())
        eq(payload["voiceover"], True, "edited script marks the narration stale")


# ---------------------------------------------------------------------------
# 5. Pipeline wiring
# ---------------------------------------------------------------------------

@test("orchestrator: voiceover is a first-class stage in every stage map")
def t_stage_order():
    sys.path.insert(0, VN)
    sys.path.insert(0, os.path.join(VN, "tools"))
    import importlib

    orch = importlib.import_module("workflow_orchestrator")
    ok("voiceover" in orch.STAGE_ORDER, "orchestrator STAGE_ORDER includes voiceover")
    eq(orch.STAGE_ORDER.index("voiceover"), orch.STAGE_ORDER.index("scriptwriting") + 1,
       "voiceover runs immediately after scriptwriting")

    rework = importlib.import_module("auto_rework")
    ok("voiceover" in rework.STAGE_ORDER, "auto_rework STAGE_ORDER includes voiceover")
    eq(rework.AGENT_TO_STAGE.get("narrator"), "voiceover",
       "the narrator agent maps to the voiceover stage")


@test("orchestrator: agent subprocesses are never invoked with shell=True on a list")
def t_no_shell_list():
    # Regression: subprocess.run([...], shell=True) runs only argv[0] on POSIX,
    # silently discarding the prompt that was supposed to drive the agent.
    path = os.path.join(VN, "workflow_orchestrator.py")
    with open(path, encoding="utf-8") as f:
        code_lines = [ln for ln in f if not ln.strip().startswith("#")]
    offenders = [i for i, ln in enumerate(code_lines, 1) if "shell=True" in ln]
    ok(not offenders,
       f"workflow_orchestrator.py has no shell=True in executable code (lines {offenders})")


@test("config: the voice block exists and holds no credentials")
def t_config_voice_block():
    path = os.path.join(VN, "config.yaml")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    ok("voice:" in text, "config.yaml declares a voice block")
    for key in ("provider:", "draft_provider:", "cost_ceiling_usd:", "fallback_chain:"):
        ok(key in text, f"voice config exposes {key}")
    lowered = text.lower()
    for secret in ("api_key:", "apikey:", "sk-", "xi-api-key"):
        ok(secret not in lowered, f"config.yaml contains no {secret!r}")


@test("packaging: every agent persona reaches every CLI target")
def t_agent_fanout():
    agents = []
    for root, _dirs, files in os.walk(os.path.join(VN, "agents")):
        for name in files:
            if name.endswith(".md") and name != "self_review_protocol.md":
                agents.append(os.path.splitext(name)[0])

    alias = {"prompt_agent": "prompt"}
    expected = {alias.get(a, a) for a in agents}

    targets = {
        ".claude/commands": ".md",
        ".qwen/commands": ".md",
        ".opencode/agents": ".md",
        ".gemini/commands": ".toml",
        ".hermes/skills": ".md",
    }
    for folder, ext in targets.items():
        full = os.path.join(REPO_ROOT, folder)
        if not os.path.isdir(full):
            raise Skip(f"{folder} not present")
        present = {os.path.splitext(f)[0] for f in os.listdir(full) if f.endswith(ext)}
        missing = expected - present
        ok(not missing, f"{folder} is missing: {sorted(missing)}")

    ok(os.path.exists(os.path.join(REPO_ROOT, ".claude", "skills", "narrator", "SKILL.md")),
       ".claude/skills/narrator/SKILL.md generated")


@test("packaging: the npm tarball is not missing its agent command folders")
def t_package_completeness():
    with open(os.path.join(VN, "package.json"), encoding="utf-8") as f:
        pkg = json.load(f)

    ok("prepack" in pkg.get("scripts", {}),
       "package.json has a prepack hook that stages root assets")

    # Every path promised in files[] must be producible. Directories that live
    # only at the repo root are staged by prepack.js - check both locations.
    for entry in pkg["files"]:
        name = entry.rstrip("/")
        in_pkg = os.path.exists(os.path.join(VN, name))
        in_root = os.path.exists(os.path.join(REPO_ROOT, name))
        ok(in_pkg or in_root, f"files[] entry '{entry}' exists somewhere")


@test("hygiene: no author-machine absolute paths are shipped")
def t_no_hardcoded_paths():
    needles = ("g:/youtuber", "g:\\youtuber", "ai%20_team")
    offenders = []
    skip_dirs = {".git", "node_modules", "__pycache__", "tests"}
    # Audit write-ups quote the offending paths verbatim as evidence. Prose that
    # documents the bug is not the bug.
    skip_files = {"AUDIT_V1_2026.md", "AUDIT_REPORT.md"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if name in skip_files:
                continue
            if name.endswith((".pyc", ".png", ".jpg", ".mp3", ".wav", ".zip")):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    body = f.read().lower()
            except OSError:
                continue
            if any(n in body for n in needles):
                offenders.append(os.path.relpath(path, REPO_ROOT))
    ok(not offenders, f"no hardcoded author paths (found: {offenders})")


@test("hygiene: no compiled bytecode is tracked by git")
def t_no_tracked_pyc():
    r = run(["git", "ls-files"], cwd=REPO_ROOT)
    if r.returncode != 0:
        raise Skip("not a git checkout")
    tracked = [f for f in r.stdout.splitlines() if f.endswith(".pyc")]
    ok(not tracked, f"no .pyc tracked (found {len(tracked)})")


@test("hygiene: secrets are gitignored")
def t_gitignore_secrets():
    with open(os.path.join(REPO_ROOT, ".gitignore"), encoding="utf-8") as f:
        body = f.read()
    for pattern in (".env", "__pycache__/", ".tts_cache/"):
        ok(pattern in body, f".gitignore covers {pattern}")
    ok(os.path.exists(os.path.join(REPO_ROOT, ".env.example")),
       ".env.example documents the required keys")


@test("docs: the narrator persona is wired into the agent roster")
def t_narrator_documented():
    persona = os.path.join(VN, "agents", "creative", "narrator.md")
    ok(os.path.exists(persona), "narrator.md persona exists")
    with open(persona, encoding="utf-8") as f:
        body = f.read()
    for needle in ("voice_script.md", "narration_full.mp3", "cost", "tts_engine.py"):
        ok(needle in body, f"persona mentions {needle}")

    with open(os.path.join(REPO_ROOT, ".cursorrules"), encoding="utf-8") as f:
        ok("narrator" in f.read(), ".cursorrules lists the narrator")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print(f"\n{'=' * 68}")
    print("  VideoNut regression suite")
    print(f"{'=' * 68}\n")

    selected = [(n, f) for n, f in _REGISTRY if not FILTER or FILTER.lower() in n.lower()]
    if not selected:
        print(f"No tests matched {FILTER!r}")
        return 1

    for name, fn in selected:
        try:
            fn()
        except Skip as e:
            _results["skip"] += 1
            print(f"{YELLOW}  SKIP{RESET}  {name}  {DIM}({e}){RESET}")
        except AssertionError as e:
            _results["fail"] += 1
            print(f"{RED}  FAIL{RESET}  {name}")
            print(f"        {RED}{e}{RESET}")
        except Exception as e:  # noqa: BLE001 - a crash is a failure
            _results["fail"] += 1
            print(f"{RED} ERROR{RESET}  {name}")
            print(f"        {RED}{type(e).__name__}: {e}{RESET}")
        else:
            _results["pass"] += 1
            print(f"{GREEN}  PASS{RESET}  {name}")

    print(f"\n{'-' * 68}")
    total = sum(_results.values())
    print(f"  {_results['pass']}/{total} passed"
          + (f", {_results['fail']} failed" if _results["fail"] else "")
          + (f", {_results['skip']} skipped" if _results["skip"] else ""))
    if not have_ffmpeg():
        print(f"  {YELLOW}ffmpeg is not on PATH - audio render tests were skipped.{RESET}")
    print(f"{'-' * 68}\n")
    return 1 if _results["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
