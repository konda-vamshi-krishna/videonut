# VideoNut Self-Improvement Analysis (DEEP DIVE)

**Date:** 2025-12-30  
**Test Topic:** Electoral Bonds Scheme  
**CLIs Tested:** Gemini CLI vs Qwen CLI

---

## 📊 Complete Output Comparison

### File Size Analysis

| File | Gemini | Qwen | Winner |
|------|--------|------|--------|
| truth_dossier.md | 5.5 KB (96 lines) | 9.5 KB (134 lines) | Qwen (more detailed) |
| voice_script.md | 6.8 KB (109 lines) | 12.3 KB (397 lines) | **Gemini** (concise, powerful) |
| narrative_script.md | 10 KB (252 lines) | 12.7 KB (414 lines) | **Gemini** (better structure) |
| video_direction.md | 5.3 KB (129 lines) | 36.9 KB (1015 lines) | **Qwen** (169 scenes) |
| master_script.md | 12.8 KB (138 lines) | 32.6 KB | Qwen (comprehensive) |
| asset_manifest.md | 4 KB (46 lines) | 19.9 KB (202 lines) | **Qwen** (better organized) |
| **TOTAL** | **44.4 KB** | **124 KB** | Qwen produced 2.8x more |

---

## 🏆 Agent-by-Agent Deep Analysis

---

### 🕵️ INVESTIGATOR (Sherlock)

#### Gemini Performance
- **21 Questions:** ❌ NOT explicitly listed in dossier
- **Dossier Structure:** Clear sections (Mechanism, Quid Pro Quo, Beneficiaries, Cover-Up)
- **"Raid-Donate-Settle" Pattern:** ✅ Coined this powerful term
- **Specific Examples:** 
  - Sarath Reddy (₹52 Cr → Approver)
  - Future Gaming (₹1,368 Cr → Lottery license)
  - Navayuga (₹55 Cr → Silkyara tunnel)
  - Qwik Supply Chain (Reliance disguise)
- **Quality Score:** 8/10

#### Qwen Performance
- **21 Questions:** ✅ EXPLICITLY listed all 21 questions in dossier
- **Dossier Structure:** Very organized with numbered questions
- **Data Quality:** 
  - "41 companies donated ₹2,471 crore while under investigation"
  - "₹1,698 crore donated AFTER raids" (powerful stat)
  - "30 shell companies purchased ₹143 crore"
- **Specific Examples:**
  - Kalpataru Group (₹5.5 Cr, 3 months after IT raid)
  - Future Gaming (₹60 Cr after ED raid)
  - Aurobindo Pharma (₹5 Cr after ED raid)
- **Confidence Score:** 8/10 (honestly stated)
- **Quality Score:** 9/10

#### 🏆 Investigator Winner: **QWEN**
**Why:** Followed protocol (21 explicit questions), better data aggregation, provided confidence score

---

### ✍️ SCRIPTWRITER (Sorkin)

#### Gemini Performance
- **Hook:** "November 10th, 2022. Prison door SLAMS." → BRILLIANT
- **Voice Cues:** ✅ Used (low pitch, slow, pause 2s, cynical tone, emphasis)
- **Length:** 109 lines (appropriate for 15-min video)
- **Emotional Moments:**
  - "This isn't a story about a donation. This is a story about a ransom."
  - "Those 41 men didn't know about the bond market... They just knew the roof was caving in."
  - "If you aren't paying the bill... then maybe, you aren't the customer."
- **Structure:** 5 clear acts (Price of Freedom, Mechanism, Algorithm, Silent Victim, Verdict)
- **Quality Score:** 10/10

#### Qwen Performance
- **Hook:** "2,471 crore rupees." → Good but less dramatic
- **Voice Cues:** ✅ Used (pause, emphasis, shocked tone, ironic tone, whisper)
- **Length:** 397 lines (TOO LONG for 30-min target - includes pause markers)
- **Emotional Moments:**
  - "The silent victim here is our democracy itself."
  - "Democracy becomes a commodity. Democracy becomes for sale."
  - "Is this legal bribery?" (whisper)
- **Structure:** Many sections but repetitive in places
- **Quality Score:** 7/10

#### 🏆 Scriptwriter Winner: **GEMINI**
**Why:** Better hook, appropriate length, more powerful emotional moments, tighter structure

---

### 🎬 DIRECTOR (Spielberg)

