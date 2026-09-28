#!/usr/bin/env python3
"""
VideoNut Script Normalizer
==========================

Turns the Scriptwriter's `voice_script.md` into a provider-agnostic list of
speech segments that a TTS engine can render deterministically.

Why this module exists
----------------------
`voice_script.md` is written for *humans and voice actors*. It contains:

  * Markdown chrome            -> `# Heading`, `**bold**`, `---`, code fences
  * Section markers            -> `[HOOK] [BRIDGE] [MEAT] [HUMAN BEAT] [VERDICT] [CTA]`
  * VideoNut voice cues        -> `(pause 2s)`, `(emphasis) ... (end emphasis)`,
                                  `(modulation pitch: high speed: fast tone: questioning) ...
                                   (end modulation)`, `(breath)`, `(sigh)`
  * Bookkeeping footers        -> `**Total Words:** 4500`

If this text is shipped to a TTS API as-is, the narrator will literally read
"open paren pause two seconds close paren" and "hash hash meat". That is the
single most common failure mode when bolting TTS onto a markdown pipeline, so
normalization is a hard requirement, not a nicety.

Output model
------------
`parse_voice_script()` returns a list of `Segment` objects:

  Segment(kind="speech", text=..., section="MEAT", cues=[...])
  Segment(kind="silence", seconds=2.0, section="MEAT")

`silence` segments are rendered as real digital silence by the TTS engine, which
makes pauses exact and identical across every provider (instead of hoping the
model "feels" the ellipsis).

Rendering
---------
`render_text(segment, dialect)` converts a speech segment into the exact string
to send to a given provider family:

  dialect="audio_tags"  -> ElevenLabs v3 inline tags: `[whispers] ... `
  dialect="ssml"        -> `<emphasis>`, `<prosody>` (Azure / Google Cloud TTS)
  dialect="style_prompt"-> plain text (cues are surfaced separately as a natural
                           language style instruction, e.g. Gemini / OpenAI)
  dialect="plain"       -> cues stripped entirely (Piper, Sarvam, fallbacks)

CLI
---
    python script_normalizer.py --script ./Projects/demo/voice_script.md --stats
    python script_normalizer.py --script ./Projects/demo/voice_script.md \
        --dialect audio_tags --preview 5
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SECTION_MARKERS = [
    "HOOK",
    "BRIDGE",
    "MEAT",
    "HUMAN BEAT",
    "VERDICT",
    "CTA",
    "OUTRO",
]

# Average spoken words-per-minute by language family. Used for duration and cost
# estimates before a single API call is made (see tts_engine --dry-run).
WPM_BY_LANGUAGE = {
    "english": 150,
    "hindi": 135,
    "telugu": 125,
    "tamil": 125,
    "kannada": 125,
    "malayalam": 120,
    "marathi": 135,
    "bengali": 135,
    "gujarati": 135,
    "punjabi": 135,
    "odia": 130,
    "default": 140,
}

# VideoNut cue -> canonical intent. Keep this table as the single source of truth;
# every provider dialect maps off it.
CUE_INTENTS = {
    "emphasis": {"audio_tag": "[emphasis]", "ssml": "emphasis", "style": "emphasised"},
    "whisper": {"audio_tag": "[whispers]", "ssml": "soft", "style": "whispered"},
    "sarcastic": {"audio_tag": "[sarcastic]", "ssml": None, "style": "sarcastic"},
    "angry": {"audio_tag": "[angry]", "ssml": None, "style": "angry"},
    "sad": {"audio_tag": "[sad]", "ssml": None, "style": "sombre"},
    "grave": {"audio_tag": "[serious]", "ssml": None, "style": "grave and serious"},
    "questioning": {"audio_tag": "[curious]", "ssml": None, "style": "questioning"},
    "excited": {"audio_tag": "[excited]", "ssml": None, "style": "excited"},
    "urgent": {"audio_tag": "[urgent]", "ssml": None, "style": "urgent"},
    "breath": {"audio_tag": "[breathes]", "ssml": None, "style": "with an audible breath"},
    "sigh": {"audio_tag": "[sighs]", "ssml": None, "style": "with a sigh"},
}

# Regexes for the cue grammar defined in agents/creative/scriptwriter.md
RE_PAUSE = re.compile(r"\(\s*pause\s+([0-9]+(?:\.[0-9]+)?)\s*s?\s*\)", re.IGNORECASE)
RE_EMPHASIS_OPEN = re.compile(r"\(\s*emphasis\s*\)", re.IGNORECASE)
RE_EMPHASIS_CLOSE = re.compile(r"\(\s*end\s+emphasis\s*\)", re.IGNORECASE)
RE_MODULATION_OPEN = re.compile(r"\(\s*modulation\s+([^)]*)\)", re.IGNORECASE)
RE_MODULATION_CLOSE = re.compile(r"\(\s*end\s+modulation\s*\)", re.IGNORECASE)
RE_SIMPLE_CUE = re.compile(r"\(\s*(breath|sigh|beat|whisper|laughs?|scoffs?)\s*\)", re.IGNORECASE)
RE_SECTION = re.compile(r"^\s*\[\s*(" + "|".join(SECTION_MARKERS) + r")\s*\]\s*$", re.IGNORECASE)
# Same markers, but anywhere in the line - lets us recognise `## [MEAT]`, which
# some writers emit, as a section header rather than discarding it as chrome.
RE_SECTION_ANYWHERE = re.compile(r"\[\s*(" + "|".join(SECTION_MARKERS) + r")\s*\]", re.IGNORECASE)
RE_INLINE_SECTION = re.compile(r"\[\s*(" + "|".join(SECTION_MARKERS) + r")\s*\]", re.IGNORECASE)
# Anything left in parentheses that looks like a stage direction rather than speech
RE_RESIDUAL_CUE = re.compile(
    r"\(\s*(?:end\s+)?(?:pause|emphasis|modulation|tone|pitch|speed|voice|sfx|music|note)\b[^)]*\)",
    re.IGNORECASE,
)
RE_SPEAKER_TAG = re.compile(r"^\s*(NARRATOR|VO|V\.O\.|VOICEOVER)\s*:\s*", re.IGNORECASE)
RE_VISUAL_DIRECTION = re.compile(r"^\s*\[\s*(visual|b-?roll|shot|source|cut|on screen)\b[^\]]*\]\s*$", re.IGNORECASE)
RE_TOTAL_WORDS = re.compile(r"^\s*\**\s*total\s+words\s*:?\**.*$", re.IGNORECASE)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?\u0964\u3002])\s+")


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Segment:
    """One renderable unit of narration."""

    kind: str  # "speech" | "silence"
    section: str = "UNSECTIONED"
    text: str = ""
    seconds: float = 0.0
    cues: List[str] = field(default_factory=list)
    index: int = 0

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScriptStats:
    words: int = 0
    characters: int = 0
    billable_characters: int = 0
    speech_segments: int = 0
    silence_segments: int = 0
    silence_seconds: float = 0.0
    sections: Dict[str, int] = field(default_factory=dict)
    estimated_minutes: float = 0.0
    cues_found: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────────────
# Markdown cleanup
# ──────────────────────────────────────────────────────────────────────────────


def strip_markdown(line: str) -> str:
    """Remove markdown chrome that must never be spoken aloud."""
    line = re.sub(r"^#{1,6}\s*", "", line)          # headings
    line = re.sub(r"^\s*[-*+]\s+", "", line)         # bullets
    line = re.sub(r"^\s*>\s?", "", line)             # block quotes
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)     # bold
    line = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", line)  # *italics*
    line = re.sub(r"__(.+?)__", r"\1", line)        # __bold__
    line = re.sub(r"(?<![\w_])_([^_]+)_(?![\w_])", r"\1", line)  # _italics_
    line = re.sub(r"~~(.+?)~~", r"\1", line)        # ~~strikethrough~~
    line = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", line)  # inline code
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)   # images
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)  # links -> label
    line = re.sub(r"^\s*\|.*\|\s*$", "", line)       # table rows
    line = re.sub(r"^\s*[-=_]{3,}\s*$", "", line)    # horizontal rules
    return line.strip()


def _is_noise(line: str) -> bool:
    """
    True for lines that are bookkeeping / direction, not narration.

    Called on the RAW line, before strip_markdown(), so markdown chrome is
    still visible here. That matters: `## Act Two` is a document heading the
    Scriptwriter left behind, and stripping the `##` would turn it into two
    narrated words in the middle of a sentence.
    """
    if not line or not line.strip():
        return True
    stripped = line.strip()
    if RE_TOTAL_WORDS.match(stripped):
        return True
    if RE_VISUAL_DIRECTION.match(stripped):
        return True
    if re.match(r"^\s*<!--.*-->\s*$", stripped):
        return True
    # Markdown headings are structure, never narration - unless the writer used
    # one to carry a section marker (`## [MEAT]`), which the caller handles.
    if stripped.startswith("#") and not RE_SECTION_ANYWHERE.search(stripped):
        return True
    # Markdown table rows and horizontal rules.
    if stripped.startswith("|") and stripped.endswith("|"):
        return True
    if re.match(r"^\s*[-=_*]{3,}\s*$", stripped):
        return True
    # Bold-only metadata lines the Scriptwriter emits: `**Target Duration:** 8 min`
    if re.match(r"^\*\*[^*]+:\*\*", stripped):
        return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Cue extraction
# ──────────────────────────────────────────────────────────────────────────────


def _parse_modulation(raw: str) -> List[str]:
    """`pitch: high speed: fast tone: questioning` -> ['excited', 'questioning']"""
    cues: List[str] = []
    lowered = raw.lower()
    for key in ("tone", "pitch", "speed", "emotion"):
        for match in re.finditer(key + r"\s*:\s*([a-z\- ]+)", lowered):
            value = match.group(1).strip().split()[0] if match.group(1).strip() else ""
            if not value:
                continue
            if value in CUE_INTENTS:
                cues.append(value)
            elif value in ("high", "fast"):
                cues.append("excited")
            elif value in ("low", "slow", "deep"):
                cues.append("grave")
            elif value in ("soft", "quiet"):
                cues.append("whisper")
    # de-duplicate, keep order
    seen, out = set(), []
    for c in cues:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _tokenize_line(
    line: str, carry: List[str], pending: Optional[List[str]] = None
) -> (List[Dict], List[str], List[str]):
    """
    Walk a line left-to-right and emit cue-scoped pieces.

    Cue markers are *inline spans*, not line properties: in
    `(emphasis) Eight pages. (end emphasis) That's all it took...`
    only "Eight pages." is emphasised. Treating cues per-line (the naive
    approach) would either tag the whole sentence or - when a span opens and
    closes on the same line - silently drop the cue entirely.

    `carry` is the cue stack inherited from previous lines, so a modulation
    block that spans several lines keeps its delivery direction.

    `pending` holds one-shot cues such as `(breath)` that were declared on a
    line of their own; they attach to the next piece of real narration instead
    of being dropped.

    Returns (pieces, updated_carry, updated_pending).
    """
    tokens = []
    for regex, kind in (
        (RE_PAUSE, "pause"),
        (RE_EMPHASIS_OPEN, "emphasis_open"),
        (RE_EMPHASIS_CLOSE, "emphasis_close"),
        (RE_MODULATION_OPEN, "modulation_open"),
        (RE_MODULATION_CLOSE, "modulation_close"),
        (RE_SIMPLE_CUE, "simple"),
    ):
        for match in regex.finditer(line):
            tokens.append((match.start(), match.end(), kind, match))
    tokens.sort(key=lambda t: t[0])

    pieces: List[Dict] = []
    active = list(carry)
    modulation_cues: List[str] = [c for c in carry if c != "emphasis"]
    emphasis_on = "emphasis" in carry
    pending_simple: List[str] = list(pending or [])
    cursor = 0

    def push_text(raw: str):
        text = RE_RESIDUAL_CUE.sub("", raw)
        text = re.sub(r"\s{2,}", " ", text).strip()
        if not text:
            return
        cues = list(modulation_cues)
        if emphasis_on:
            cues.append("emphasis")
        cues.extend(pending_simple)
        pending_simple.clear()
        seen, ordered = set(), []
        for cue in cues:
            if cue not in seen:
                seen.add(cue)
                ordered.append(cue)
        pieces.append({"kind": "speech", "text": text, "cues": ordered})

    for start, end, kind, match in tokens:
        push_text(line[cursor:start])
        cursor = end
        if kind == "pause":
            pieces.append({"kind": "silence", "seconds": float(match.group(1))})
        elif kind == "emphasis_open":
            emphasis_on = True
        elif kind == "emphasis_close":
            emphasis_on = False
        elif kind == "modulation_open":
            modulation_cues = _parse_modulation(match.group(1))
        elif kind == "modulation_close":
            modulation_cues = []
        elif kind == "simple":
            key = match.group(1).lower().rstrip("s")
            key = {"laugh": "sigh", "scoff": "sarcastic", "beat": "breath"}.get(key, key)
            if key in CUE_INTENTS:
                pending_simple.append(key)

    push_text(line[cursor:])

    updated = list(modulation_cues)
    if emphasis_on:
        updated.append("emphasis")
    return pieces, updated, list(pending_simple)


# ──────────────────────────────────────────────────────────────────────────────
# Main parser
# ──────────────────────────────────────────────────────────────────────────────


def parse_voice_script(path: str, language: str = "English") -> (List[Segment], ScriptStats):
    """Parse a `voice_script.md` file into ordered segments plus statistics."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Voice script not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()

    return parse_voice_text(raw, language=language)


