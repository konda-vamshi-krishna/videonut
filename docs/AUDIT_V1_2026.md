# VideoNut v1 — Comprehensive Audit

**Audited version:** 1.4.0 (commit `761110c`)
**Audit date:** 28 September 2026
**Scope:** entire repository — packaging, installer, orchestrator, agent prompts, tools, validators, config, docs, repo hygiene
**Outcome:** 1 critical defect, 4 high, 7 medium, plus a new Narrator (TTS) agent designed, implemented and wired into the pipeline.

---

## 0. Executive summary

VideoNut v1 is a genuinely well-structured idea: a supervised multi-agent pipeline where an Editor-in-Chief gates every stage, checkpoints make the run resumable, and staleness detection stops downstream work from being built on a changed script. That skeleton is sound and most of this audit leaves it alone.

The problems are in the seams.

The single worst finding is that **the published npm package could not work**. `package.json` promises to ship the agent command folders, and `bin/videonut.js` copies them at install time — but nothing ever put them inside the package directory, and every copy is guarded by `if (existsSync(src))`. So `npx videonut init` copied nothing, printed "Installation complete", and left the user with a pipeline that has no agents. It failed silently, which is why it survived a release.

The second theme is **two sources of truth that disagree**. There are two validators with different contracts for the same files; `file_validator.py` rejects 3 of the 4 files the orchestrator's own mock mode produces. The docs claim 5, 7, 10 and 11 agents in four different places. Agent prompts are compiled into eight CLI-specific folders by a script that lives in `scratch/`, is wired to no npm script or CI, and does not emit two of the folders it needs to.

The third theme is that **the pipeline stopped at text**. The Scriptwriter emitted `voice_script.md` — complete with `(pause 1.5s)` and `(modulation pitch: low tone: grave)` cues, and an EIC check that audits those cues "for AI voice cloning" — and then nothing ever read them. The user was left to paste the script into a TTS website by hand, losing the cues, the section timings and any chance of the Director cutting shots against a real runtime.

This audit fixes the critical and high findings, and adds the missing stage: a **Narrator** agent that turns `voice_script.md` into a finished, timecoded voiceover track.

**Round two (§7) audited the agents against each other** rather than each against its own file, and found a worse defect than F1: **an EIC rejection could be read as an approval**. `auto_rework` returned the same value for "approved" and "I could not work out what happened", and the orchestrator treated silence as a pass. Five of six failure fixtures — a missing verdict file, malformed JSON, an unrecognised agent name, a rejection naming no agent, and the abbreviations the EIC's own prompt tells it to use — all printed `[OK]` and exited 0. The pipeline failed open, on the one control that exists to stop bad work shipping. It now fails closed.

Round two also found that **the two halves of the pipeline disagreed about how fast people talk**, in a way that made the narration gate reject correct Telugu and Hindi scripts, and that `narration_cues.md` — the whole reason the free draft render exists — had no reader.

**§8 revises the TTS choice for long scripts on modest hardware:** **Kokoro-82M**, Apache-2.0, 300 MB, CPU-only, UTMOS 4.44, zero cost per render, with Sarvam retained for Telugu.

### Findings at a glance

| # | Severity | Finding | Status |
|---|---|---|---|
| F1 | 🔴 Critical | Published npm package contains zero agent command files | **Fixed** |
| F2 | 🟠 High | `subprocess.run(list, shell=True)` silently discards the agent prompt on POSIX | **Fixed** |
| F3 | 🟠 High | Two validators, conflicting contracts; `file_validator.py` fails on the pipeline's own output | **Fixed** |
| F4 | 🟠 High | Author's absolute `G:\youtuber\...` paths shipped to every user | **Fixed** |
| F5 | 🟠 High | No voiceover stage — the pipeline's cue grammar had no consumer | **Implemented** |
| F6 | 🟡 Medium | Compiled `.pyc` tracked in git and published to npm; `.gitignore` missing `.env` | **Fixed** |
| F7 | 🟡 Medium | Agent fan-out generator is unreferenced, incomplete, and hardcodes stale model IDs | **Partially fixed** |
| F8 | 🟡 Medium | Docs contradict each other on agent count, output folders, and status | **Fixed** |
| F9 | 🟡 Medium | `requirements.txt` omits PyYAML although config parsing needs it | **Fixed** |
| F10 | 🟡 Medium | No tests, no CI | **39-test suite + GitHub Actions** |
| F11 | 🟡 Medium | `ensure_config_sync` rewrites shared config by line-prefix string replacement | **Documented** |
| F12 | 🟡 Medium | Bare `except:` in `article_screenshotter.py`; dead Nitter dependency | **Documented** |
| F13 | 🔴 Critical | An EIC *rejection* could be read as an approval — the pipeline failed open | **Fixed** |
| F14 | 🟠 High | The EIC's agent vocabulary matched nothing the rework engine knew | **Fixed** |
| F15 | 🟠 High | Two different words-per-minute tables — the gate rejected correct Telugu/Hindi scripts | **Fixed** |
| F16 | 🟡 Medium | `/visionary` and `/narrator` had no inbound handoff; `narration_cues.md` had no reader | **Fixed** |
| F17 | 🟡 Medium | Menu items without `triggers=`; dead letter-codes in `seo.md` / `thumbnail.md` | **Partially fixed** |
| F18 | 🟡 Medium | Piper profile claimed an MIT licence that no longer applies | **Fixed** |