#### Gemini Performance
- **Scene Count:** 22 scenes (5 main scenes with sub-shots)
- **Timing:** ✅ Good timestamps [00:00 - 01:20]
- **Source Quality:**
  - Real URLs: 5 verified (The Hindu, Indian Express, etc.)
  - Manual tags: Appropriate for stock/animation
  - Fake URLs: 2 (YouTube video IDs invented)
- **Mood Tags:** ✅ Used ("Terrifying, final", "Dystopian, unfair")
- **Sample Direction:**
  ```
  Visual: Black screen -> Heavy metal prison door SLAMS shut. Echo.
  Source: [MANUAL] - Sound Effect
  Mood: Terrifying, final.
  ```
- **Quality Score:** 8/10

#### Qwen Performance
- **Scene Count:** 169+ scenes (extremely detailed)
- **Timing:** ✅ Every 5-10 seconds marked
- **Source Quality:**
  - Real URLs: 8 verified (myneta.info, livemint, etc.)
  - Manual tags: 160+ (overwhelming amount of custom graphics needed)
  - Fake URLs: None detected (good!)
- **Mood Tags:** ✅ Used consistently
- **Sample Direction:**
  ```
  ## Scene 106: [11:45 - 11:50]
  **Visual:** Pure quid pro quo transaction.
  **Source:** [MANUAL] - Created graphic
  **Mood:** Direct, showing clear exchange
  ```
- **Quality Score:** 9/10 (but may be impractical to produce)

#### 🏆 Director Winner: **QWEN** (for completeness) / **GEMINI** (for practicality)
**Why Qwen:** More thorough visual planning, no fake URLs
**Why Gemini:** More realistic scope, easier to actually produce

---

### 🦅 SCAVENGER (Hunter)

#### Gemini Performance
- **Valid URLs:** 6 verified
- **Fake URLs:** 2 (YouTube IDs hallucinated)
- **Stock Suggestions:** ✅ Pexels links provided
- **Field Notes:** ✅ Added contextual notes
- **Quality Score:** 7/10

#### Qwen Performance
- **Valid URLs:** 8 verified
- **Fake URLs:** 0 detected
- **Free Stock Alternatives:** ✅ Section with Vecteezy, Pixabay links
- **Organization:** Better table structure
- **Quality Score:** 9/10

#### 🏆 Scavenger Winner: **QWEN**
**Why:** No fake URLs, better organized, more free stock alternatives

---

### 💾 ARCHIVIST (Vault)

Both performed similarly in concept, but:
- **Downloads attempted:** Screenshots mostly succeeded
- **YouTube failures:** Due to fake URLs from Scavenger
- **Error handling:** Both continued after failures

#### 🏆 Archivist Winner: **TIE**

---

### 🧐 EIC (Chief)

#### Gemini Performance
- **Review Output:** Verbal report only
- **Blueprint Check:** Noted missing 21 questions
- **Bottleneck Identified:** Yes (missing video clips)
- **Verdict:** "APPROVED FOR PRODUCTION (with notes)"

#### Qwen Performance
- **Review Output:** Created `review_report.md` file
- **Blueprint Check:** ✅ Found all 21 questions
- **Detailed Checks:** 
  - Blueprint: ✅ PASSED
  - Fact Check: ✅ PASSED
  - Retention Audit: ✅ PASSED
  - Visual Check: ✅ 169 scenes
  - Logic Check: ✅ PASSED
- **Confidence Score:** 8/10
- **Verdict:** "APPROVED FOR PRODUCTION"

#### 🏆 EIC Winner: **QWEN**
**Why:** Created actual file artifact, more thorough checklist, found 21 questions

---

## 📈 Final Agent Ratings

| Agent | Gemini | Qwen | Better Tool |
|-------|--------|------|-------------|
| Investigator | 8/10 | 9/10 | Qwen |
| Scriptwriter | 10/10 | 7/10 | **Gemini** |
| Director | 8/10 | 9/10 | Qwen |
| Scavenger | 7/10 | 9/10 | Qwen |
| Archivist | 7/10 | 7/10 | Tie |
| EIC | 7/10 | 9/10 | Qwen |
| **OVERALL** | **7.8/10** | **8.3/10** | **Qwen** |

---

## ❌ Critical Red Flags

### 1. URL Hallucination (Gemini)
**Evidence:** `https://www.youtube.com/watch?v=f7h32MpiGOqG` (invalid ID)
**Fix:** Added URL validation to Scavenger ✅

### 2. Script Verbosity (Qwen)
**Evidence:** 397 lines with repetitive pauses
**Fix:** Add word count target instead of line count

