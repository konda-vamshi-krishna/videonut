# Contributing to VideoNut

Thanks for wanting to improve VideoNut. This document covers the few things
that are easy to get wrong in this repository.

---

## Repository layout, in one paragraph

`_video_nut/` is the npm package (`package.json` lives there). Everything at the
repository root — `.claude/`, `.gemini/`, `.qwen/`, `.opencode/`, `.hermes/`,
`.codex/`, `.antigravity/`, `.cursorrules`, `.clinerules` — is **compiled
output**, generated from `_video_nut/agents/**` and staged into the package at
publish time. Editing compiled output directly works until the next build
overwrites it.

---

## The one rule: agents are compiled, not hand-written

```bash
# 1. Edit the source of truth
$EDITOR _video_nut/agents/creative/narrator.md

# 2. Recompile every CLI target
python _video_nut/scratch/generate_agents.py

# 3. cli_templates/ is NOT generated - update it by hand if you added an agent
$EDITOR _video_nut/cli_templates/claude/agents/<name>.md
$EDITOR _video_nut/cli_templates/claude/commands/<name>.md
$EDITOR _video_nut/cli_templates/opencode/commands/<name>.md
```

Adding a whole new agent also means touching:

| File | What to add |
|---|---|
| `_video_nut/scratch/generate_agents.py` | an entry in `agent_mappings` |
| `.antigravity/config.toml` | a `<verb> = ".gemini/commands/<name>.toml"` line |
| `_video_nut/workflow_orchestrator.py` | `STAGE_ORDER`, a `run_<stage>()`, checkpoint keys |
| `_video_nut/tools/auto_rework.py` | `STAGE_ORDER`, `AGENT_TO_STAGE`, `stage_to_key` |
| `_video_nut/tools/validators/stale_detector.py` | a staleness rule for its output file |
| `_video_nut/agents/core/eic.md` | a row in the Phase 1 file-existence table |
| `.cursorrules` / `.clinerules` / `README_AGENTS.md` | the roster |

The test suite checks most of this for you — see below.

---

## Running the tests

```bash
python tests/run_tests.py          # everything
python tests/run_tests.py -v       # show each assertion
python tests/run_tests.py voice    # only tests matching "voice"
```

The suite is stdlib-only, never hits the network, and never spends money: all
audio tests use the `mock` TTS provider. Tests that need `ffmpeg` skip cleanly
when it is not on `PATH`, but **please install ffmpeg before submitting audio
changes** — a skipped test proves nothing.

---

## What CI checks

`.github/workflows/ci.yml` runs on every push and pull request. Four jobs, each
one guarding a defect that actually shipped in v1:

| Job | What it does | The bug it prevents |
|---|---|---|
| `tests` | Runs the suite on Python 3.9 and 3.12, byte-compiles everything, and **fails if the audio tests were skipped** | A green suite that quietly tested nothing |
| `package` | `npm run verify-package`, then packs the real tarball and asserts all seven CLI folders are inside it | The published package containing zero agents |
| `agent-drift` | Re-runs `generate_agents.py` and fails if anything changed | Editing a persona and leaving seven stale compiled copies |
| `hygiene` | No author-machine paths, no `.env`, no bytecode, no API-key-shaped strings | Absolute Windows drive paths from the author's machine shipped to users |

Two of these deserve a note.

**`agent-drift` is the one people trip over.** Agent personas live in
`_video_nut/agents/**` and are *compiled* into eight CLI-specific folders. If you
edit a persona and do not re-run the generator, seven copies keep the old text
and only the CLI you happened to test behaves correctly. If this job fails, run:

```bash
python _video_nut/scratch/generate_agents.py
```

and commit the result.

**`package` packs a real tarball rather than trusting `verify-package`.** Those
two can disagree — the audit's worst packaging finding slipped through precisely
because the staging step succeeded while the published artifact was still empty.

---

## Never commit a secret

`config.yaml` is committed, published to npm, and copied into every user's
project folder. It must never contain an API key.

Keys go in `.env` at the repository root. `.env` is gitignored; `.env.example`
documents every variable the pipeline reads. If you add a provider, add its key
to `.env.example` with a link to where the user gets one.

---

## Touching the narration pipeline

The Narrator is the only agent that spends money. Two invariants:

1. **Never synthesize without an explicit confirmation.** Every code path that
   can call a paid API must first print a character count and a cost estimate.
   `--dry-run` must stay free, and `--yes` must stay the only way to skip the prompt.
2. **Runtime problems are script problems.** If narration overruns the target
   duration, the fix is to cut words, never to speed up the voice. Do not add a
   "just make it fit" mode.

Provider adapters live in `_video_nut/tools/audio/providers.py`. A new one needs:
a `ProviderProfile` (dialect, `max_chars`, cost per 1M characters, env keys), a
`synthesize()` implementation, a `check_ready()` that never raises, and an entry
in `REGISTRY`. `max_chars` must be the vendor's real documented per-request
limit — getting it wrong produces truncated audio that nobody notices until the
final render.

---

## Publishing

```bash
cd _video_nut
npm run verify-package    # fails if any agent folder is missing
npm pack --dry-run        # inspect the file list
npm publish
```

`prepack` stages the root CLI folders into the package and `postpack` removes
them again. **Do not publish with `--ignore-scripts`** — that is exactly how
v1.4.0 shipped a tarball containing zero agent command files.

---

## Style

- Python: stdlib first. Every new third-party import must be added to
  `_video_nut/requirements.txt` *and* have a graceful fallback, because users
  install into a bundled interpreter that may be offline.
- No bare `except:`. Catch the exception you mean and say what went wrong.
- Every `requests` call needs a `timeout=`.
- Agent prompts: keep the existing XML-ish `<menu-handlers>` structure. The
  orchestrator and the CLI compilers both parse it.
- Windows matters. Use `os.path.join`, pass `encoding="utf-8"` to every `open()`,
  and never hardcode an absolute path.