---

## 1. Critical

### F1 — The published package shipped without its agents

**Severity: Critical. Impact: `npx videonut init` produced a non-functional install.**

Three facts that are individually fine and jointly fatal:

1. `package.json` lives in `_video_nut/`, so npm packs from `_video_nut/` as the package root.
2. `package.json` `files[]` lists `.gemini/`, `.qwen/`, `.claude/`, `.opencode/`, `.antigravity/`, `workflows/`, `CONTRIBUTING.md` and `LICENSE`.
3. None of those exist inside `_video_nut/`. They are generated into the **repository root** by `scratch/generate_agents.py`. `workflows/`, `CONTRIBUTING.md` and `LICENSE` never existed in the package at all.

`bin/videonut.js` then does:

```js
const packageRoot = path.join(__dirname, '..');        // = _video_nut/
const cliFolders = ['.gemini', '.qwen', '.claude', '.opencode', '.antigravity'];
for (const folder of cliFolders) {
    const src = path.join(packageRoot, folder);
    if (existsSync(src)) { copyDir(src, dest); success(`Copied ${folder}/`); }
}
```

Every `existsSync` returns false. The loop copies nothing, logs nothing, and the installer proceeds to print a success banner. The user gets `_video_nut/` with agent *personas*, but no `/investigator` or `/scriptwriter` slash commands in any CLI — the entire user-facing interface.

**Fix — three layers, because one was not enough:**

1. **`_video_nut/scripts/prepack.js`** stages the root CLI folders plus `LICENSE`, `CONTRIBUTING.md` and `.env.example` into the package, creates the missing `workflows/`, purges `__pycache__`, and **exits non-zero if anything required is missing**. Wired to the `prepack` lifecycle hook, so it runs automatically on `npm pack` and `npm publish`; `postpack` removes the staged copies again so they are never committed twice.
2. **`npm run verify-package`** runs the same check on demand, for CI.
3. **`bin/videonut.js` now counts what it copied.** If zero CLI folders landed, it prints a real error explaining the package is broken, links the issue tracker, gives a git-clone workaround, and exits 1. This class of bug can no longer be silent.

Verified: `npm pack --dry-run` went from missing all agent folders to **176 files / 612 kB**, including `.claude/commands/narrator.md`, all 12 `.gemini/commands/*.toml`, and `tools/audio/`, with zero `.pyc`.

---

## 2. High

### F2 — `shell=True` with a list argument

`workflow_orchestrator.py:138` invoked every agent like this:

```python
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
```

where `cmd` is a **list**. On POSIX, `subprocess` with `shell=True` executes `/bin/sh -c cmd[0]` and passes the remaining elements as `$0`, `$1`… to the shell — they are not arguments to the program. So `["gemini", "-p", "<the entire agent prompt>"]` ran bare `gemini` and **silently dropped the prompt**. The agent was invoked with no instructions.

On Windows this happened to work, which is presumably why it shipped.

**Fix:** `shell=False` (the default), plus `errors='replace'` so a stray byte in agent output cannot crash the run, plus a comment explaining the footgun. A regression test now greps the file for `shell=True` outside comments.

### F3 — Two validators with contradictory contracts

The repository contains two validation systems:

| | `_video_nut/file_validator.py` | `_video_nut/tools/validators/output_validator.py` |
|---|---|---|
| Called by | nothing in the pipeline | the orchestrator's `run_validation_gate()` |
| `truth_dossier.md` | requires `Investigation Questions`, `Findings`, `The Angle`, `The Conflict` | requires ≥1 URL and ≥3 list items |
| `narrative_script.md` | requires `[HOOK] [BRIDGE] [MEAT] [HUMAN BEAT] [VERDICT] [CTA]` | requires ≥2 markers |
| `master_script.md` | requires `[NARRATION: "..."]` blocks | requires ≥500 bytes and some structure |

Run against the orchestrator's own mock output, `file_validator.py` **fails 3 of 4 files**. Only `asset_manifest.md` passes. Neither validator matches the templates in the agent prompts.

This is worse than having no validator: a maintainer who runs `file_validator.py` concludes the pipeline is broken; a maintainer who trusts the orchestrator's gates concludes it is fine. Both are reading real output.

**Resolved in v1.5.2.** Investigating properly changed the diagnosis. F3 was described above as "two validators disagree", but the deeper defect was that **the orchestrator's mock produced artifacts that neither validator would accept**:

- `truth_dossier.md` had no `## Investigation Questions` or `## Findings` headings, though `investigator.md` declares that structure MANDATORY.
- `narrative_script.md` was missing `[BRIDGE]` and `[VERDICT]`, two of the five beat markers `scriptwriter.md` specifies.
- `master_script.md` used `Narration: …` prose instead of the `[NARRATION: "…"] [VISUAL: … [Source: …]]` format `director.md` declares.

So every mock run validated against a fake that did not resemble real agent output. Mock mode gave false confidence, and `file_validator.py` looked broken when it was partly telling the truth.

Three changes:

