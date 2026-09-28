# VideoNut Complete Lifecycle Documentation

## 📊 SYSTEM OVERVIEW

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           VIDEONUT AGENT PIPELINE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   USER ──────────────────────────────────────────────────────────────────►   ║
║          │                                                                    ║
║          ▼                                                                    ║
║   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐║
║   │ 📡 SCOUT    │────►│ 🎯 PROMPT   │────►│ 🕵️ INVEST  │────►│ ✍️ SCRIPT   │║
║   │ (1st Agent) │     │   AGENT     │     │  IGATOR     │     │  WRITER     │║
║   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘║
║          │                   │                   │                   │        ║
║          │ WRITES            │ READS             │ READS             │ READS  ║
║          ▼                   ▼                   ▼                   ▼        ║
║   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐║
║   │config.yaml  │     │topic_brief  │     │  prompt.md  │     │truth_dossier│║
║   │             │     │    .md      │     │             │     │    .md      │║
║   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘║
║                                                                               ║
║   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐║
║   │ 🎙️ NARRATOR │────►│ 🎬 DIRECTOR │────►│ 🦅 SCAVENGE │────►│ 💾 ARCHIVIST│║
║   │ (draft VO)  │     │             │     │     R       │     │             │║
║   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘║
║          │                   │                   │                   │        ║
║          │ READS             │ READS             │ READS             │ READS  ║
║          ▼                   ▼                   ▼                   ▼        ║
║   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐║
║   │voice_script │     │narrative_   │     │master_script│     │asset_manifes│║
║   │    .md      │     │script.md +  │     │    .md      │     │t.md         │║
║   │             │     │narration_   │     │             │     │             │║
║   │             │     │cues.md      │     │             │     │             │║
║   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘║
║                                                                               ║
║                    ┌─────────────┐     ┌─────────────┐                        ║
║                    │ 🧐 EIC      │────►│ 🎙️ NARRATOR │                        ║
║                    │ (gate)      │     │ (final VO)  │                        ║
║                    └─────────────┘     └─────────────┘                        ║
║                           │                   │                               ║
║                           │ READS             │ WRITES                        ║
║                           ▼                   ▼                               ║
║                    ┌─────────────┐     ┌─────────────┐                        ║
║                    │ALL PREVIOUS │     │narration_   │                        ║
║                    │   FILES     │     │full.mp3     │                        ║
║                    └─────────────┘     └─────────────┘                        ║
║                                                                               ║
║                    ┌─────────────┐     ┌─────────────┐                        ║
║                    │ 🎨 THUMBNAIL│     │ 🔍 SEO      │                        ║
║                    │             │     │             │                        ║
║                    └─────────────┘     └─────────────┘                        ║
║                           │                   │                               ║
║                           └───────┬───────────┘                               ║
║                                   ▼                                           ║
║                          ┌─────────────────┐                                  ║
║                          │youtube_         │                                  ║
║                          │optimization.md  │                                  ║
║                          └─────────────────┘                                  ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 🔐 CONFIG.YAML ACCESS CONTROL

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           WHO CAN MODIFY CONFIG.YAML?                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌──────────────────────────────────────────────────────────────────────┐   ║
║   │                    📡 TOPIC SCOUT (ONLY AGENT)                        │   ║
║   │                                                                       │   ║
║   │   ✅ CAN WRITE TO config.yaml:                                        │   ║
║   │      • projects_folder                                                │   ║
║   │      • current_project                                                │   ║
║   │      • video_format                                                   │   ║
║   │      • target_duration                                                │   ║
║   │      • target_line_count                                              │   ║
║   │      • audio_language                                                 │   ║
║   │      • scope (international/national/regional)                        │   ║
║   │      • country                                                        │   ║
║   │      • region                                                         │   ║
║   │      • industry_tag                                                   │   ║
║   │                                                                       │   ║
║   └──────────────────────────────────────────────────────────────────────┘   ║
║                                      │                                        ║
║                                      │ WRITES                                 ║
║                                      ▼                                        ║
║   ┌──────────────────────────────────────────────────────────────────────┐   ║
║   │                         config.yaml                                   │   ║
║   └──────────────────────────────────────────────────────────────────────┘   ║
║                                      │                                        ║
║                                      │ READ ONLY                              ║
║                                      ▼                                        ║
║   ┌──────────────────────────────────────────────────────────────────────┐   ║
║   │  🎯 Prompt  │ 🕵️ Investigator │ ✍️ Scriptwriter │ 🎬 Director        │   ║
║   │  🦅 Scavenger │ 💾 Archivist │ 🧐 EIC │ 🎨 Thumbnail │ 🔍 SEO         │   ║
║   │                                                                       │   ║
║   │  ❌ CANNOT MODIFY config.yaml                                         │   ║
║   │  ✅ CAN READ all values                                               │   ║
║   │  ✅ CAN CREATE files in {projects_folder}/{current_project}/          │   ║
║   └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 🛠️ AGENT TOOLS MATRIX

