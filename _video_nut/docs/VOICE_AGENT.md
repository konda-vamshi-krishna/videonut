# 🎙️ The Narrator — VideoNut's Voice Agent

The Narrator turns `voice_script.md` into a finished, timecoded voiceover track.
It is the only agent in VideoNut that can spend money, so most of its design is
about not spending it by accident.

---

## Quick start

```bash
# 1. Put a key in .env (repo root). One is enough.
cp .env.example .env
$EDITOR .env          # ELEVENLABS_API_KEY=... or SARVAM_API_KEY=... or GEMINI_API_KEY=...

# 2. See what it would cost. This is free and writes nothing.
python _video_nut/tools/audio/tts_engine.py --project "Projects/My Video" --dry-run

# 3. Render.
python _video_nut/tools/audio/tts_engine.py --project "Projects/My Video" --mode final --yes

# 4. Prove it is good.
python _video_nut/tools/validators/audio_validator.py "Projects/My Video"
```

Or, inside any AI CLI: `/narrator`

No key at all? It still works — the engine falls back to free `edge-tts`, then to
`mock` (silent audio with exact timings), so the Director always has a real runtime.

---

## What you get

| File | What it is |
|---|---|
| `assets/audio/narration/narration_full.mp3` | **The deliverable.** Drop it on the timeline at 00:00:00.000. |
| `assets/audio/narration/narration_cues.md` | Section → timecode map. Cut shots against this. |
| `assets/audio/narration/narration_manifest.json` | Machine-readable timeline for the Director and validators. |
| `assets/audio/narration/segments/` | Per-chunk audio, so you can re-render one sentence instead of the whole track. |
| `voiceover_report.md` | Render report for the Editor-in-Chief: provider, cost, warnings. |

Every timecode is absolute and gap-free — segment *n* starts exactly where
segment *n−1* ended — so the shot list in `master_script.md` lines up without
re-syncing. A regression test asserts this contiguity.

---

## Where it runs in the pipeline

```
investigation → scriptwriting → [🎙️ draft VO] → direction → visionary ∥ scavenging
                                              → archiving → EIC review → [🎙️ final VO]
```

**Draft pass** — free provider, runs right after the Scriptwriter. Its only job
is to produce a real runtime so the Director stops guessing shot lengths from
word count. Never shipped; never fatal if it fails.

**Final pass** — premium provider, runs only after the EIC approves the script.
Rendering before approval means paying twice for every script that gets sent back.

Skip both with `--skip-voice`, or force a backend with `--voice-provider mock`.

---

## Choosing a provider

The Narrator picks automatically based on `audio_language` in `config.yaml`:

```
Indic languages  → sarvam → elevenlabs → gemini → edge → piper → mock
Everything else  → elevenlabs → gemini → openai → edge → piper → mock
```

It walks the chain and takes the first provider that is actually ready (key
present, binary installed). Override with `voice.fallback_chain`.

| Provider | Model | Best at | ~Cost / 1M chars |
|---|---|---|---|
| `elevenlabs` | `eleven_multilingual_v2` | long-form English stability, voice cloning | $100 (v3) / $50 (v3 conv.) |
| `elevenlabs` | `eleven_v3` | expressive delivery, inline audio tags | $100 |
| `sarvam` | `bulbul:v3` | **Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, Bengali, Hinglish** | ~₹30 / 10k chars |
| `gemini` | `gemini-3.1-flash-tts` | best quality per rupee; prompt-steerable | ~$16 |
| `openai` | `gpt-4o-mini-tts` | cheapest credible | ~$15 |
| `edge` | — | free draft passes | free |
| `piper` | — | offline / air-gapped, MIT licensed | free |
| `mock` | — | CI and tests: silent audio, exact timings | free |

**Why Sarvam for Indian languages.** Bulbul scores MOS 4.5–4.6 on Hindi and 4.4
on Tamil, against ElevenLabs' 4.1 and 3.8. It code-switches Hinglish in a single
pass without language tagging, pronounces Indian names correctly, and reads
"lakh"/"crore" as numbers. It is also about a tenth of the price.

**Why Multilingual v2 and not v3 for English masters.** v3 scores higher on
short-clip arenas and is more expressive, but it is non-deterministic and drifts
emotionally across long inputs. ElevenLabs' own documentation names Multilingual v2
as the long-form narration model. Use v3 for a punchy 3-minute video, v2 for a
25-minute documentary.

---

## Cue grammar

The Scriptwriter writes these; the Narrator translates them per provider.

| Cue | Effect |
|---|---|
| `(pause 1.5s)` | **Exactly 1.500 s of real silence**, on every provider |
| `(emphasis) … (end emphasis)` | Stress the enclosed words |
| `(modulation pitch: low speed: slow tone: grave) … (end modulation)` | Delivery style for the enclosed span |
| `(breath)`, `(sigh)`, `(whisper)` | Non-verbal / delivery hint; applies to the next sentence if on its own line |

Two rules that matter:

1. **Cues are spans, not line flags.** `(emphasis) Eight pages. (end emphasis) That is all.`
   emphasises exactly "Eight pages." — the cue opens and closes mid-line and is
   still applied. (An earlier implementation treated cues as line-level flags and
   silently dropped every same-line cue. There is a regression test for this.)
2. **Every opener needs its closer.** An unclosed `(emphasis)` swallows the rest
   of the script into one delivery style. `output_validator.py voice` fails on
   unbalanced spans before you pay for anything.