### 3. Missing 21 Questions (Gemini)
**Evidence:** EIC couldn't find questions in dossier
**Fix:** Force Investigator to list questions explicitly

### 4. Impractical Scene Count (Qwen)
**Evidence:** 169 [MANUAL] scenes requiring custom graphics
**Fix:** Add practical limit (30-50 scenes max)

### 5. No Link Checker Tool Exists
**Evidence:** Scavenger references `link_checker.py` but tool doesn't exist
**Fix:** Create the tool

---

## 20 Improvement Questions & Answers

### Q1: Why did Gemini's hook work better?
**A:** Started with ACTION (prison door slam) not STATISTIC. Humans connect to stories, not numbers. Qwen's "₹2,471 crore" is powerful but abstract.

### Q2: Why did Qwen produce 3x more content?
**A:** Qwen follows instructions more literally. When asked for voice cues, it added them extensively. Gemini is more "editorially aware" and self-limits.

### Q3: Should we limit scene count?
**A:** Yes. 169 [MANUAL] scenes is impractical. Add guidance: "Design 25-50 key scenes, not every 5 seconds."

### Q4: Why didn't Gemini list 21 questions?
**A:** The prompt says "generate" questions, not "write them in the dossier." Need explicit instruction: "List all questions at top of dossier."

### Q5: Was the "Raid-Donate-Settle" framework original?
**A:** Gemini coined this term. It's a powerful narrative device. Qwen used "quid pro quo" more generically.

### Q6: Why did Qwen's EIC create a file but Gemini's didn't?
**A:** Qwen follows file-creation instructions more literally. Add explicit: "Save review to `review_report.md`"

### Q7: Which output would be easier to actually produce?
**A:** Gemini. 22 scenes is manageable. 169 scenes requires a large creative team.

### Q8: Did regional language search work?
**A:** Not visible in output. Need to add logging: "Searched in Telugu: హైదరాబాద్..."

### Q9: What's the ideal voice_script length?
**A:** ~100-150 lines for 15 min. ~200-250 lines for 30 min. Qwen's 397 is excessive.

### Q10: Should we add section markers to voice_script?
**A:** Yes. [HOOK], [BRIDGE], [MEAT], [HUMAN BEAT], [VERDICT] would help editing.

### Q11: Why did Qwen have better source URLs?
**A:** Qwen used myneta.info (official EC data) more than Gemini. Add this source to Investigator prompt.

### Q12: Is 8/10 confidence score honest?
**A:** Yes. Both correctly identified that correlation doesn't prove causation.

### Q13: What's the best Qwen output?
**A:** The asset_manifest.md - well-organized table with clear [MANUAL] vs verified URL sections.

### Q14: What's the best Gemini output?
**A:** The voice_script.md - emotionally powerful, appropriate length, excellent pacing.

### Q15: Should we use Gemini for creative, Qwen for research?
**A:** Interesting idea. Gemini for Scriptwriter, Qwen for Investigator/Director/Scavenger.

### Q16: Why did both miss the "22 years" claim verification?
**A:** Qwen correctly noted: "There's no evidence SBI asked for 22 years specifically." Good fact-checking.

### Q17: Should Prompt Agent generate different prompts for different CLIs?
**A:** Not necessary. Same prompt should work for both.

### Q18: What's the biggest strength of VideoNut system?
**A:** The pipeline structure (Investigator→Scriptwriter→Director→Scavenger→Archivist) creates comprehensive outputs.

### Q19: What's the biggest weakness?
**A:** URL validation. Both CLIs can hallucinate links, especially for YouTube videos.

### Q20: Priority improvement for tomorrow?
**A:** Create `link_checker.py` tool so Scavenger can verify URLs exist.

---

## 🚀 Action Items (Priority Order)

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| 🔴 P0 | Create `link_checker.py` tool | ✅ DONE | Already exists at `tools/validators/link_checker.py` |
| 🔴 P0 | Prompt Agent: Research-first approach | ✅ DONE (2025-12-30) | Now searches internet BEFORE generating questions |
| 🔴 P1 | Add word count target to Scriptwriter | ✅ DONE (2025-12-30) | Uses words not lines, min 2000 words (15 min) |
| 🔴 P1 | Add section markers to voice_script | ✅ DONE (2025-12-30) | [HOOK], [BRIDGE], [MEAT], [HUMAN BEAT], [VERDICT], [CTA] |
| 🔴 P1 | Force Investigator to list 21 questions explicitly | ✅ DONE (2025-12-30) | Added mandatory dossier template with numbered questions |
| 🟡 P2 | Add scene count limit (30-50) to Director | ✅ DONE (2025-12-30) | 15min=35 scenes, 30min=60 scenes, 60min=100 scenes max |
| 🟡 P2 | Add myneta.info to Investigator source list | ✅ DONE | Already in prompt_agent.md for official data |
| 🟢 P3 | Add search logging for regional languages | ✅ DONE (2025-12-30) | Created `search_logger.py` with Hindi/Telugu/Tamil support |
| 🟢 P3 | Force EIC to save review_report.md | ✅ DONE (2025-12-30) | EIC now saves agent-by-agent review report |

