#!/usr/bin/env python3
"""
Compute the target word count for a script - the one number the whole pipeline
is graded against.

Why this tool exists
--------------------
`target_word_count` lives in config.yaml and the Editor-in-Chief hard-fails any
script outside +/-10% of it. But nothing ever *computed* it: topic_scout.md told
the agent to "Calculate target_word_count based on audio_language settings",
i.e. an LLM did `duration x words-per-minute` as mental arithmetic and wrote the
answer into config.

Two things go wrong with that.

  1. If the model slips a digit, every downstream script is measured against a
     wrong target and the EIC rejects correct work (or passes bad work). Nothing
     cross-checks the number.
  2. The model has to remember the per-language speaking rate. Those rates drifted
     between the agent prompts and the audio engine once already, and Telugu and
     Hindi scripts were rejected for being "12-15% short" when they were correct.

So the rate table has exactly one home - script_normalizer.WPM_BY_LANGUAGE - and
this tool is the only thing that multiplies.

Usage
-----
    python word_target.py 15 English            # -> target and the accepted band
    python word_target.py 15 Telugu --json
    python word_target.py 15 Hindi --check 1680 # does an actual count pass?
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio"))

try:
    from script_normalizer import WPM_BY_LANGUAGE
except ImportError:  # pragma: no cover - only if the package is broken
    # Keep the tool usable rather than crashing the pipeline, but say so loudly.
    WPM_BY_LANGUAGE = {"english": 135, "hindi": 115, "telugu": 110, "default": 120}
    print("[WARN] Could not import script_normalizer; using a built-in copy of the "
          "WPM table. Fix the import - two copies is how they drift apart.",
          file=sys.stderr)

TOLERANCE = 0.10  # the EIC's +/-10% gate


def wpm_for(language):
    return WPM_BY_LANGUAGE.get((language or "english").strip().lower(),
                               WPM_BY_LANGUAGE.get("default", 120))


def compute(duration_minutes, language="English"):
    """Return the target word count and the band the EIC will accept."""
    try:
        duration = float(duration_minutes)
    except (TypeError, ValueError):
        raise ValueError(f"duration must be a number, got {duration_minutes!r}")
    if duration <= 0:
        raise ValueError(f"duration must be positive, got {duration}")

    wpm = wpm_for(language)
    target = int(round(duration * wpm))
    return {
        "language": (language or "English").strip().title(),
        "duration_minutes": duration,
        "wpm": wpm,
        "target_word_count": target,
        "min_acceptable": int(round(target * (1 - TOLERANCE))),
        "max_acceptable": int(round(target * (1 + TOLERANCE))),
        "tolerance_pct": int(TOLERANCE * 100),
    }


def check(actual_words, duration_minutes, language="English"):
    """Does an actual word count pass the gate? Returns (ok, result_dict)."""
    r = compute(duration_minutes, language)
    actual = int(actual_words)
    r["actual_word_count"] = actual
    r["drift_pct"] = round((actual - r["target_word_count"]) / r["target_word_count"] * 100, 1)
    r["estimated_runtime_minutes"] = round(actual / r["wpm"], 2)
    r["passes"] = r["min_acceptable"] <= actual <= r["max_acceptable"]
    return r["passes"], r


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    as_json = "--json" in flags
    actual = None
    for i, a in enumerate(sys.argv):
        if a == "--check" and i + 1 < len(sys.argv):
            actual = sys.argv[i + 1]

    if not args:
        print("Usage: python word_target.py <duration_minutes> [language] [--check N] [--json]")
        print()
        print("Examples:")
        print("    python word_target.py 15 English")
        print("    python word_target.py 20 Telugu --json")
        print("    python word_target.py 15 Hindi --check 1680")
        sys.exit(2)

    duration = args[0]
    language = args[1] if len(args) > 1 else "English"

    try:
        if actual is not None:
            passed, r = check(actual, duration, language)
        else:
            r, passed = compute(duration, language), None
    except ValueError as e:
        print(f"[FAIL] {e}")
        sys.exit(2)

    if as_json:
        print(json.dumps(r, indent=2))
    else:
        print(f"  Language            : {r['language']} ({r['wpm']} wpm)")
        print(f"  Duration            : {r['duration_minutes']:g} min")
        print(f"  Target word count   : {r['target_word_count']}")
        print(f"  Accepted band (+/-{r['tolerance_pct']}%): "
              f"{r['min_acceptable']} - {r['max_acceptable']}")
        if passed is not None:
            print(f"  Actual word count   : {r['actual_word_count']} "
                  f"({r['drift_pct']:+.1f}%)")
            print(f"  Estimated runtime   : {r['estimated_runtime_minutes']:g} min")
            print()
            print("  [OK] Within tolerance." if passed else
                  f"  [FAIL] Outside the +/-{r['tolerance_pct']}% gate. "
                  f"{'Cut' if r['actual_word_count'] > r['max_acceptable'] else 'Add'} "
                  f"{abs(r['actual_word_count'] - r['target_word_count'])} words.")

    if passed is False:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