**Pauses are real silence, not markup.** ElevenLabs does not support SSML
`<break>` at all, and every provider interprets pause markup differently. So the
engine renders speech chunks, generates silence with ffmpeg, and splices them.
`(pause 2s)` is 2.000 seconds everywhere, and the cue sheet timings are exact
rather than approximate.

Provider dialects:

| Cue | ElevenLabs | Azure/GCP | Gemini/OpenAI | Sarvam/Piper |
|---|---|---|---|---|
| emphasis | `[emphasizes]` | `<emphasis level="strong">` | prompt text | punctuation |
| grave | `[sad]` | `<prosody pitch="-10%" rate="slow">` | prompt text | `pace: 0.9` |
| excited | `[excited]` | `<prosody pitch="+15%" rate="fast">` | prompt text | `pace: 1.15` |
| breath | `[sighs]` | `<break time="300ms"/>` | — | — |

---

## Configuration

In `config.yaml`:

```yaml
voice:
  enabled: true
  provider: auto            # auto | elevenlabs | sarvam | gemini | openai | piper | edge | mock
  draft_provider: auto      # provider for the free timing pass
  voice: ""                 # provider voice id / speaker name; "" = VideoNut default
  model: ""                 # e.g. eleven_multilingual_v2, bulbul:v3; "" = default
  pace: 1.0                 # 0.5 - 2.0
  stability: 0.45           # ElevenLabs: lower = more expressive
  similarity: 0.8           # ElevenLabs
  style_prompt: "Authoritative investigative documentary narrator. Measured, credible, never theatrical."
  output_format: "mp3"      # mp3 | wav
  sample_rate: 44100
  normalize_loudness: true
  loudness_lufs: -14.0      # YouTube normalises to roughly -14 LUFS
  max_chars_per_request: 0  # 0 = use each provider's own safe cap
  concurrency: 3
  retries: 3
  cache: true
  draft_pass: true
  cost_ceiling_usd: 25.0    # hard stop before an accidental expensive render
  fallback_chain: []        # [] = use the language-aware default
```

**Never put an API key here.** `config.yaml` is committed, published to npm, and
copied into every user's project. Keys go in `.env`. A test asserts this.

---

## Cost control

| Mechanism | What it does |
|---|---|
| `--dry-run` | Prices the job. Writes nothing, bills nothing. |
| Confirmation prompt | Every billing path shows chars + cost and waits for an explicit yes. `--yes` is the only bypass. |
| `cost_ceiling_usd` | Aborts before exceeding the budget. |
| Content-addressed cache | `sha256(text + voice + model + settings)`. Fix two words, re-render, pay for one chunk. |
| Draft on a free provider | Timing passes cost nothing. |
| Final only after EIC approval | A rejected script never gets a paid render. |

Cache lives at `<project>/.tts_cache/` and is gitignored. Delete it to force a
full re-render, or pass `--force`.

A 30-minute documentary (~4,500 words) costs roughly: ElevenLabs v3 $2.70 ·
Gemini Flash $0.44 · Sarvam ₹81 · Piper/edge/mock free.

---

## Quality gate

`audio_validator.py` runs automatically after the final render and checks:

- the manifest exists and matches the rendered files
- the master track exists and is not a stub
- **every** segment rendered (a partial track is the failure mode you notice last)
- runtime is within `--tolerance` (default 10 %) of `target_duration`
- the track is not silent, and is not clipping (ffmpeg `volumedetect`)
- the cue sheet covers every section

Loudness checks are skipped when `provider == mock`, since mock deliberately
renders silence.

**Runtime drift is a script problem.** If narration overruns, the validator
reports the percentage and the Narrator tells you which section to cut. It will
not speed up the voice to hit a number — that is how documentaries end up sounding
like auctioneers.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Missing API key. Set one of: …` | no `.env`, or key not loaded | `cp .env.example .env` and fill one key. The engine reads `.env` from the project, its parent, and the cwd. |
| `ffmpeg not found` | ffmpeg not on PATH | Install it, or drop the binary in `_video_nut/tools/bin/`, or set `FFMPEG_BINARY`. |
| Narration ignores your cues | unbalanced cue spans | `python _video_nut/tools/validators/output_validator.py voice <path>` |
| Numbers/URLs read out character by character | citations left in the voice script | Move them to `truth_dossier.md`; the voice gate flags this. |
| `voiceover: STALE` | script edited after rendering | Re-render. The audio is of an older script. |
| Track is 20 % too long | script is too long | Cut words. Do not change pace. |
| Voice changes character mid-video | chunks too large on an expressive model | Lower `max_chars_per_request`, or switch to `eleven_multilingual_v2`. |

---

## Extending: adding a provider

In `_video_nut/tools/audio/providers.py`:

1. Add a `ProviderProfile`: `dialect` (`plain` / `audio_tags` / `ssml` / `style_prompt`),
   `max_chars` (**the vendor's real documented per-request cap**), cost per 1M
   characters, and the env var names for its key.
2. Implement `synthesize(text, settings) -> bytes`.
3. Implement `check_ready() -> (bool, str)`. It must never raise — it runs in
   `check_env.py` and in the agent menu.
4. Register it in `REGISTRY`, and add it to `fallback_chain` defaults if it
   should be auto-selected.
5. Add the key to `.env.example` with a link to where the user gets one.
6. Add its `max_chars` to the assertion in `tests/run_tests.py`.

Getting `max_chars` wrong is the classic bug: the API silently truncates, and
nobody notices until the last sentence of a 25-minute documentary is missing.