1. **The mock now matches the real contracts.** A mock run produces artifacts shaped exactly as the agent prompts specify.
2. **`output_validator.py` is the single implementation**, extended with `validate_master_script()` and a `project` mode that sweeps every artifact and prints one line each.
3. **`file_validator.py` is now a deprecation shim.** It keeps both CLI modes and its old importable names, but every check delegates. Its genuinely stale requirements are gone: it demanded `The Angle` and `The Conflict` sections that `investigator.md` has *never* produced — which is why it failed on correct output.

Before and after, on the same project folder:

```
# before                                   # after
[FAIL] truth_dossier.md   missing sections  [OK] truth_dossier.md    3 URLs, 15 items
[FAIL] narrative_script.md missing markers  [OK] narrative_script.md valid structure
[FAIL] master_script.md   no narration      [OK] master_script.md    3 narration, 3 visual
[OK]   asset_manifest.md                    [OK] asset_manifest.md   2 verified URLs
exit 1                                      exit 0
```

Guarded by three tests, including one that renders a project through the mock agents and validates it with the production validator — so the mock and the agent contracts can no longer drift apart silently. It was confirmed to fail when the mock is broken.

### F4 — Author's machine paths shipped to users

- `start_videonut.bat` set `PATH` from `G:\youtuber\work_space\AI _TEAM\_video_nut\python` and launched `python "G:/youtuber/.../check_env.py"`. Nobody else has a `G:` drive with that layout, so the launcher was dead on arrival for every user who downloaded the repo as a zip.
- `.cursorrules` and `.clinerules` gave all 11 agents as `file:///g:/youtuber/work_space/AI%20_TEAM/...` links. In Cursor these resolve to nothing on any other machine.

**Fix:** the batch file now derives everything from `%~dp0` (its own directory) and works from any drive. `.cursorrules` / `.clinerules` were rewritten with workspace-relative paths, updated to 12 agents, given the pipeline order, and given an explicit spend protocol for the Narrator. A regression test walks the whole tree and fails if any `g:/youtuber` string reappears.

### F5 — The pipeline had no voice