```
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                              WHICH AGENT USES WHICH TOOLS?                              ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  TOOL                    │ SCOUT │ PROMPT │ INVEST │ SCRIPT │ DIREC │ SCAV │ ARCH │ EIC ║
║  ────────────────────────┼───────┼────────┼────────┼────────┼───────┼──────┼──────┼─────║
║  google_web_search       │  ✅   │   ✅   │   ✅   │   ❌   │  ✅   │  ✅  │  ❌  │  ❌ ║
║  youtube_search.py       │  ✅   │   ✅   │   ✅   │   ❌   │  ✅   │  ✅  │  ❌  │  ❌ ║
║  caption_reader.py       │  ✅   │   ✅   │   ✅   │   ❌   │  ✅   │  ✅  │  ✅  │  ❌ ║
║  web_reader.py           │  ✅   │   ✅   │   ✅   │   ❌   │  ✅   │  ✅  │  ❌  │  ❌ ║
║  link_checker.py         │  ✅   │   ✅   │   ✅   │   ❌   │  ✅   │  ✅  │  ✅  │  ✅ ║
║  clip_grabber.py         │  ❌   │   ❌   │   ❌   │   ❌   │  ❌   │  ❌  │  ✅  │  ❌ ║
║  image_grabber.py        │  ❌   │   ❌   │   ❌   │   ❌   │  ❌   │  ❌  │  ✅  │  ❌ ║
║  article_screenshotter   │  ❌   │   ❌   │   ❌   │   ❌   │  ❌   │  ❌  │  ✅  │  ❌ ║
║  screenshotter.py        │  ❌   │   ❌   │   ❌   │   ❌   │  ❌   │  ❌  │  ✅  │  ❌ ║
║  pdf_reader.py           │  ❌   │   ❌   │   ✅   │   ❌   │  ❌   │  ❌  │  ❌  │  ❌ ║
║  archive_url.py          │  ❌   │   ❌   │   ✅   │   ❌   │  ❌   │  ✅  │  ❌  │  ❌ ║
║  search_logger.py        │  ✅   │   ✅   │   ✅   │   ❌   │  ❌   │  ❌  │  ❌  │  ❌ ║
║                                                                                          ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
```

### 🎙️ Narrator tools (audio stage)

```
╔════════════════════════════════════════════════════════════════════════════════════════╗
║  TOOL                                  │ NARRATOR │ DIRECTOR │ EIC │ ORCHESTRATOR      ║
║  ──────────────────────────────────────┼──────────┼──────────┼─────┼───────────────────║
║  tools/audio/tts_engine.py             │    ✅    │    ❌    │ ❌  │  ✅ (both passes) ║
║  tools/audio/script_normalizer.py      │    ✅    │    ❌    │ ❌  │  ❌               ║
║  tools/audio/providers.py              │    ✅    │    ❌    │ ❌  │  ❌               ║
║  tools/validators/output_validator.py  │    ✅    │    ❌    │ ✅  │  ✅ (voice gate)  ║
║      (voice)                           │ pre-flight│         │     │                   ║
║  tools/validators/audio_validator.py   │    ✅    │    ❌    │ ✅  │  ✅ (post-flight) ║
║  narration_cues.md (READ)              │    ❌    │    ✅    │ ✅  │  ❌               ║
║  ffmpeg                                │    ✅    │    ❌    │ ✅  │  ❌               ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
```

**Why the Narrator is not invoked as an LLM.** Every other stage shells out to an
AI CLI with a prompt. The Narrator stage calls `tools/audio/tts_engine.py`
directly. Rendering audio is deterministic work — chunking, synthesis, silence
splicing, concatenation — and routing it through a language model would add cost,
latency and non-determinism for no gain. The `/narrator` **persona** exists for
the interactive path: it explains costs, picks providers, and interprets
validator output. The **pipeline** path skips straight to the engine.