---

## 📝 Improvements Made (2025-12-30)

### 1. Prompt Agent (Catalyst) - Major Upgrade
- **Research-First Approach:** Now searches internet BEFORE generating questions
- Runs 5 search queries to understand the topic
- Identifies 360-degree view (victims, perpetrators, silent perspectives)
- Includes actual URLs found in research
- Questions are now SPECIFIC based on research findings

### 2. Scriptwriter (Sorkin) - Word Count System
- **Word Count, Not Line Count:** 130 words = 1 minute
- **Minimum Video Length:** 15 minutes = 2000 words
- Word budget allocation by section:
  - HOOK: 10%
  - BRIDGE: 5%
  - CONTEXT: 15%
  - MEAT: 40%
  - HUMAN BEAT: 15%
  - VERDICT: 10%
  - CTA: 5%
- Voice cues don't count toward word count
- Final word count displayed and validated

### 3. Video Format Durations
| Format | Duration | Word Target |
|--------|----------|-------------|
| News Explainer | 15-20 min | 2000-3000 |
| Video Essay | 20-30 min | 2600-4500 |
| Investigation | 30-45 min | 3900-6750 |
| Documentary | 45-60 min | 5850-9000 |
| Podcast | 60+ min | 7800+ |

### 4. Archivist (Vault) - Tool Integration Upgrade
- **Pre-download URL validation:** Now runs `link_checker.py` on EVERY URL before downloading
- **YouTube Transcript-First Workflow:**
  1. Get transcript with `caption_reader.py`
  2. Find exact timestamps from transcript
  3. Download only needed clip with `clip_grabber.py --start --end`
  4. If no timestamp specified → download 30s preview only
- **Improved error logging** with summary statistics

### 5. Scavenger (Hunter) - Timestamp Extraction
- **YouTube Timestamp Extraction:** Now extracts exact timestamps from transcripts
- **Manifest Format Updated:** Includes `Timestamp` column for video clips
- **Quote Verification:** Adds relevant quote from transcript as verification
- **Format example:**
  ```
  | Scene | Type | URL | Timestamp | Quote |
  | 5 | Video Clip | youtube.com/... | 05:23-06:10 | "Electoral bonds..." |
  ```

### 6. Tool Usage Summary (All Agents)
| Tool | Used By | Purpose |
|------|---------|---------|
| `youtube_search.py` | **NEW!** Investigator, Director | Search YouTube, filter by year |
| `caption_reader.py` | Investigator, Scriptwriter, Director, Scavenger, Archivist | Extract transcripts with --timestamps --search --find-quote |
| `link_checker.py` | Scavenger, Archivist | Validate URLs before use |
| `clip_grabber.py` | Archivist | Download YouTube clips with timestamps |
| `screenshotter.py` | Archivist | Capture web page screenshots |
| `image_grabber.py` | Archivist | Download web images |
| `web_reader.py` | Investigator | Extract web page text |
| `pdf_reader.py` | Investigator, Archivist | Extract PDF text |

### 7. EIC (Chief) - Review Report
- **Now saves review_report.md** - Creates file artifact
- **New checks added:**
  - Word count validation (min 2000 words)
  - Scene count validation (based on duration)
  - Video evidence check (at least 1 YouTube clip)
  - Human story check (named person, not abstract)

---

## 🎯 Recommendation

**For Production Videos:**
1. Use **Qwen** for Investigator (better research)
2. Use **Gemini** for Scriptwriter (better storytelling)
3. Use **Qwen** for Director/Scavenger (more thorough, no fake URLs)
4. ~~Review all URLs manually before Archivist runs~~ → Now automated with link_checker.py!

**Optimal CLI:** If only one CLI, use **Qwen** (higher overall score 8.3/10 vs 7.8/10)

---

## 📝 Session 2 Improvements (2025-12-30 09:45)

### New Scripts Created
1. **`youtube_search.py`** - Search YouTube for videos
   - `--query` Search term
   - `--max` Number of results (default 10)
   - `--year` Filter by year (e.g., 2018)
   - `--json` Output as JSON

