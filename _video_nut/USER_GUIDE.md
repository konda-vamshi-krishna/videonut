# The VideoNut Production Agency — User Guide

Welcome to your AI-powered production studio. VideoNut turns a single idea into a
researched, scripted, **narrated** and asset-complete video project using
**12 specialized AI agents**.

This guide walks the full lifecycle with a real example:
**"The Irony of OpenAI using Google's Transformer."**

---

## 🎭 The Cast

**Research**

| # | Agent | Command | Does |
|---|---|---|---|
| 1 | 📡 **Topic Scout** | `/topic_scout` | Finds a trending, under-covered topic and creates the project folder |
| 2 | 🎯 **Prompt Agent** | `/prompt` | Turns the topic into focused research questions |
| 3 | 🕵️ **Investigator** ("Sherlock") | `/investigator` | Deep research with sourced facts and video timestamps |

**Creative**

| # | Agent | Command | Does |
|---|---|---|---|
| 4 | ✍️ **Scriptwriter** ("Sorkin") | `/scriptwriter` | Writes the narration with hooks, beats and voice cues |
| 5 | 🎙️ **Narrator** ("Attenborough") | `/narrator` | Renders the script to real voiceover audio |
| 6 | 🎬 **Director** ("Spielberg") | `/director` | Designs shots, timed against the real narration |
| 7 | 🎨 **Visionary** | `/visionary` | Writes AI image/video prompts for scenes with no footage |
| 8 | 🎨 **Thumbnail** ("Canvas") | `/thumbnail` | Click-worthy thumbnail prompts |
| 9 | 🔍 **SEO** ("Ranker") | `/seo` | Titles, descriptions, tags |

**Technical & Core**

| # | Agent | Command | Does |
|---|---|---|---|
| 10 | 🦅 **Scavenger** ("Hunter") | `/scavenger` | Finds and verifies asset URLs |
| 11 | 💾 **Archivist** ("Vault") | `/archivist` | Downloads everything |
| 12 | 🧐 **Editor-in-Chief** ("Chief") | `/eic` | 10-phase audit; gates the whole pipeline |

---

## 📁 Where your files go

Everything lives in **`Projects/<your-project-name>/`**. There is no `_output/`
folder — older versions of this guide said there was; they were wrong.

```
Projects/openai-transformer-irony/
├── topic_brief.md            # Topic Scout
├── prompt.md                 # Prompt Agent
├── truth_dossier.md          # Investigator
├── voice_script.md           # Scriptwriter  ← what the Narrator reads
├── narrative_script.md       # Scriptwriter
├── master_script.md          # Director
├── video_direction.md        # Director
├── visual_prompts.md         # Visionary
├── asset_manifest.md         # Scavenger
├── voiceover_report.md       # Narrator
├── review_report.md          # EIC
├── assets/
│   ├── audio/narration/
│   │   ├── narration_full.mp3      ← your finished voiceover
│   │   ├── narration_cues.md       ← section → timecode map
│   │   ├── narration_manifest.json
│   │   └── segments/
│   ├── 001_clip.mp4
│   └── 002_chart.png
└── .workflow_checkpoint.json # Resume state — do not delete mid-run
```

---

## 🚀 The Workflow

### Step 0 — Set up once

```bash
npx videonut init          # installs Python, FFmpeg, and your chosen AI CLI
cp .env.example .env       # add one TTS API key (optional but recommended)
python _video_nut/tools/check_env.py
```

`check_env.py` tells you which TTS providers are ready. With none configured,
narration still works — it falls back to free voices.

---

### Step 1 — The Topic (`/topic_scout`)

Finds a topic with real search demand and weak competition, then creates the
project folder. Skip it if you already know what you are making.

**Result:** `topic_brief.md`

---

### Step 2 — The Questions (`/prompt`)

Converts the brief into the specific questions the Investigator must answer.

**Result:** `prompt.md`

---

### Step 3 — The Brief (`/investigator`)

Sherlock researches the questions, records every source URL, and timestamps any
video evidence. He also grades the topic's volatility — a fast-moving story gets
re-checked before publication.

**Result:** `truth_dossier.md`

---

### Step 4 — The Soul (`/scriptwriter`)

Sorkin reads the dossier and writes the narration: the hook, the 360-degree
perspective, the emotional beats. He produces **two** files:

- `voice_script.md` — pure narration with section markers and voice cues. This is
  the file that gets read aloud, so it must contain no URLs and no shot directions.
- `narrative_script.md` — the same story with context for the Director.

The voice cues are instructions to the Narrator:

```
[HOOK]
(modulation pitch: low speed: slow tone: grave) In 2017, eight researchers
published a paper. (end modulation)
(pause 2s)
(emphasis) Eight pages. (end emphasis) That is all it took.
```

**Result:** `voice_script.md`, `narrative_script.md`

---

### Step 5 — The Voice, draft pass (`/narrator`)

**Goal:** get a real runtime before anyone times a single shot.

1. Type `/narrator`
2. Select **[2] Draft render**
3. The Narrator renders on a free provider and writes a cue sheet.

This costs nothing and takes under a minute. It exists because word count is a
bad predictor of runtime — pauses, emphasis and delivery routinely move the true
length 15–20 %. The Director now cuts against measured timecodes:

```
HOOK        0:00.0 – 0:18.8
BRIDGE      0:18.8 – 0:31.8
MEAT        0:31.8 – 1:09.0
HUMAN BEAT  1:09.0 – 1:18.6
VERDICT     1:18.6 – 1:30.6
CTA         1:30.6 – 1:38.6
```

If the runtime is far off your target, fix it **now** by cutting or extending the
script — not later by speeding up the voice.

**Result:** `assets/audio/narration/narration_draft.mp3`, `narration_cues.md`

---

### Step 6 — The Vision (`/director`)

Spielberg designs a shot for every paragraph and finds the source URL for every
piece of evidence — now against the real narration timings.

**Result:** `master_script.md`, `video_direction.md`

---

### Step 7 — The Prompts (`/visionary`)

For scenes where no footage exists, the Visionary writes copy-pasteable prompts
for Midjourney, Flux, Sora or Runway, with a consistent style guide.

**Result:** `visual_prompts.md`

---

### Step 8 — The Hunt (`/scavenger`)

Hunter reads `master_script.md` and finds a real, verified URL for every visual.

> *Script:* "Show the 'Attention Is All You Need' paper abstract."
> *Hunter:* finds the arXiv PDF and the exact page.

**Result:** `asset_manifest.md`

---

### Step 9 — The Heist (`/archivist`)

Vault downloads everything with `yt-dlp`, Playwright and friends, organized by scene.

**Result:** `assets/`

---

### Step 10 — The Quality Check (`/eic`)

Chief runs a 10-phase audit: file existence, config compliance, fact-checking
against the dossier, script quality, plagiarism proximity, asset verification,
voice-cue readiness, and pipeline staleness.

- **If it fails:** Chief names the failing stage. Run that agent again — the
  orchestrator resets only the affected checkpoints, so you never redo the whole run.
- **If it passes:** continue to the final narration.

**Result:** `review_report.md`, `review_result.json`

---

### Step 11 — The Voice, final pass (`/narrator`)

1. Type `/narrator`
2. Select **[3] Generate FINAL narration**
3. Review the cost estimate. Nothing is billed until you say yes.
4. The Narrator renders on your production provider, then automatically runs the
   narration quality gate.

**Result:** `assets/audio/narration/narration_full.mp3` — drop it on the timeline
at 00:00:00.000. Every cue-sheet timecode is absolute and gap-free, so your shot
list lines up without re-syncing.

See [docs/VOICE_AGENT.md](docs/VOICE_AGENT.md) for providers, costs and cue grammar.

---

### Step 12 — The Package (`/thumbnail`, `/seo`)

Thumbnail prompts and an optimized title/description/tag set.

---

## 🤖 Running it all at once

```bash
python _video_nut/workflow_orchestrator.py --project "Projects/My Video" --cli gemini
```

| Flag | Effect |
|---|---|
| `--status` | Show which stages are complete |
| `--next` | Show the next command to run |
| `--resume` | Continue from the last checkpoint |
| `--force` | Re-run stages that are already complete |
| `--skip-voice` | Skip both narration passes |
| `--voice-provider elevenlabs` | Force a TTS backend |
| `--cli mock` | Dry-run the whole pipeline with no API calls |

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| Agent produced nothing | `python _video_nut/tools/check_env.py` — your CLI is probably not on PATH |
| "Validation FAILED" at a gate | The message names the file and the missing element. Re-run that agent. |
| Narration has no API key | `cp .env.example .env` and add one key. Or accept the free fallback. |
| Narration is too long | Cut words. Never fix runtime with playback speed. |
| `voiceover: STALE` | You edited the script after rendering. Re-render. |
| Want to start over | Delete `.workflow_checkpoint.json` in the project folder |

---

## 🎉 You are ready to edit

You have a sourced dossier, a cinematic script, a finished voiceover with exact
timecodes, and a folder of verified assets. Open Premiere or DaVinci, drop
`narration_full.mp3` at zero, and cut against `narration_cues.md`.