---

## 📁 FILE CREATION & READING FLOW

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                              FILE FLOW: WHO CREATES, WHO READS                            ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║  📡 TOPIC SCOUT ─────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      ├──► CREATES: Project folder (gemini_2026-01-04_Topic_001/)                         ║
║      ├──► UPDATES: config.yaml (ALL settings)                                            ║
║      └──► CREATES: topic_brief.md (200 words)                                            ║
║                    │                                                                      ║
║                    ▼ READS topic_brief.md                                                 ║
║  🎯 PROMPT AGENT ────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      └──► CREATES: prompt.md (Full investigation prompt with 21 questions)               ║
║                    │                                                                      ║
║                    ▼ READS prompt.md                                                      ║
║  🕵️ INVESTIGATOR ────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      └──► CREATES: truth_dossier.md (Research findings, answers to 21 questions)         ║
║                    │                                                                      ║
║                    ▼ READS truth_dossier.md                                               ║
║  ✍️ SCRIPTWRITER ─────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      ├──► CREATES: voice_script.md (Script for TTS with voice cues)                      ║
║      └──► CREATES: narrative_script.md (Clean script for Director)                       ║
║                    │                                                                      ║
║                    ▼ READS voice_script.md                                                ║
║  🎙️ NARRATOR (draft pass - free provider) ───────────────────────────────────────────►   ║
║      │                                                                                    ║
║      ├──► CREATES: assets/audio/narration/narration_draft.mp3                            ║
║      ├──► CREATES: assets/audio/narration/narration_cues.md (section -> timecode)        ║
║      ├──► CREATES: assets/audio/narration/narration_manifest.json                        ║
║      └──► CREATES: voiceover_report.md                                                   ║
║                    │                                                                      ║
║                    ▼ READS narrative_script.md + narration_cues.md                        ║
║  🎬 DIRECTOR ──────────────────────────────────────────────────────────────────────────►  ║
║      │                                                                                    ║
║      ├──► CREATES: master_script.md (Scene-by-scene with visual directions)              ║
║      └──► CREATES: video_direction.md (Summary of visual needs)                          ║
║                    │                                                                      ║
║                    ▼ READS master_script.md                                               ║
║  🦅 SCAVENGER ───────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      └──► CREATES: asset_manifest.md (All URLs + timestamps verified)                    ║
║                    │                                                                      ║
║                    ▼ READS asset_manifest.md                                              ║
║  💾 ARCHIVIST ───────────────────────────────────────────────────────────────────────►   ║
║      │                                                                                    ║
║      ├──► DOWNLOADS: assets/ folder (images, videos, screenshots)                        ║
║      └──► CREATES: MANUAL_REQUIRED.txt (If some downloads failed)                        ║
║                    │                                                                      ║
║                    ▼ READS ALL previous files                                             ║
║  🧐 EIC (Editor-in-Chief) ────────────────────────────────────────────────────────────►  ║
║      │                                                                                    ║
║      └──► CREATES: review_report.md (Quality review, approval/rejection)                 ║
║                    │                                                                      ║
║                    ▼ READS voice_script.md, truth_dossier.md                              ║
║  🎨 THUMBNAIL + 🔍 SEO ─────────────────────────────────────────────────────────────────► ║
║      │                                                                                    ║
║      └──► CREATES: youtube_optimization.md (Thumbnail prompts + SEO)                     ║
║                                                                                           ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 💬 WHAT EACH AGENT ASKS THE USER

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                              USER INTERACTION PER AGENT                                   ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║  📡 TOPIC SCOUT (MOST USER INTERACTION)                                                   ║
║  ├── [NP] What's the topic? ─────────────────────►  User enters topic                    ║
║  ├── [NP] Scope? (1=International, 2=National, 3=Regional) ───► User picks 1/2/3         ║
║  ├── [NP] Which country? ─────────────────────────►  User enters "India"                 ║
║  ├── [NP] Which region? ──────────────────────────►  User enters "Telangana"             ║
║  ├── [NP] Audio language? ────────────────────────►  User picks Telugu                   ║
║  ├── [NP] Video format? ──────────────────────────►  User picks Investigative            ║
║  ├── [NP] Duration? ──────────────────────────────►  User enters 25 (minutes)            ║
║  ├── [NP] Industry tag? ──────────────────────────►  User picks Political                ║
║  ├── [ST] Pick topic (1-5)? ──────────────────────►  User picks 2                        ║
║  └── Proceed to Prompt Agent? ────────────────────►  User says Y                         ║
║                                                                                           ║
║  🎯 PROMPT AGENT (MINIMAL INTERACTION)                                                    ║
║  ├── Topic already from topic_brief.md? Use it? ──►  User says Y                         ║
║  └── Proceed to Investigator? ────────────────────►  User says Y                         ║
║                                                                                           ║
║  🕵️ INVESTIGATOR (ONE CONFIRMATION)                                                       ║
║  └── [SI] Start Investigation? ───────────────────►  User says Y                         ║
║                                                                                           ║
║  ✍️ SCRIPTWRITER (ONE CONFIRMATION)                                                       ║
║  └── [GS] Generate Script? ───────────────────────►  User says Y                         ║
║                                                                                           ║
║  🎬 DIRECTOR (ONE CONFIRMATION)                                                           ║
║  └── [GM] Generate Master Script? ────────────────►  User says Y                         ║
║                                                                                           ║
║  🦅 SCAVENGER (ONE CONFIRMATION)                                                          ║
║  └── [FA] Find Assets? ───────────────────────────►  User says Y                         ║
║                                                                                           ║
║  💾 ARCHIVIST (ONE CONFIRMATION)                                                          ║
║  └── [DA] Download Assets? ───────────────────────►  User says Y                         ║
║                                                                                           ║
║  🧐 EIC (Automatic, may ask for revisions)                                                ║
║  └── [SR] Start Review? ──────────────────────────►  User says Y                         ║
║                                                                                           ║
║  🎨 THUMBNAIL + 🔍 SEO (ONE CONFIRMATION)                                                  ║
║  └── [GO] Generate Optimization? ─────────────────►  User says Y                         ║
║                                                                                           ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 📋 COMPLETE EXAMPLE: Electoral Bonds Scam

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║              COMPLETE WALKTHROUGH: "Electoral Bonds Scam" (Political, India)              ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣

STEP 1: USER RUNS /topic_scout
═══════════════════════════════════════════════════════════════════════════════════════════

User: /topic_scout

📡 Scout: "Ready to configure. What do you want to do?"

User: [NP] New Project

📡 Scout: "What's the topic?"
User: "Electoral Bonds Scam"

📡 Scout: "What's the scope?"
   [1] International
   [2] National
   [3] Regional
User: 2

📡 Scout: "Which country?"
User: "India"

📡 Scout: "Audio language?"
   [1] English  [2] Telugu  [3] Hindi...
User: 2 (Telugu)

📡 Scout: "Video format?"
   [1] Investigative Case Study (30-45 min)
   [2] News Explainer (15-20 min)
   ...
User: 1

📡 Scout: "Target duration in minutes?"
User: 30

📡 Scout: "Industry tag?"
   [1] Finance  [2] Stock Market  [3] Political...
User: 3 (Political)

📡 Scout: "✅ PROJECT CREATED"
   📁 Folder: gemini_2026-01-04_Electoral_Bonds_Scam_001
   📊 Settings:
      • Scope: national | India
      • Language: Telugu
      • Format: Investigative Case Study
      • Duration: 30 min (4050 words)
      • Industry: Political
      
   config.yaml UPDATED ✅
   
📡 Scout: "Search for topic context or enter manually?"
User: [ST] Search

📡 Scout: *searches using google_web_search, youtube_search.py*
   
   TOP 5 ANGLES:
   #1 🔥 "Supreme Court reveals full donor list"
   #2 📈 "Congress demands JPC probe"
   #3 💡 "How companies bought politicians"
   ...

User: 1

📡 Scout: *researches deeply, finds YouTube videos*
   *uses caption_reader.py to get timestamps*
   *writes 200-word brief*
   *saves to topic_brief.md*

📡 Scout: "✅ Brief saved. Proceed to /prompt? [Y/N]"
User: Y

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 2: USER RUNS /prompt
═══════════════════════════════════════════════════════════════════════════════════════════

User: /prompt

🎯 Prompt Agent: "📁 Found topic_brief.md from Topic Scout!"
   Topic: Electoral Bonds Scam - Supreme Court revelation
   
🎯 Prompt Agent: "Use this topic? [Y/N]"
User: Y