def parse_voice_text(raw: str, language: str = "English") -> (List[Segment], ScriptStats):
    """
    Parse voice-script *text* into ordered segments plus statistics.

    Separated from `parse_voice_script` so the tokenizer can be unit-tested
    against literal strings without touching the filesystem.
    """
    # Drop fenced code blocks wholesale - they are never narration.
    raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL)

    stats = ScriptStats()
    segments: List[Segment] = []
    carry: List[str] = []
    pending: List[str] = []
    skipped_frontmatter = 0

    lines = raw.splitlines()

    # Drop YAML front matter if the Scriptwriter emitted any.
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break

    # Everything before the first section marker is file header, not narration
    # (title, generation metadata, blockquotes). Narrating it is the classic
    # "the narrator read the filename out loud" bug.
    first_marker = next(
        (i for i, line in enumerate(lines)
         if RE_SECTION.match(line) or RE_INLINE_SECTION.search(strip_markdown(line))),
        None,
    )
    if first_marker is not None and first_marker > 0:
        skipped_frontmatter = len([line for line in lines[:first_marker] if line.strip()])
        lines = lines[first_marker:]
    current_section = "UNSECTIONED"

    for rawline in lines:
        line = rawline.rstrip()

        section_match = RE_SECTION.match(line)
        if section_match:
            current_section = section_match.group(1).upper()
            continue

        # Noise detection must see the RAW line: once strip_markdown() removes
        # the leading "##", a document heading is indistinguishable from a
        # sentence and gets narrated.
        if _is_noise(line):
            continue

        line = strip_markdown(line)
        if not line:
            continue

        # Inline section marker, e.g. "[HOOK] Three years ago..."
        inline = RE_INLINE_SECTION.search(line)
        if inline:
            current_section = inline.group(1).upper()
            line = RE_INLINE_SECTION.sub("", line).strip()
            if not line:
                continue

        line = RE_SPEAKER_TAG.sub("", line)

        pieces, carry, pending = _tokenize_line(line, carry, pending)
        for piece in pieces:
            if piece["kind"] == "silence":
                stats.cues_found["pause"] = stats.cues_found.get("pause", 0) + 1
                segments.append(
                    Segment(kind="silence", section=current_section, seconds=piece["seconds"])
                )
                continue
            for cue in piece["cues"]:
                stats.cues_found[cue] = stats.cues_found.get(cue, 0) + 1
            segments.append(
                Segment(
                    kind="speech",
                    section=current_section,
                    text=piece["text"],
                    cues=piece["cues"],
                )
            )

    # Merge consecutive silences, index everything, collect stats.
    merged: List[Segment] = []
    for seg in segments:
        if seg.kind == "silence" and merged and merged[-1].kind == "silence":
            merged[-1].seconds = round(merged[-1].seconds + seg.seconds, 3)
            continue
        merged.append(seg)

    for i, seg in enumerate(merged):
        seg.index = i
        if seg.kind == "speech":
            stats.speech_segments += 1
            stats.words += seg.word_count
            stats.characters += seg.char_count
            stats.billable_characters += seg.char_count
            stats.sections[seg.section] = stats.sections.get(seg.section, 0) + seg.word_count
        else:
            stats.silence_segments += 1
            stats.silence_seconds = round(stats.silence_seconds + seg.seconds, 3)

    wpm = WPM_BY_LANGUAGE.get((language or "english").strip().lower(), WPM_BY_LANGUAGE["default"])
    stats.estimated_minutes = round(stats.words / wpm + stats.silence_seconds / 60.0, 2)

    # --- sanity warnings (these become EIC / orchestrator gate failures) ------
    if stats.words == 0:
        stats.warnings.append("No narration text found - the script may be empty or all-directions.")
    if not stats.sections or set(stats.sections) == {"UNSECTIONED"}:
        stats.warnings.append(
            "No section markers ([HOOK]/[MEAT]/[CTA]) detected - narration timing map will be flat."
        )
    if stats.cues_found.get("pause", 0) == 0 and stats.words > 300:
        stats.warnings.append(
            "Zero pause cues in a long script - delivery will sound rushed and monotone."
        )
    if skipped_frontmatter:
        stats.warnings.append(
            f"Skipped {skipped_frontmatter} header line(s) above the first section marker "
            "(title/metadata are never narrated)."
        )
    residual = [
        seg.text for seg in merged
        if seg.kind == "speech" and re.search(r"[\[\]]|\*\*|^\s*\|", seg.text)
    ]
    if residual:
        stats.warnings.append(
            f"{len(residual)} chunk(s) still contain bracket/markdown characters - "
            "check the script for stage directions the normalizer did not recognise."
        )

    return merged, stats