2. **`caption_reader.py` - UPGRADED**
   - `--timestamps` Show timestamps with each line
   - `--search "{keyword}"` Find lines containing keyword
   - `--find-quote "{quote}"` Get exact timestamp for quote with context

### Agent Updates Summary
| Agent | Update |
|-------|--------|
| **Investigator** | Added youtube_search.py commands, VIDEO EVIDENCE HUNT phase mandatory |
| **Director** | Added YouTube video clip workflow with --find-quote |
| **Scavenger** | Enhanced timestamp extraction with --search and --find-quote |
| **Archivist** | Already had link validation and transcript-first workflow |
| **EIC** | Now saves review_report.md with word/scene count validation |
| **Prompt Agent** | Already had research-first approach |

### Key Expectation for Next Run
- Investigator MUST find at least 1 YouTube video with transcript
- Director MUST include timestamp ranges for video clips
- Scavenger MUST use --find-quote to get exact clip times
- Archivist MUST validate ALL URLs before downloading
- EIC MUST create review_report.md file

---

## 📝 Session 3 Improvements (2025-12-30 16:00)

### NEW AGENTS Created

#### 1. Thumbnail Agent (`agents/creative/thumbnail.md`)
- **Purpose:** Create YouTube thumbnail concepts that demand clicks
- **Features:**
  - Generates 3 thumbnail variations
  - Uses YouTube psychology (faces, contrast, curiosity)
  - Recommends color palettes and text overlays
  - Finds reference images for key people
- **Output:** `thumbnail_concepts.md`

#### 2. SEO Agent (`agents/creative/seo.md`)
- **Purpose:** Optimize video for YouTube algorithm
- **Features:**
  - Keyword research with competitor analysis
  - 5 title options (under 60 chars)
  - Optimized description with chapters
  - 30+ tags ready to copy-paste
  - 5 hashtags
- **Output:** `youtube_seo.md`

### NEW TOOLS Created

#### 1. Archive URL Tool (`tools/validators/archive_url.py`)
```
python archive_url.py --url "https://timesofindia.com/article/..."
```
- Archives news URLs to Archive.is before they expire
- Checks if URL already archived
- Returns permanent archive URL
- Critical for preserving news articles

#### 2. Search Logger (`tools/logging/search_logger.py`)
```
python search_logger.py --log --query "electoral bonds" --language "hi" --agent "investigator"
```
- Logs all search queries by agents
- Tracks regional language usage (Hindi, Telugu, Tamil, Marathi)
- Provides statistics on search patterns
- Helps identify if regional sources are being used

### Self-Review System (ALL AGENTS)
Every agent now has:
1. **Self-Review Phase** after main work
2. **10 Questions** about gaps/missing info
3. **End Menu** with 3 options:
   - [1] Sub-investigate
   - [2] Manual input
   - [3] Proceed

### Complete Agent List (9 Total)
| Agent | File | Purpose |
|-------|------|---------|
| Prompt | `core/prompt_agent.md` | Research-first prompt generation |
| Investigator | `research/investigator.md` | Deep research with questions |
| Scriptwriter | `creative/scriptwriter.md` | Voice script with word count |
| Director | `creative/director.md` | Visual script with scene limits |
| Thumbnail | `creative/thumbnail.md` | **NEW** YouTube thumbnails |
| SEO | `creative/seo.md` | **NEW** Title/Description/Tags |
| Scavenger | `technical/scavenger.md` | Asset manifest with timestamps |
| Archivist | `technical/archivist.md` | Download with validation |
| EIC | `core/eic.md` | Review with agent-by-agent analysis |

### Complete Tool List
| Tool | Path | Purpose |
|------|------|---------|
| youtube_search.py | downloaders/ | Search YouTube videos |
| caption_reader.py | downloaders/ | Extract transcripts with timestamps |
| clip_grabber.py | downloaders/ | Download video clips |
| article_screenshotter.py | downloaders/ | Screenshot with quote highlight |
| screenshotter.py | downloaders/ | Basic webpage screenshot |
| image_grabber.py | downloaders/ | Download images |
| web_reader.py | downloaders/ | Extract webpage text |
| pdf_reader.py | downloaders/ | Extract PDF text |
| link_checker.py | validators/ | Validate URLs |
| archive_url.py | validators/ | **NEW** Archive news URLs |
| search_logger.py | logging/ | **NEW** Track regional searches |

### All Action Items: ✅ COMPLETE
