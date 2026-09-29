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

# ---------------------------------------------------------------------------
# Cross-agent consistency (added v1.5.1 after the audit found silent drift)
# ---------------------------------------------------------------------------


@test("consistency: the WPM table is identical in the normalizer, the agents and LIFECYCLE")
def _():
    """
    The scriptwriter sizes a script with one words-per-minute table and the
    narrator measures it with another. When they drifted, a correctly sized
    Telugu script came out 12% short and the narration gate rejected it.
    Any future edit must touch all four places or this test fails.
    """
    import re
    from script_normalizer import WPM_BY_LANGUAGE

    expected = {"english": 135, "telugu": 110, "hindi": 115}
    for lang, wpm in expected.items():
        eq(WPM_BY_LANGUAGE[lang], wpm, f"normalizer WPM for {lang}")
    eq(WPM_BY_LANGUAGE["default"], 120, "normalizer default WPM")

    sources = {
        "scriptwriter.md": os.path.join(VN, "agents", "creative", "scriptwriter.md"),
        "prompt_agent.md": os.path.join(VN, "agents", "core", "prompt_agent.md"),
        "LIFECYCLE.md": os.path.join(VN, "docs", "LIFECYCLE.md"),
    }
    for label, path in sources.items():
        ok(os.path.exists(path), f"{label} exists")
        text = open(path, encoding="utf-8").read()
        for lang, wpm in expected.items():
            ok(re.search(lang + r"\D{0,14}" + str(wpm), text, re.I) is not None,
               f"{label} states {lang.title()} = {wpm} wpm")


@test("rework: an unresolvable EIC verdict fails CLOSED, never as an approval")
def _():
    """
    The original parse_review_result() returned None for BOTH "approved" and
    "I could not work out what happened", and the orchestrator read any absence
    of a RERUN_STAGE line as approval. A missing verdict file therefore shipped
    an unreviewed video - and, once the Narrator existed, paid for its final
    narration too. Each of these cases must now be UNDETERMINED.
    """
    sys.path.insert(0, os.path.join(VN, "tools"))
    import importlib
    ar = importlib.import_module("auto_rework")
    importlib.reload(ar)

    cases = {
        "no review_result.json at all": None,
        "malformed JSON": "{\"verdict\":",
        "rejected but no agent named": '{"verdict": "REJECTED", "failed_agents": []}',
        "an agent nobody recognises": '{"verdict": "REJECTED", "rerun_from": "gaffer"}',
        "a manual-only agent": '{"verdict": "REJECTED", "rerun_from": "prompt"}',
    }
    for label, payload in cases.items():
        d = tempfile.mkdtemp(prefix="vn_rework_")
        try:
            if payload is not None:
                with open(os.path.join(d, "review_result.json"), "w", encoding="utf-8") as fh:
                    fh.write(payload)
            raised = False
            try:
                ar.parse_review_result(d)
            except ar.UndeterminedVerdict:
                raised = True
            ok(raised, f"UndeterminedVerdict raised for: {label}")
        finally:
            shutil.rmtree(d, ignore_errors=True)


@test("rework: a real rejection still routes to the right stage")
def _():
    sys.path.insert(0, os.path.join(VN, "tools"))
    import importlib
    ar = importlib.import_module("auto_rework")

    for name, stage in [("investigator", "investigation"),
                        ("INV", "investigation"),
                        ("scriptwriter", "scriptwriting"),
                        ("narrator", "voiceover")]:
        d = tempfile.mkdtemp(prefix="vn_rework_")
        try:
            with open(os.path.join(d, "review_result.json"), "w", encoding="utf-8") as fh:
                json.dump({"verdict": "REJECTED", "rerun_from": name}, fh)
            got, _msg = ar.parse_review_result(d)
            eq(got, stage, f"{name!r} routes to {stage!r}")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vn_rework_")
    try:
        with open(os.path.join(d, "review_result.json"), "w", encoding="utf-8") as fh:
            json.dump({"verdict": "APPROVED"}, fh)
        got, _msg = ar.parse_review_result(d)
        eq(got, None, "an explicit APPROVED returns no stage")
    finally:
        shutil.rmtree(d, ignore_errors=True)