🎯 Prompt Agent: *reads brief*
   *searches for more details using google_web_search*
   *generates 21 investigation questions*
   *saves to prompt.md*

🎯 Prompt Agent: "✅ Prompt created. Proceed to /investigator? [Y/N]"
User: Y

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 3: USER RUNS /investigator
═══════════════════════════════════════════════════════════════════════════════════════════

User: /investigator

🕵️ Investigator: "Active Project: gemini_2026-01-04_Electoral_Bonds_Scam_001"
   "📍 Scope: national | India"
   "🏷️ Industry: Political"
   
🕵️ Investigator: "[SI] Start Investigation? [Y/N]"
User: Y

🕵️ Investigator: *reads prompt.md*
   *uses google_web_search for each question*
   *uses youtube_search.py to find interviews*
   *uses caption_reader.py to extract quotes with timestamps*
   *uses web_reader.py to read news articles*
   *uses archive_url.py to preserve key sources*
   
   Industry: Political → Prioritizes:
      • myneta.info (donation data)
      • Election Commission website
      • Supreme Court judgments
      • Parliament proceedings

🕵️ Investigator: *writes truth_dossier.md with all findings*

🕵️ Investigator: "✅ Dossier created. Proceed to /scriptwriter? [Y/N]"
User: Y

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 4: USER RUNS /scriptwriter
═══════════════════════════════════════════════════════════════════════════════════════════

User: /scriptwriter

✍️ Scriptwriter: "Active Project: gemini_2026-01-04_Electoral_Bonds_Scam_001"
   Target: 30 min = 4050 words (Telugu audio)

✍️ Scriptwriter: "[GS] Generate Script?"
User: Y

✍️ Scriptwriter: *reads truth_dossier.md*
   *reads config for audio_language: Telugu*
   *writes voice_script.md (with voice cues like (pause 2s), (angry tone))*
   *writes narrative_script.md (clean version for Director)*
   
   Word count check: 4050 words ✅

✍️ Scriptwriter: "✅ Scripts created: voice_script.md, narrative_script.md"

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 5: USER RUNS /director
═══════════════════════════════════════════════════════════════════════════════════════════

User: /director

🎬 Director: "[GM] Generate Master Script?"
User: Y

🎬 Director: *reads narrative_script.md*
   *reads config for video_format: Investigative Case Study*
   *designs visual shots for each narration line*
   *uses youtube_search.py to find clips*
   *uses caption_reader.py to get exact timestamps*
   
   Scene count: 50 scenes (30 min video) ✅

🎬 Director: *writes master_script.md*
   *writes video_direction.md*
   
   Assets sourced:
   - 15 YouTube clips with timestamps
   - 10 news article screenshots [MANUAL]
   - 8 stock footage [STOCK-MANUAL]
   - 12 graphics/charts [MANUAL]

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 6: USER RUNS /scavenger
═══════════════════════════════════════════════════════════════════════════════════════════

User: /scavenger

🦅 Scavenger: "[FA] Find Assets?"
User: Y

🦅 Scavenger: *reads master_script.md*
   *uses link_checker.py to validate ALL URLs*
   *uses youtube_search.py to find better alternatives*
   *uses caption_reader.py to verify timestamps*
   *uses archive_url.py to preserve news links*
   
   URL Validation:
   - 15 YouTube URLs: ✅ All valid
   - 8 News URLs: ✅ 7 valid, 1 archived
   - 5 Image URLs: ✅ All valid

🦅 Scavenger: *writes asset_manifest.md*
   
   Ready to Download: 28 assets
   Manual Required: 10 assets

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 7: USER RUNS /archivist
═══════════════════════════════════════════════════════════════════════════════════════════

User: /archivist

💾 Archivist: "[DA] Download Assets?"
User: Y

💾 Archivist: *reads asset_manifest.md*
   *uses link_checker.py before each download*
   *uses clip_grabber.py for YouTube clips*
   *uses image_grabber.py for images*
   *uses article_screenshotter.py for news quotes*
   *uses caption_reader.py for transcript files*

   Downloads:
   ├── assets/
   │   ├── 001_supreme_court_judgment_clip.mp4 ✅
   │   ├── 002_rahul_gandhi_speech_0215-0342.mp4 ✅
   │   ├── 003_bjp_press_conference.mp4 ✅
   │   ├── 004_economist_article_quote.png ✅
   │   ...
   └── MANUAL_REQUIRED.txt (10 items)

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 8: USER RUNS /eic
═══════════════════════════════════════════════════════════════════════════════════════════