Covered in full in [§5](#5-the-narrator-agent). In summary: `scriptwriter.md` produced `voice_script.md` with a precise cue grammar, `eic.md` audited those cues "for AI voice cloning", and no code anywhere read the file. The most expensive manual step in the whole workflow — producing narration — sat outside the automation, and because the Director had no real runtime, every shot timing was guessed from word count.

---

## 3. Medium

### F6 — Repository hygiene

- **11 compiled `.pyc` files were tracked in git** and published to npm, including bytecode of modules that no longer matched their source.
- `.gitignore` had no `__pycache__/`, no `*.pyc`, and **no `.env`** — in a project that was about to start handling API keys.
- No `.npmignore`, so `files[]` whitelisting pulled bytecode into the tarball.

**Fix:** `.pyc` untracked (`git rm --cached`), `.gitignore` extended with bytecode, `.env*`, and `.tts_cache/`, `.npmignore` added, and `prepack.js` purges `__pycache__` before packing. Two regression tests assert no tracked `.pyc` and that `.env` is ignored.

### F7 — The agent fan-out is compiled, but nothing says so

`_video_nut/scratch/generate_agents.py` compiles `_video_nut/agents/**` into eight targets: `.claude/commands`, `.claude/skills/<n>/SKILL.md`, `.qwen/commands`, `.opencode/agents`, `.hermes/skills`, `.gemini/commands/*.toml`, `.codex/AGENTS.md`, `.opencode.json`.

Problems:

- It lives in `scratch/`, the universal signal for "throwaway". It is in fact load-bearing.
- No npm script, no CI, no mention in any README. A contributor editing `.claude/commands/eic.md` directly would have their work erased by the next run.
- It does **not** emit `_video_nut/cli_templates/**`, which `setup.js` copies. So two parallel agent trees drift apart.
- It hardcodes `anthropic/claude-3.5-sonnet` and `gpt-4o` as default models — both long superseded in 2026.
- `.antigravity/config.toml` is maintained entirely by hand.

**Partially fixed:** added `npm run build-agents`, added the narrator to `agent_mappings`, hand-updated `cli_templates/` and `.antigravity/config.toml`, and documented the whole build step in `CONTRIBUTING.md` and `README_AGENTS.md`. A regression test now asserts that **every** persona in `agents/**` has a compiled artifact in every CLI target, so the next drift fails the suite instead of silently shipping.

**Left for the maintainer:** move `generate_agents.py` out of `scratch/`, teach it to emit `cli_templates/`, and refresh the default model IDs.

### F8 — Documentation contradicts itself

| Source | Claim |
|---|---|
| `USER_GUIDE.md` | "five specialized AI agents" — then lists seven |
| `README.md` | 11 agents |
| `package.json` | 10 agents |
| Reality (pre-audit) | 11 personas, 9 in the pipeline |

`USER_GUIDE.md` also told users their files appear in `_output/`, a folder the code never creates (it is `Projects/<name>/`), omitted Topic Scout, Prompt Agent, SEO and Thumbnail entirely, and had two sections both numbered "Step 3". `temp_implementation.md` listed all six phases as "Not Started" although the tools for them exist and run.

**Fix:** counts reconciled to 12 everywhere, `README_AGENTS.md` rewritten with the real directory map and the regeneration step, `package.json` description corrected, and this audit plus `docs/VOICE_AGENT.md` added.

### F9 — `requirements.txt` missing PyYAML

Every tool that reads `config.yaml` needs a YAML parser; `requirements.txt` did not list one. The new TTS engine therefore ships a `_mini_yaml` fallback that handles simple `key: value` blocks, so it works on a bare interpreter — but that fallback is a workaround for a packaging omission, not a design choice. PyYAML is now declared, with a comment explaining the fallback.

### F10 — No tests, no CI

There was no test directory, no CI workflow, and no way to know whether a change broke the pipeline short of running it end to end against paid APIs.

**Fix:** `tests/run_tests.py` — 27 tests, stdlib only, no network, no spend (every audio test uses the `mock` provider). It covers the script normalizer's tokenizer, provider routing and readiness, end-to-end render with manifest/timeline assertions, cache behaviour, all four validators, staleness detection, orchestrator stage wiring, config secret-hygiene, agent fan-out completeness, package completeness, and the two regression bugs from this audit (`shell=True`, hardcoded paths). Tests needing `ffmpeg` skip cleanly rather than failing.

```
  27/27 passed
```

### F11 — `ensure_config_sync` edits shared config by string replacement

The orchestrator keeps `config.yaml`'s `current_project` in sync by reading the file, finding the line that starts with `current_project:`, and rewriting it. Two problems: it mutates a file shared by every project (so two concurrent runs fight over it), and line-prefix replacement is fragile — a commented-out `current_project:` or an indented one under another key would be silently corrupted.

Not fixed here because the fix is a design change (per-project state file) with wider blast radius than an audit should take on. Documented so it is a decision rather than an accident.

### F12 — Miscellaneous code smells

- Three bare `except:` clauses in `tools/downloaders/article_screenshotter.py`. A bare `except` also swallows `KeyboardInterrupt` and `SystemExit`, so Ctrl-C during a screenshot run does nothing visible.
- `social_media_reader.py` depends on `ntscraper` and public Nitter mirrors, essentially all of which are dead. This tool cannot work as written.
- **Good news:** every `requests` call in the codebase does set a `timeout`, and `copyDir` in the installer correctly skips `__pycache__`. Those were checked and are fine.

---

## 4. Text-to-speech model selection

The brief was to research current TTS options and pick one. The honest answer is that picking exactly one would be wrong for this project, and the reason is in VideoNut's own config file: `audio_language` already offers English plus Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi and Bengali. No single vendor is best across that range.

### The 2026 landscape

Ranked by the Artificial Analysis TTS arena (September 2026):

| Model | Arena Elo | Price / 1M chars | ≈ Cost per finished minute | Notes |
|---|---|---|---|---|
| Cartesia Sonic 3.6 | ~1273 | — | — | Arena #1; tuned for realtime conversation, not long-form |
| Gemini 3.8 Flash TTS | ~1265 | $16.49 | ~$0.025 | Prompt-steerable delivery |
| Gemini 3.1 Flash TTS | ~1199–1204 | ~$16 | ~$0.024 | 30 prebuilt voices, returns raw PCM |
| ElevenLabs v3 Conversational | ~1196 | $50 | ~$0.045 | |
| ElevenLabs v3 | ~1167 | $100 | ~$0.090 | Inline audio tags, 70+ languages |
| OpenAI tts-1 / gpt-4o-mini-tts | — | ~$15 | ~$0.014 | Cheapest credible option |

Arena Elo measures short-clip preference. It does **not** measure what matters most for a 20-minute documentary: whether the voice stays consistent from minute 2 to minute 18. On that axis the ranking inverts. ElevenLabs' own model documentation names **Multilingual v2**, not the higher-scoring v3, as their long-form narration model, because v3 is non-deterministic and drifts emotionally across long inputs. Community long-form testing agrees.

For Indian languages the global leaderboard is simply the wrong leaderboard. **Sarvam AI's Bulbul** scores MOS 4.5–4.6 on Hindi, 4.4 Tamil and 4.3 Telugu, against ElevenLabs' 4.1 Hindi and 3.8 Tamil. It handles Hinglish and Tanglish code-switching in a single pass (no language tagging), pronounces Indian names correctly, and reads "lakh" and "crore" as numbers rather than spelling them. It costs roughly **₹30 per 10,000 characters — about a tenth of ElevenLabs**.

### Decision: one abstraction, five backends, language-aware routing

| Role | Provider / model | Why it wins that role |
|---|---|---|
| **Default English master** | ElevenLabs `eleven_multilingual_v2` | The vendor's own long-form-stability pick; voice cloning; holds character across 30 minutes |
| **Expressive English** | ElevenLabs `eleven_v3` | Audio tags (`[excited]`, `[whispers]`, `[sighs]`) map 1:1 onto VideoNut's existing cue grammar |
| **All Indic languages** | **Sarvam `bulbul:v3`** | Beats ElevenLabs on MOS for every Indian language VideoNut supports; native code-switching; ~10× cheaper |
| **Budget / high volume** | Google `gemini-3.1-flash-tts` | Near-top quality at ~$16/1M chars; delivery steerable by prompt |
| **Draft / offline / CI** | `edge-tts`, Piper (MIT), `mock` | Free timing pass, no API key, keeps the pipeline testable and the test suite free |

Cost for a 30-minute documentary (~4,500 words, ~27,000 characters):

| Provider | Cost |
|---|---|
| ElevenLabs v3 | ~$2.70 |
| ElevenLabs Flash v2.5 / v3 Conversational | ~$1.35 |
| Gemini 3.1 Flash TTS | ~$0.44 |
| Sarvam Bulbul | ~₹81 (~$0.95) |
| Piper / edge-tts / mock | free |

### Implementation notes that shaped the code

These are vendor behaviours that a naive integration gets wrong:

- **Per-request character limits differ by an order of magnitude** — `eleven_v3` 3,000 (safe) / 5,000 (documented), `eleven_multilingual_v2` 10,000, `eleven_flash_v2_5` 40,000, Sarvam **2,500 hard**, Gemini per-request token budget. Each provider profile declares its own `max_chars` and the chunker respects it. A test asserts these against the vendors' documented caps, because getting one wrong produces truncated audio that nobody notices until the final render.
- **ElevenLabs does not support SSML `<break>`.** Pacing comes from punctuation and line breaks only. This is the single most important constraint on the design, and it is why VideoNut renders `(pause 1.5s)` as a **real ffmpeg silence segment** spliced between clips rather than as any provider's pause markup. The consequence is that a `(pause 2s)` is exactly 2.000 seconds on every provider, and the cue sheet timings are exact rather than approximate.
- **Gemini returns raw PCM**, not a container: L16, 24 kHz, mono, 16-bit. It must be wrapped in a 44-byte WAV header before ffmpeg will touch it.
- **Chunks above ~2,000 characters drift emotionally** on v3. The chunker merges sentences up to the provider limit but never across a section boundary.

---

## 5. The Narrator agent

### What it does

Reads `{project}/voice_script.md`, renders it through an AI TTS model, and hands the user a finished, timecoded narration track.

```
voice_script.md
      │
      ├─ script_normalizer.py   strip markdown, parse section markers,
      │                         tokenize cue spans, convert (pause Ns)
      │                         into silence segments
      ├─ providers.py           pick a backend for the language, chunk to its
      │                         real limit, translate cues into its dialect
      ├─ tts_engine.py          synthesize (cached, concurrent, cost-capped),
      │                         splice silences, concatenate with ffmpeg
      └─ audio_validator.py     prove the result is complete, audible and on-target
      │
      ▼
assets/audio/narration/narration_full.mp3   ← the deliverable
assets/audio/narration/narration_cues.md    ← section → timecode map
assets/audio/narration/narration_manifest.json
assets/audio/narration/segments/            ← per-chunk, for surgical re-cuts
voiceover_report.md                         ← EIC-facing render report
```

### Where it sits in the pipeline

It runs **twice**, and that is the central design decision.

```
investigation → scriptwriting → [VOICE: draft] → direction → visionary ∥ scavenging
                                                → archiving → EIC review → [VOICE: final]
```

- **Draft pass**, immediately after scriptwriting, on a free provider. Its only job is to produce a *real* runtime. Before this, the Director timed shots from word count — a guess that is routinely 15–20 % off once pauses and delivery are real. Now the Director cuts against `narration_cues.md`, where every section has an exact in/out timecode.
- **Final pass**, only after the EIC approves the script, on the premium provider. Rendering earlier would mean paying twice for every script that gets sent back — and in the mock end-to-end run the EIC *does* send it back once before approving.

`auto_rework.py` resets both narration checkpoints whenever a rework touches investigation, scriptwriting or voiceover, and `stale_detector.py` gained a `voiceover` rule that fires when `voice_script.md` is newer than `narration_manifest.json`. Shipping audio of a superseded script is the most expensive failure mode this pipeline has; it now takes two independent mechanisms to reach it.

### Cue translation

VideoNut's cue grammar is provider-agnostic; each backend declares a *dialect* and the renderer translates:

| VideoNut cue | ElevenLabs (`audio_tags`) | Azure/GCP (`ssml`) | Gemini/OpenAI (`style_prompt`) | Sarvam/Piper (`plain`) |
|---|---|---|---|---|
| `(emphasis) … (end emphasis)` | `[emphasizes]` | `<emphasis level="strong">` | "emphasise this line" | punctuation only |
| `(modulation tone: grave)` | `[sad]` | `<prosody pitch="-10%" rate="slow">` | "slow, grave delivery" | pace 0.9 |
| `(modulation pitch: high speed: fast)` | `[excited]` | `<prosody pitch="+15%" rate="fast">` | "quick, excited" | pace 1.15 |
| `(breath)` / `(sigh)` | `[sighs]` | `<break time="300ms"/>` | — | — |
| `(pause 1.5s)` | **real 1.500 s silence, every provider** | | | |

### Safety rails

The Narrator is the only agent in VideoNut that can spend money. The rails are deliberate:

1. **Never silent spend.** Every path that can bill prints character count, chunk count and cost estimate first. `--dry-run` is free; `--yes` is the only way to skip the prompt.
2. **Cost ceiling.** `voice.cost_ceiling_usd` aborts before exceeding a budget.
3. **Content-addressed cache.** `sha256(text + voice + model + settings)` — re-rendering after a two-word fix bills only the changed chunk. Verified: second full render of the demo billed **0 characters**.
4. **Pre-flight gate.** `output_validator.py voice` runs before synthesis and blocks scripts containing URLs, unbalanced cue spans, or a pile of visual directions — text you would otherwise pay to have read aloud.
5. **Post-flight gate.** `audio_validator.py` proves the track exists, is non-empty, contains every segment, is not silent, is not clipping, and is within tolerance of the target runtime.
6. **Keys in `.env` only.** `config.yaml` is committed, published and copied into every user project. A test asserts it contains no credential-shaped strings.
7. **Runtime problems are script problems.** If narration overruns, the Narrator reports which section to cut. It will not speed up the voice to fit.
8. **Disclosure.** The persona requires telling the user the voice is synthetic, and refuses to clone a real person's voice without stated consent.

### Verification

End-to-end with `--provider mock` on a 252-word, six-section script:

```
Master narration : assets/audio/narration/narration_full.mp3
Runtime          : 00:01:38.600
Chunks           : 14 speech + 4 silence (6.5 s total)
Cache (2nd run)  : 14/14 hits, 0 characters billed

HOOK        0:00.0 – 0:18.8
BRIDGE      0:18.8 – 0:31.8
MEAT        0:31.8 – 1:09.0
HUMAN BEAT  1:09.0 – 1:18.6
VERDICT     1:18.6 – 1:30.6
CTA         1:30.6 – 1:38.6
```

Full pipeline (`workflow_orchestrator.py --cli mock`) runs green including one EIC rework cycle, both narration passes, and the narration quality gate. `tests/run_tests.py`: 27/27.

---

## 6. What changed

**New**

```
_video_nut/agents/creative/narrator.md          the Narrator persona
_video_nut/tools/audio/script_normalizer.py     cue-aware script tokenizer
_video_nut/tools/audio/providers.py             7 backends behind one interface
_video_nut/tools/audio/tts_engine.py            render, cache, splice, report
_video_nut/tools/validators/audio_validator.py  narration quality gate
_video_nut/scripts/prepack.js                   package completeness (fixes F1)
_video_nut/.npmignore                           keeps bytecode out of the tarball
tests/run_tests.py                              27-test regression suite
.env.example                                    documented API keys
CONTRIBUTING.md                                 build steps and invariants
docs/AUDIT_V1_2026.md                           this document
_video_nut/docs/VOICE_AGENT.md                  Narrator reference
```

**Modified**

```
_video_nut/workflow_orchestrator.py   voiceover stage ×2, voice gate, --skip-voice,
                                      --voice-provider, shell=True fix (F2)
_video_nut/tools/validators/output_validator.py   validate_voice_script (reports all
                                      problems at once), validate_narration
_video_nut/tools/validators/stale_detector.py     voiceover staleness rule
_video_nut/tools/auto_rework.py       narrator ↔ voiceover mapping; narration
                                      invalidated by script-level rework
_video_nut/tools/audio/script_normalizer.py       markdown headings and metadata
                                      lines are no longer narrated
_video_nut/tools/audio/providers.py   is_indic() accepts "hi-IN" and "hi", not just "Hindi"
_video_nut/tools/check_env.py         TTS readiness probe (advisory, never fatal)
_video_nut/agents/core/eic.md         narration deliverables in the file table;
                                      mechanical voice-cue and narration audits
_video_nut/config.yaml                voice: block
_video_nut/package.json               v1.5.0, prepack/postpack/test/build-agents scripts
_video_nut/bin/videonut.js            refuses to report success on an empty install
_video_nut/requirements.txt           PyYAML
_video_nut/scratch/generate_agents.py narrator mapping
start_videonut.bat                    %~dp0-relative; narration menu entry
.cursorrules / .clinerules / README_AGENTS.md     rewritten, 12 agents, no absolute paths
.gitignore                            __pycache__, *.pyc, .env, .tts_cache
```

---

---

## 7. Round two — inter-agent consistency

The first pass audited each agent against its own file. This pass audited the agents
**against each other**: what one writes versus what the next one reads, what the EIC
emits versus what the rework engine accepts, and what two halves of the pipeline
believe about the same number.

Every finding below is a place where two components were individually correct and
jointly wrong.

### F13 — 🔴 The pipeline failed open on review

This is the most serious defect found in either pass.

`auto_rework.parse_review_result()` returned `None` to mean "approved". It also
returned `None` when `review_result.json` was missing, when it was malformed, when
the EIC named an agent it did not recognise, and when a rejection carried no agent at
all. The orchestrator's only test was:

```python
if rerun_stage:
    ...rework...
else:
    print("[SUCCESS] EIC APPROVED!")
```

So *absence of evidence was treated as approval*. I reproduced it with six fixtures:
**five of the six failure modes printed `[OK] Rework not required` and exited 0.**
The one that worked was the single case where the EIC happened to spell the agent
name exactly as the engine expected.

Concretely: if the EIC crashed before writing its verdict, VideoNut announced the
video was approved. And since v1.5 added the Narrator, it would then spend real money
rendering final narration for a script no one had signed off.

**Fix.** The two states are now distinct at all three layers:

| Layer | Before | After |
|---|---|---|
| `parse_review_result` | `None` for both | returns a stage, or raises `UndeterminedVerdict` |
| stdout contract | `RERUN_STAGE:` or silence | always one of `REVIEW_STATUS:APPROVED\|REWORK\|UNDETERMINED` |
| orchestrator | `if rerun_stage: … else: approved` | approval must be *stated*; `UNDETERMINED` halts and returns `False` |

Exit code for an unresolvable verdict is now `2`, not `0`. Checkpoints are left
untouched so `--resume` picks up cleanly once the verdict is fixed.

### F14 — 🟠 The EIC spoke a language the rework engine did not

`eic.md` asked `"Which agent? [SCOUT/PROMPT/INV/SCRIPT/DIR/SCAV/ARCH]"`.
`AGENT_TO_STAGE` contained only canonical lowercase names. **Not one of those seven
abbreviations was a key.** Every send-back therefore hit the `None` path above and was
reported as an approval.

The list was also missing VISIONARY, SEO, THUMBNAIL and NARRATOR entirely — four
agents the EIC scores but could not route work back to.

**Fix.** `AGENT_TO_STAGE` now accepts abbreviations, canonical names and common
aliases. `topic_scout` and `prompt` have no automated stage, so they live in
`MANUAL_ONLY_AGENTS` and produce an explicit "re-run this by hand" message instead of
a silent pass. `eic.md` now lists the exact accepted names, documents the
`review_result.json` shape it must write, and warns that rolling back invalidates
downstream narration. A test asserts the two vocabularies stay in sync.

### F15 — 🟠 Two words-per-minute tables, and the Indic scripts paid for it

The scriptwriter sizes a script with one table. The narrator measures it with another.
They disagreed:

| Language | Agents said | Normalizer said |
|---|---|---|
| English | 135 | 150 |
| Telugu | 110 | 125 |
| Hindi | 115 | 135 |
| Others | 120 | 140 |

A *correctly sized* script then failed the ±10% narration gate:

| Language | Target words | Estimated runtime | Drift | Gate |
|---|---|---|---|---|
| English | 2,025 | 13.5 min | −10.0% | borderline |
| Telugu | 1,650 | 13.2 min | −12.0% | **FAIL** |
| Hindi | 1,725 | 12.8 min | −14.8% | **FAIL** |
| Marathi / Bengali | 1,800 | 13.3 min | −11.1% | **FAIL** |

The gate rejected correct Telugu and Hindi scripts — precisely the languages this
project targets. English squeaked through on the boundary, which is why it had not
been noticed.

**Fix.** `WPM_BY_LANGUAGE` in `script_normalizer.py` is now the single source of truth
and matches the agents (135 / 115 / 110 / 120). `LIFECYCLE.md`'s flat "Duration × 135"
rule has been replaced with the per-language table and an explanation of why Indian
languages need a lower rate. A regression test reads all four files and fails if any
one of them drifts.

### F16 — 🟡 Orphaned agents and write-only artifacts

Tracing "who names whom as the next step" left two agents unreachable and three files
with no reader:

| Orphan | Problem |
|---|---|
| `/visionary` | No agent ever tells the user to run it (pre-existing) |
| `/narrator` | Same — introduced by v1.5's own work |
| `narration_cues.md` | **Zero readers.** The Director was never told to time shots against it |
| `visual_prompts.md` | Only the EIC's existence check; the Visionary's images never reach `asset_manifest.md` |
| `youtube_optimization.md` | No readers, and absent from the EIC's audit table |

`narration_cues.md` is the important one. The entire justification for the free draft
narration pass is that the Director should cut to **measured** speech durations rather
than a words-per-minute guess — and nothing instructed it to.

**Fix.** The Scriptwriter now hands off to `/narrator` (draft), the Director now reads
`narration_cues.md` as its timing source, warns loudly when it is falling back to
estimates, reconciles disagreements over 10% in favour of the measurement, and hands
off to `/visionary`. `visual_prompts.md` and `youtube_optimization.md` remain open
items — see §9.

### F17 — 🟡 The menu/handler contract is only half-enforced

`eic.md` has eight menu items but only handler `[1]` carries a `triggers=` attribute;
`[2]`–`[6]` are bare `<handler type="action">` identified by prose, appear out of order
(…4, 6, 5), and `[7] Dismiss` / `[8] Redisplay` have no handler at all. `seo.md` and
`thumbnail.md` have **zero** `triggers` attributes and reference letter codes `[OS]`
and `[CT]` that appear in no menu — the same dead convention already removed from the
user guide. Partially addressed; the full sweep is an open item.

### F18 — 🟡 A licence claim that expired

`providers.py` described Piper as "Local MIT-licensed neural TTS". `rhasspy/piper` was
archived in October 2025; the maintained fork `OHF-Voice/piper1-gpl` is **GPL-3.0**.
For a package distributed on npm that distinction matters. The note now states it
plainly, and a test guards against the old wording returning.

---

## 8. Revised TTS recommendation — long scripts, low compute

The original selection optimised for quality with cost as a secondary concern. Re-run
against the real workload — **15–20 minute scripts, rendered often, on modest
hardware** — the answer changes.

**What a 15–20 minute script actually is:**

| Length | Words (@135 wpm) | Characters |
|---|---|---|
| 15 min | ~2,025 | ~12,150 |
| 20 min | ~2,700 | ~16,200 |

And at catalogue scale (~1,020 minutes of finished video ≈ 826,000 characters):

| Provider | Cost for ~826k chars | Notes |
|---|---|---|
| ElevenLabs v3 | ~$83 | best quality, per-render billing |
| Gemini Flash TTS | ~$14 | good value |
| Sarvam `bulbul:v3` | ~₹2,480 (~$29) | the only strong Telugu option |
| **Kokoro-82M** | **$0** | local, offline, unlimited re-renders |

### Selected: Kokoro-82M for English

| | |
|---|---|
| Parameters | 82M (StyleTTS2 + ISTFTNet) |
| Size | ~300 MB (164 MB FP16) |
| Licence | **Apache-2.0** — safe to ship |
| Hardware | **CPU, ~2 GB RAM. No GPU.** |
| Measured speed | RTF ≈ 0.57–0.67 → **1.5–1.8× real-time** |
| Quality (UTMOS) | **4.44–4.46** — highest of any CPU-class model |
| Cost | zero, forever |

A 15-minute narration renders in roughly 8–10 minutes on a plain CPU; 20 minutes in
about 11–13. That is slower than an API call and free, repeatable and offline —
which is the right trade when you re-render after every script revision.

I have quoted the **measured** real-time factor, not the 3–11× figures in vendor
material. Those come from batch throughput on server hardware.

**Both of Kokoro's documented weaknesses are already neutralised by VideoNut's
design:**

1. *510-token cap per call* — the engine already chunks at sentence boundaries and
   splices with ffmpeg. The `kokoro` profile sets `max_chars=400`, comfortably under.
2. *Drift at paragraph boundaries in sustained 10-minute single-shot generation* —
   VideoNut never does single-shot generation. Every chunk is an independent render.

The weakness that **does** remain: narrow emotional range (~6.5/10) and no voice
cloning. For an authoritative documentary read — measured, even, credible — that
narrowness is closer to an asset than a defect. For character work or dramatic
delivery, use ElevenLabs.

### Telugu is the exception

Kokoro's only Indian language is Hindi. `check_ready()` therefore **refuses** Telugu
rather than mangling it, and names Sarvam in the error. The CPU alternative,
Indic Parler-TTS (Apache-2.0, 22 languages including `te-IN`), needs ~4–6 GB RAM —
heavier than Kokoro and heavier than most laptops enjoy. IndicF5 covers Telugu too but
has a documented duration bug (21 of 30 outputs silent or truncated) and is
gated on Hugging Face; I do not recommend it.

**So: Kokoro for English, Sarvam for Telugu, and the router picks automatically.**

### How to turn it on

```yaml
# config.yaml
voice:
  prefer_local: true     # puts Kokoro at the front of the auto chain
```

```bash
pip install kokoro-onnx soundfile    # ~300 MB on first run, no key, no GPU
```

Two runtimes are supported and tried in order: `kokoro-onnx` (no PyTorch, smallest,
fastest on CPU) then the reference `kokoro` package. Both are imported lazily, so the
module still loads with neither installed and `check_ready()` explains what to do.

Draft passes now use a dedicated free chain — `kokoro → piper → edge → mock` — so a
timing render can never reach for a paid API. A test asserts every provider in that
chain costs `$0.00` per 1,000 characters.

---

## 9. Recommended next steps

Not done here, in priority order:

1. ~~**Resolve F3.**~~ **Done in v1.5.2** — see the F3 entry above.
2. **Move `generate_agents.py` out of `scratch/`**, teach it to emit `cli_templates/**` and `.antigravity/config.toml`, refresh the default model IDs.
3. ~~**Add CI.**~~ **Done in v1.5.2** — `.github/workflows/ci.yml`, four jobs (tests on Python 3.9/3.12, real-tarball package check, agent-drift, hygiene). Green on first run.
4. **Fix F11** with per-project state instead of mutating the shared `config.yaml`.
5. **Rewrite `USER_GUIDE.md`** end to end; it is the most-read and least-accurate file in the repository.
6. **Retire or replace `social_media_reader.py`** — its Nitter backend no longer exists.
7. **Add a Music/SFX agent.** With narration timecodes now exact, scoring a bed against `narration_cues.md` is a small, well-defined next stage.
8. **Finish F17** — give every menu item a `triggers=` attribute, reorder the handlers, and delete the dead `[OS]`/`[CT]` letter codes.
9. **Give `visual_prompts.md` a consumer** — the Archivist should fold the Visionary's generated images into `asset_manifest.md`; today they reach the EIC's existence check and stop.
10. **Add `youtube_optimization.md` to the EIC audit table** so the SEO agent's output is reviewed rather than merely produced.
11. **Ship a Kokoro smoke test in CI** behind an opt-in flag, so the local path is exercised on a real render and not only through `check_ready()`.