@test("rework: every agent the EIC can name is routable or explicitly manual")
def _():
    """The EIC prompt and the rework engine must share one vocabulary."""
    import re
    sys.path.insert(0, os.path.join(VN, "tools"))
    import importlib
    ar = importlib.import_module("auto_rework")

    eic = open(os.path.join(VN, "agents", "core", "eic.md"), encoding="utf-8").read()
    block = re.search(r'Ask: "Which agent\? \[(.+?)\]"', eic, re.S)
    ok(block is not None, "the EIC still asks which agent to send work back to")
    names = [n.strip().lower() for n in re.split(r"[/\s\n]+", block.group(1)) if n.strip()]
    ok(len(names) >= 7, f"the EIC offers a full agent list (got {len(names)})")
    known = set(ar.AGENT_TO_STAGE) | set(ar.MANUAL_ONLY_AGENTS)
    for n in names:
        ok(n in known, f"EIC-offered agent {n!r} is known to the rework engine")


@test("consistency: the narrator and visionary are reachable from the pipeline")
def _():
    """
    Both agents existed with no inbound handoff - nothing in the pipeline ever
    told the user to run them, so they were dead code from the user's side.
    """
    agents_dir = os.path.join(VN, "agents")
    body = ""
    for root, _dirs, files in os.walk(agents_dir):
        for f in files:
            if f.endswith(".md"):
                body += open(os.path.join(root, f), encoding="utf-8").read()
    for slash, owner in [("/narrator", "narrator"), ("/visionary", "visionary")]:
        others = body.count(slash)
        ok(others >= 2, f"{slash} is named as a next step somewhere ({others} mentions)")


@test("consistency: the director times shots against measured narration, not a guess")
def _():
    d = open(os.path.join(VN, "agents", "creative", "director.md"), encoding="utf-8").read()
    ok("narration_cues.md" in d, "the director reads narration_cues.md")
    ok("ESTIMATED" in d or "estimate" in d.lower(),
       "the director warns when it is falling back to estimated timings")


@test("providers: kokoro is registered, free, offline and refuses languages it cannot speak")
def _():
    import providers as P

    ok("kokoro" in P.REGISTRY, "kokoro is in the provider registry")
    prof = P.PROFILES["kokoro"]
    eq(prof.usd_per_1k_chars, 0.0, "kokoro costs nothing per character")
    eq(prof.offline, True, "kokoro runs offline")
    ok(prof.max_chars <= 450, f"kokoro chunks under its ~510 token cap (got {prof.max_chars})")

    # It must not silently mangle a language it has no voice for.
    ready, why = P.get_provider("kokoro", P.ProviderSettings(language="Telugu")).check_ready()
    eq(ready, False, "kokoro refuses Telugu")
    ok("sarvam" in why.lower(), "and points at a provider that can do it")

    # A draft pass must never reach for a paid API.
    for name in P.DRAFT_CHAIN:
        eq(P.PROFILES[name].usd_per_1k_chars, 0.0, f"draft-chain provider {name!r} is free")


@test("providers: the piper profile no longer claims an MIT licence")
def _():
    """
    rhasspy/piper (MIT) was archived in Oct 2025; the maintained fork is GPL-3.0.
    Shipping a distributed npm package on a wrong licence note is a real risk.
    """
    import providers as P
    notes = P.PROFILES["piper"].notes
    ok("MIT-licensed neural TTS" not in notes, "the stale MIT claim is gone")
    ok("GPL" in notes, "the note mentions the actual GPL-3.0 fork")



@test("hygiene: prepack build artifacts are not tracked in git")
def _():
    """
    `prepack` stages the seven CLI folders into _video_nut/ so the tarball is
    self-contained, and `postpack` deletes them. They are generated from the
    identically named folders at the repo root.

    Running `git add -A` while a pack is half-finished commits 76 generated
    files; the next clean checkout then deletes them again, and the diff noise
    hides real changes. It happened once. This stops it happening twice.
    """
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise Skip("not a git checkout")
    tracked = out.stdout.splitlines()

    staged_dirs = [".claude", ".gemini", ".qwen", ".opencode",
                   ".hermes", ".codex", ".antigravity"]
    for d in staged_dirs:
        prefix = f"_video_nut/{d}/"
        hits = [f for f in tracked if f.startswith(prefix)]
        ok(not hits, f"{prefix} is a build artifact and must not be tracked "
                     f"({len(hits)} files found; run `node _video_nut/scripts/prepack.js --clean`)")

    for f in ("_video_nut/LICENSE", "_video_nut/CONTRIBUTING.md", "_video_nut/.env.example"):
        ok(f not in tracked, f"{f} is staged by prepack from the repo root, not authored here")

    ok(not [f for f in tracked if f.endswith(".tgz")], "no npm tarball is tracked")



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