# ──────────────────────────────────────────────────────────────────────────────
# Provider-dialect rendering
# ──────────────────────────────────────────────────────────────────────────────


def render_text(segment: Segment, dialect: str = "plain") -> str:
    """Render a speech segment for a specific provider dialect."""
    if segment.kind != "speech":
        return ""

    text = segment.text
    cues = segment.cues or []

    if dialect == "audio_tags":
        # ElevenLabs v3: inline bracketed performance direction, prepended once.
        tags = []
        for cue in dict.fromkeys(cues):
            tag = CUE_INTENTS.get(cue, {}).get("audio_tag")
            if tag and tag not in tags:
                tags.append(tag)
        return (" ".join(tags) + " " + text).strip() if tags else text

    if dialect == "ssml":
        body = text
        if "emphasis" in cues:
            body = f'<emphasis level="strong">{body}</emphasis>'
        if "whisper" in cues:
            body = f'<prosody volume="soft" rate="95%">{body}</prosody>'
        if "excited" in cues:
            body = f'<prosody pitch="+10%" rate="110%">{body}</prosody>'
        if "grave" in cues:
            body = f'<prosody pitch="-8%" rate="92%">{body}</prosody>'
        return body

    # "style_prompt" and "plain" both send clean text; style_prompt callers use
    # style_instruction() to pass delivery direction out-of-band.
    return text