User: /eic

🧐 EIC: "[SR] Start Review?"
User: Y

🧐 EIC: *reads ALL files*
   *uses link_checker.py to verify URLs still work*
   
   CHECKLIST:
   ✅ Dossier has 21 questions answered
   ✅ Script is 4050 words (30 min target)
   ✅ All 21 questions referenced in script
   ✅ Scene count: 50 (within limit)
   ✅ 28/38 assets downloaded (10 manual)
   ✅ Human story present (victims identified)
   ✅ Hook in first 30 seconds
   
🧐 EIC: *writes review_report.md*
   Status: APPROVED ✅

═══════════════════════════════════════════════════════════════════════════════════════════
STEP 9: USER RUNS /thumbnail and /seo
═══════════════════════════════════════════════════════════════════════════════════════════

User: /thumbnail

🎨 Thumbnail: *reads voice_script.md, truth_dossier.md*
   *generates 3 AI image prompts*
   *saves to youtube_optimization.md*

User: /seo

🔍 SEO: *reads voice_script.md*
   *uses google_web_search for keyword research*
   *generates title, description, tags*
   *appends to youtube_optimization.md*

═══════════════════════════════════════════════════════════════════════════════════════════
FINAL PROJECT FOLDER STRUCTURE
═══════════════════════════════════════════════════════════════════════════════════════════

./Projects/gemini_2026-01-04_Electoral_Bonds_Scam_001/
├── topic_brief.md           (200 words - from Scout)
├── prompt.md                (21 questions - from Prompt Agent)
├── truth_dossier.md         (Research - from Investigator)
├── voice_script.md          (TTS ready - from Scriptwriter)
├── narrative_script.md      (Clean script - from Scriptwriter)
├── master_script.md         (Scene-by-scene - from Director)
├── video_direction.md       (Summary - from Director)
├── asset_manifest.md        (URLs + timestamps - from Scavenger)
├── review_report.md         (Quality check - from EIC)
├── youtube_optimization.md  (Thumbnail + SEO - from both)
├── MANUAL_REQUIRED.txt      (Failed downloads - from Archivist)
└── assets/
    ├── 001_supreme_court_judgment_clip.mp4
    ├── 002_rahul_gandhi_speech.mp4
    ├── 003_bjp_press_conference.mp4
    ├── ...
    └── (28 downloaded files)

╚══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🔗 AGENT CONNECTION DIAGRAM

```
                                    USER
                                      │
                                      │ /topic_scout
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           📡 TOPIC SCOUT            │
                    │  • Creates project folder           │
                    │  • WRITES config.yaml (ALL fields)  │
                    │  • Creates topic_brief.md           │
                    └─────────────────┬───────────────────┘
                                      │
                            config.yaml updated
                            topic_brief.md created
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           🎯 PROMPT AGENT           │
                    │  • READS config.yaml                │
                    │  • READS topic_brief.md             │
                    │  • Creates prompt.md                │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │          🕵️ INVESTIGATOR           │
                    │  • READS config.yaml (industry_tag) │
                    │  • READS prompt.md                  │
                    │  • Creates truth_dossier.md         │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │          ✍️ SCRIPTWRITER            │
                    │  • READS config.yaml (language)     │
                    │  • READS truth_dossier.md           │
                    │  • Creates voice_script.md          │
                    │  • Creates narrative_script.md      │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           🎬 DIRECTOR               │
                    │  • READS config.yaml (format)       │
                    │  • READS narrative_script.md        │
                    │  • Creates master_script.md         │
                    │  • Creates video_direction.md       │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           🦅 SCAVENGER              │
                    │  • READS config.yaml                │
                    │  • READS master_script.md           │
                    │  • Creates asset_manifest.md        │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           💾 ARCHIVIST              │
                    │  • READS config.yaml                │
                    │  • READS asset_manifest.md          │
                    │  • Downloads to assets/             │
                    │  • Creates MANUAL_REQUIRED.txt      │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │             🧐 EIC                  │
                    │  • READS config.yaml                │
                    │  • READS ALL previous files         │
                    │  • Creates review_report.md         │
                    └─────────────────┬───────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
          ┌──────────────────────┐    ┌──────────────────────┐
          │     🎨 THUMBNAIL     │    │       🔍 SEO         │
          │  • Creates prompts   │    │  • Title/Desc/Tags   │
          └──────────┬───────────┘    └──────────┬───────────┘
                     │                           │
                     └───────────┬───────────────┘
                                 ▼
                    ┌─────────────────────────────────────┐
                    │       youtube_optimization.md       │
                    └─────────────────────────────────────┘
                                 │
                                 ▼
                           VIDEO READY!
```

