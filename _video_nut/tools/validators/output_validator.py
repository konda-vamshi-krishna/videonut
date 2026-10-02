import os
import sys
import re

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def validate_dossier(dossier_path):
    """
    Validates truth_dossier.md:
    1. Checks file exists and is not empty (size > 500 bytes).
    2. Checks for presence of research questions (looks for at least 10 numbered items or questions).
    3. Checks for presence of source URLs (looks for 'http://' or 'https://').
    """
    if not os.path.exists(dossier_path):
        return False, "File does not exist"
    
    if os.path.getsize(dossier_path) < 500:
        return False, "File is too small (< 500 bytes), likely empty or incomplete"
        
    try:
        with open(dossier_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    # Check for links
    urls = re.findall(r'https?://[^\s)\]]+', content)
    if not urls:
        return False, "No source URLs/links found in the truth dossier. Investigator must include sources."
        
    # Check for research questions (numbered lists or questions)
    # Match items like "1. ", "15. ", or paragraphs starting with numbers, or question marks
    question_matches = re.findall(r'\d+\.\s+.*', content)
    question_marks = content.count('?')
    
    # We expect some substantial list of findings or questions
    if len(question_matches) < 10 and question_marks < 5:
        return False, f"Insufficient research questions/findings found (matched lists: {len(question_matches)}, question marks: {question_marks}). Minimum is 10."
        
    return True, f"Valid truth dossier (found {len(urls)} URLs, {len(question_matches)} research list items)"

def validate_script(script_path):
    """
    Validates narrative_script.md:
    1. Checks file exists and size > 1000 bytes.
    2. Checks for standard script structural sections (HOOK, MEAT, HUMAN BEAT, OUTRO/CALL TO ACTION).
    3. Checks for presence of visual cues or voice directions.
    """
    if not os.path.exists(script_path):
        return False, "File does not exist"
        
    if os.path.getsize(script_path) < 1000:
        return False, "File is too small (< 1KB). Narrative script must be a complete script."
        
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    content_upper = content.upper()
    
    # Check sections (at least a couple of hook, meat, human, outro sections or indicators)
    has_hook = "HOOK" in content_upper
    has_meat = "MEAT" in content_upper or "BODY" in content_upper
    has_outro = "OUTRO" in content_upper or "CALL TO ACTION" in content_upper or "CTA" in content_upper
    
    # Validate structure
    missing_sections = []
    if not has_hook: missing_sections.append("HOOK")
    if not has_meat: missing_sections.append("MEAT/BODY")
    if not has_outro: missing_sections.append("OUTRO/CTA")
    
    if len(missing_sections) > 1: # Let it pass if only one section label is missing, but fail if more
        return False, f"Missing script structure sections: {', '.join(missing_sections)}"
        
    # Check for visual cues or voice indicators (e.g. bracketed text, narrator tags)
    visual_indicators = re.findall(r'\[Visual:.*?\]|\[Voice:.*?\]|\(Narrator:.*?\)|NARRATOR:', content, re.IGNORECASE)
    if not visual_indicators and len(re.findall(r'\[.*?\]', content)) < 5:
        return False, "No visual directions or narration cues found (e.g. [Visual: ...] or NARRATOR:)"
        
    return True, "Valid narrative script structure"

def validate_manifest(manifest_path):
    """
    Validates asset_manifest.md:
    1. Checks file exists and size > 200 bytes.
    2. Checks for markdown table formatting.
    3. Verifies that columns look correct (contains URLs/timestamps).
    """
    if not os.path.exists(manifest_path):
        return False, "File does not exist"
        
    if os.path.getsize(manifest_path) < 200:
        return False, "File is too small (< 200 bytes). Manifest must contain asset list."
        
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    # Check for markdown table divider (|---|)
    table_dividers = re.findall(r'\|[\s-]*:?[\s-]*\|', content)
    if not table_dividers:
        return False, "No valid markdown table formatting found in asset manifest."
        
    # Check for URLs
    urls = re.findall(r'https?://[^\s|\]]+', content)
    # Check if we have at least one valid URL or placeholder
    if not urls and "MANUAL" not in content and "STOCK" not in content:
        return False, "No download URLs or MANUAL/STOCK asset listings found in manifest."
        
    return True, f"Valid asset manifest (found {len(urls)} verified URLs)"

def validate_voice_script(script_path):
    """
    Validates voice_script.md - the file the Narrator/TTS stage consumes.

    Deliberately stricter than validate_script(): once text reaches a TTS API,
    every stray markdown table, URL or stage direction is either billed and read
    aloud, or silently mangled. Catching it here is free.

    Unlike the other validators this one reports EVERY problem it finds instead
    of stopping at the first. A script with four issues should cost one round
    trip to fix, not four.
    """
    if not os.path.exists(script_path):
        return False, "File does not exist (Scriptwriter must emit voice_script.md)"

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"

    problems = []   # fatal - block the pipeline
    warnings = []   # non-fatal - the engine copes, but the Scriptwriter should not do this
    upper = content.upper()

    # 1. Section markers drive the narration cue sheet.
    markers = [m for m in ("[HOOK]", "[BRIDGE]", "[MEAT]", "[HUMAN BEAT]", "[VERDICT]", "[CTA]")
               if m in upper]
    if len(markers) < 2:
        problems.append(
            "Missing section markers - needs at least [HOOK] and one of "
            "[MEAT]/[VERDICT]/[CTA] so narration can be mapped to timecodes."
        )

    # 2. Visual directions must NOT be in the voice script - they get narrated.
    visual_hits = re.findall(
        r'\[\s*(?:VISUAL|B-?ROLL|SHOT|CUT TO|SOURCE|ON SCREEN|GRAPHIC|TEXT ON SCREEN)\b[^\]]*\]',
        content, re.IGNORECASE)
    if visual_hits:
        # The normalizer strips a handful safely, so a few are a warning. Past
        # that the file is structurally a shot list, not a narration script,
        # and the word count / runtime estimate can no longer be trusted.
        message = (
            f"{len(visual_hits)} visual direction(s) found (e.g. {visual_hits[0][:48]!r}). "
            "voice_script.md is narration only. Visuals belong in "
            "master_script.md / video_direction.md."
        )
        (problems if len(visual_hits) > 3 else warnings).append(message)

    # 3. Raw URLs are unreadable by TTS.
    urls = re.findall(r'https?://\S+', content)
    if urls:
        problems.append(
            f"{len(urls)} raw URL(s) in the voice script (e.g. {urls[0][:50]}). "
            "TTS spells them out character by character. Move citations to truth_dossier.md."
        )

    # 4. Unbalanced cue spans. An unclosed (emphasis) swallows the rest of the
    #    script into one delivery style - the single most common cue bug.
    for opener, closer in (("emphasis", "end emphasis"), ("modulation", "end modulation")):
        n_open = len(re.findall(r'\(\s*%s\b' % opener, content, re.IGNORECASE))
        n_close = len(re.findall(r'\(\s*%s\b' % closer, content, re.IGNORECASE))
        if n_open != n_close:
            problems.append(
                f"Unbalanced ({opener}) cues: {n_open} opened, {n_close} closed. "
                f"Every ({opener}) needs a matching ({closer})."
            )

    # 5. Voice cues make the difference between narration and a robot.
    cues = re.findall(r'\((?:pause|emphasis|end emphasis|modulation|end modulation|breath|sigh|whisper)\b[^)]*\)',
                      content, re.IGNORECASE)
    word_count = len(re.sub(r'\(.*?\)|\[.*?\]', '', content).split())
    if word_count > 400 and len(cues) < max(3, word_count // 200):
        problems.append(
            f"Only {len(cues)} voice cue(s) across {word_count} words. Aim for roughly one cue "
            "per 100-200 words: (pause Ns), (emphasis)...(end emphasis), (modulation ...)."
        )

    # 6. Substance check - run last so a thin script still reports its real defects.
    if word_count < 80:
        problems.append(
            f"Only {word_count} narratable words. This is too short to be a real "
            "narration script (a 1-minute video needs roughly 150)."
        )

    suffix = "".join(f"\n     [WARN] {w}" for w in warnings)

    if problems:
        if len(problems) == 1:
            return False, problems[0] + suffix
        joined = "".join(f"\n     {i}. {p}" for i, p in enumerate(problems, 1))
        return False, f"{len(problems)} problems in voice_script.md:{joined}{suffix}"

    return True, (
        f"Valid voice script ({word_count} words, {len(markers)} sections, "
        f"{len(cues)} voice cues){suffix}"
    )


def validate_narration(project_path):
    """Delegates to audio_validator for the generated-audio gate."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from audio_validator import validate_narration as _validate
    except ImportError as exc:
        return False, f"audio_validator.py is unavailable: {exc}"
    result = _validate(project_path)
    if result["passed"]:
        summary = result.get("summary", {})
        return True, (
            f"Narration OK ({summary.get('duration_seconds', '?')}s via "
            f"{summary.get('provider', '?')}, drift {summary.get('drift_pct', 'n/a')}%)"
        )
    return False, "; ".join(result["errors"]) or "narration validation failed"


# Artifact -> validator. Order matches the pipeline so the report reads like a
# run. `required` is False for artifacts a given run may legitimately not have
# reached yet; missing ones are reported as SKIP, not FAIL.
PROJECT_ARTIFACTS = [
    ("truth_dossier.md", "dossier", True),
    ("narrative_script.md", "script", True),
    ("voice_script.md", "voice", False),
    ("master_script.md", "master", False),
    ("asset_manifest.md", "manifest", True),
]


def validate_master_script(path):
    """
    master_script.md is the Director's combined narration+visual reference.
    director.md declares the format as:
        [NARRATION: "..."] [VISUAL: Description. [Source: URL or MANUAL]]
    """
    if not os.path.exists(path):
        return False, f"File does not exist: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if len(content.strip()) < 100:
        return False, "File content too short, may be incomplete"

    narration = re.findall(r"\[NARRATION:.*?\]", content, re.S)
    visual = re.findall(r"\[VISUAL:.*?\]", content, re.S)

    if not narration:
        return False, ('No narration blocks found. director.md requires '
                       '[NARRATION: "..."] blocks in master_script.md.')
    if not visual:
        return False, ("No visual blocks found. director.md requires "
                       "[VISUAL: ...] blocks in master_script.md.")
    return True, f"Valid master script ({len(narration)} narration, {len(visual)} visual blocks)"


def validate_project(project_path):
    """
    Sweep every artifact in a project folder and report one line each.

    This replaces the old top-level `file_validator.py`, which duplicated these
    checks with a *different* and partly stale contract - it demanded 'The Angle'
    and 'The Conflict' headings that investigator.md has never produced, so it
    failed on correct output. One implementation, one contract.
    """
    if not os.path.isdir(project_path):
        return False, f"Project directory does not exist: {project_path}"

    dispatch = {
        "dossier": validate_dossier,
        "script": validate_script,
        "voice": validate_voice_script,
        "manifest": validate_manifest,
        "master": validate_master_script,
    }

    lines, failed, checked = [], 0, 0
    for filename, kind, required in PROJECT_ARTIFACTS:
        path = os.path.join(project_path, filename)
        if not os.path.exists(path):
            if required:
                failed += 1
                lines.append(f"  [FAIL] {filename}: missing (required)")
            else:
                lines.append(f"  [SKIP] {filename}: not produced yet")
            continue
        checked += 1
        try:
            good, msg = dispatch[kind](path)
        except Exception as e:  # a crashing validator is a failing validator
            good, msg = False, f"validator crashed: {type(e).__name__}: {e}"
        if good:
            lines.append(f"  [OK]   {filename}: {msg}")
        else:
            failed += 1
            lines.append(f"  [FAIL] {filename}: {msg}")

    report = "\n".join(lines)
    if failed:
        return False, f"{failed} artifact(s) failed validation:\n{report}"
    return True, f"All {checked} artifact(s) validated:\n{report}"



def main():
    if len(sys.argv) < 3:
        print("Usage: python output_validator.py <type> <file_path|project_path>")
        print("Types: dossier, script, voice, master, manifest, narration, project")
        sys.exit(1)
        
    val_type = sys.argv[1].lower()
    file_path = sys.argv[2]
    
    if val_type == "dossier":
        success, msg = validate_dossier(file_path)
    elif val_type == "script":
        success, msg = validate_script(file_path)
    elif val_type == "voice":
        success, msg = validate_voice_script(file_path)
    elif val_type == "narration":
        success, msg = validate_narration(file_path)
    elif val_type == "master":
        success, msg = validate_master_script(file_path)
    elif val_type == "project":
        success, msg = validate_project(file_path)
    elif val_type == "manifest":
        success, msg = validate_manifest(file_path)
    else:
        print(f"Unknown validation type: {val_type}")
        sys.exit(1)
        
    if success:
        print(f"[OK] Validation PASSED: {msg}")
        sys.exit(0)
    else:
        print(f"[FAIL] Validation FAILED: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