def style_instruction(segment: Segment, base_style: str = "") -> str:
    """Natural-language delivery note for providers with a style/instructions field."""
    descriptors = []
    for cue in dict.fromkeys(segment.cues or []):
        style = CUE_INTENTS.get(cue, {}).get("style")
        if style and style not in descriptors:
            descriptors.append(style)
    parts = [p for p in [base_style.strip(), ", ".join(descriptors)] if p]
    return "; ".join(parts)


def merge_segments(segments: List[Segment], max_chars: int, dialect: str) -> List[Segment]:
    """
    Pack consecutive speech segments (same section + same cues) into chunks that
    stay under `max_chars`, splitting on sentence boundaries when a single
    segment is too long. Prosody survives far better with fewer, larger requests.
    """
    packed: List[Segment] = []
    buffer: Optional[Segment] = None

    def flush():
        nonlocal buffer
        if buffer is not None and buffer.text.strip():
            packed.append(buffer)
        buffer = None

    for seg in segments:
        if seg.kind == "silence":
            flush()
            packed.append(seg)
            continue

        rendered_len = len(render_text(seg, dialect))

        # Hard-split an oversized single segment on sentence boundaries.
        if rendered_len > max_chars:
            flush()
            sentences = [s for s in SENTENCE_SPLIT.split(seg.text) if s.strip()]
            current = ""
            for sentence in sentences:
                candidate = (current + " " + sentence).strip()
                if len(candidate) > max_chars and current:
                    packed.append(
                        Segment(kind="speech", section=seg.section, text=current, cues=list(seg.cues))
                    )
                    current = sentence
                else:
                    current = candidate
            while len(current) > max_chars:  # pathological single sentence
                packed.append(
                    Segment(kind="speech", section=seg.section, text=current[:max_chars], cues=list(seg.cues))
                )
                current = current[max_chars:]
            if current.strip():
                packed.append(
                    Segment(kind="speech", section=seg.section, text=current, cues=list(seg.cues))
                )
            continue

        if (
            buffer is not None
            and buffer.section == seg.section
            and buffer.cues == seg.cues
            and len(render_text(buffer, dialect)) + rendered_len + 1 <= max_chars
        ):
            buffer.text = (buffer.text + " " + seg.text).strip()
        else:
            flush()
            buffer = Segment(kind="speech", section=seg.section, text=seg.text, cues=list(seg.cues))

    flush()
    for i, seg in enumerate(packed):
        seg.index = i
    return packed


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize voice_script.md for TTS rendering.")
    parser.add_argument("--script", required=True, help="Path to voice_script.md")
    parser.add_argument("--language", default="English", help="audio_language from config.yaml")
    parser.add_argument(
        "--dialect",
        default="plain",
        choices=["plain", "audio_tags", "ssml", "style_prompt"],
        help="Provider dialect to render",
    )
    parser.add_argument("--max-chars", type=int, default=2500, help="Chunk size for packing")
    parser.add_argument("--preview", type=int, default=0, help="Print the first N rendered chunks")
    parser.add_argument("--stats", action="store_true", help="Print statistics")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    try:
        segments, stats = parse_voice_script(args.script, args.language)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}")
        return 1

    chunks = merge_segments(segments, args.max_chars, args.dialect)

    if args.json:
        print(json.dumps(
            {"stats": stats.to_dict(), "chunks": [c.to_dict() for c in chunks]},
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    if args.stats or not args.preview:
        print("[SCAN] Voice script analysis")
        print("-" * 52)
        print(f"  Words              : {stats.words}")
        print(f"  Billable characters: {stats.billable_characters}")
        print(f"  Speech chunks      : {len(  [c for c in chunks if c.kind == 'speech'])}")
        print(f"  Silence blocks     : {stats.silence_segments} ({stats.silence_seconds}s total)")
        print(f"  Estimated runtime  : {stats.estimated_minutes} min")
        print(f"  Sections           : {', '.join(stats.sections) or 'none'}")
        print(f"  Cues               : {stats.cues_found or 'none'}")
        for warning in stats.warnings:
            print(f"  [WARN] {warning}")

    if args.preview:
        print("\n[PREVIEW] Rendered chunks")
        print("-" * 52)
        shown = 0
        for chunk in chunks:
            if shown >= args.preview:
                break
            if chunk.kind == "silence":
                print(f"  <silence {chunk.seconds}s>")
            else:
                print(f"  [{chunk.section}] {render_text(chunk, args.dialect)[:300]}")
            shown += 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