---

## 📌 KEY RULES SUMMARY

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                                    KEY RULES                                              ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║  1️⃣  ONLY Topic Scout creates projects and modifies config.yaml                           ║
║                                                                                           ║
║  2️⃣  ALL other agents READ config.yaml but NEVER modify it                                ║
║                                                                                           ║
║  3️⃣  ALL files are created in: {projects_folder}/{current_project}/                       ║
║                                                                                           ║
║  4️⃣  Region is USER SELECTED, not auto-derived from language                              ║
║                                                                                           ║
║  5️⃣  Each agent READS the previous agent's output file                                    ║
║                                                                                           ║
║  6️⃣  Industry Tag helps agents prioritize relevant sources                                ║
║                                                                                           ║
║  7️⃣  Word count = Duration × 135 (avg 135 words per minute)                               ║
║                                                                                           ║
║  8️⃣  Minimum video duration = 15 minutes (2025 words)                                     ║
║                                                                                           ║
║  9️⃣  Word count is an ESTIMATE. The Narrator's draft pass gives the REAL runtime;         ║
║      the Director times shots against narration_cues.md, not the word count.              ║
║                                                                                           ║
║  🔟  The Narrator is the ONLY agent that spends money. It must print a cost               ║
║      estimate and get an explicit yes before any paid synthesis.                          ║
║                                                                                           ║
║  1️⃣1️⃣  API keys live in .env ONLY. config.yaml is committed, published to npm and         ║
║      copied into every user project - a key there is a key leaked.                        ║
║                                                                                           ║
║  1️⃣2️⃣  Runtime overruns are SCRIPT problems. Cut words; never raise playback speed.       ║
║                                                                                           ║
║  1️⃣3️⃣  Editing voice_script.md makes the narration STALE. stale_detector.py enforces      ║
║      this, and auto_rework.py invalidates both narration checkpoints on any                ║
║      script-level rework.                                                                 ║
║                                                                                           ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🎙️ NARRATION STAGE DETAIL

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                        WHY THE NARRATOR RUNS TWICE                                        ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║   DRAFT PASS                                  FINAL PASS                                  ║
║   after scriptwriting                         after EIC approval                          ║
║   ──────────────────────                      ──────────────────────                      ║
║   provider : free (edge / piper / mock)       provider : production (elevenlabs/sarvam)   ║
║   cost     : $0                               cost     : ~$0.44-$2.70 per 30 min          ║
║   purpose  : real runtime for the Director    purpose  : the deliverable                  ║
║   failure  : WARN, pipeline continues         failure  : FAIL, pipeline stops             ║
║   gate     : none                             gate     : audio_validator.py               ║
║                                                                                           ║
║   Rendering the final pass BEFORE EIC approval would mean paying twice for every          ║
║   script that gets sent back. In the reference mock run, the EIC rejects once             ║
║   before approving - so this is the normal case, not the edge case.                       ║
║                                                                                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                        PAUSES ARE REAL SILENCE, NOT MARKUP                                ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║   ElevenLabs does not support SSML <break> at all, and every other provider               ║
║   interprets pause markup differently. So the engine renders speech chunks,               ║
║   generates silence with ffmpeg, and splices them:                                        ║
║                                                                                           ║
║     (pause 2s)  ──►  exactly 2.000 s of silence, on EVERY provider                        ║
║                                                                                           ║
║   Consequence: segment n starts exactly where segment n-1 ended, every cue-sheet          ║
║   timecode is absolute, and the Director's shot list needs no re-syncing.                 ║
║                                                                                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                        PROVIDER ROUTING                                                   ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║   audio_language is Indic   ──►  sarvam ► elevenlabs ► gemini ► edge ► piper ► mock       ║
║   anything else             ──►  elevenlabs ► gemini ► openai ► edge ► piper ► mock       ║
║                                                                                           ║
║   The chain is walked until a provider is READY (key present / binary installed).         ║
║   `mock` is always ready, so the pipeline never hard-blocks on a missing key.             ║
║                                                                                           ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
```
