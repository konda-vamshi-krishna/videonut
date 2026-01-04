# 🎬 VideoNut

> **AI-Powered YouTube Documentary Production Pipeline**

Transform your ideas into professional YouTube documentaries using 10 specialized AI agents that handle research, scripting, visual direction, and asset management.

<p align="center">
  <img src="https://img.shields.io/badge/Agents-10-brightgreen" alt="10 Agents">
  <img src="https://img.shields.io/badge/CLI-Gemini%20%7C%20Qwen%20%7C%20Claude-blue" alt="Multi-CLI Support">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
  <img src="https://img.shields.io/npm/v/videonut" alt="NPM Version">
</p>

---

## 🚀 What is VideoNut?

VideoNut is a **complete video production pipeline** powered by AI agents. Each agent specializes in one part of the documentary creation process:

```
📡 Topic Scout → 🎯 Prompt → 🕵️ Investigator → ✍️ Scriptwriter → 🎬 Director → 🦅 Scavenger → 💾 Archivist → 🧐 EIC
```

**No more context switching.** Run one command, get a complete video plan with:
- ✅ Researched facts with sources
- ✅ Professional script (word-count matched to target duration)
- ✅ Visual directions with timestamps
- ✅ Downloaded assets ready for editing

---

## 📦 Installation

### Option 1: NPX (Recommended - No Install)
```bash
npx videonut init
```

### Option 2: NPM Global Install
```bash
npm install -g videonut
videonut init
```

### Option 3: Clone Repository
```bash
git clone https://github.com/vamshikrishna131437/videonut.git
cd videonut
npm install
```

---

## 🛠️ Requirements

- **Node.js** 16+ 
- **One of these AI CLI tools:**
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli) - `npm install -g gemini-cli`
  - [Qwen CLI](https://github.com/QwenLM/qwen-cli)
  - [Claude Code](https://claude.ai/code)

---

## 🎯 Quick Start

### 1. Start with Topic Scout
```bash
# In your terminal with Gemini CLI
/topic_scout
# or
/scout
```

### 2. Follow the Agent Pipeline
| Step | Agent | Command | What It Does |
|------|-------|---------|--------------|
| 1 | 📡 Topic Scout | `/topic_scout` | Find trending topics, create project |
| 2 | 🎯 Prompt | `/prompt` | Generate research prompts |
| 3 | 🕵️ Investigator | `/investigator` | Deep research with sources |
| 4 | ✍️ Scriptwriter | `/scriptwriter` | Write the narration script |
| 5 | 🎬 Director | `/director` | Create visual directions |
| 6 | 🦅 Scavenger | `/scavenger` | Find and verify asset URLs |
| 7 | 💾 Archivist | `/archivist` | Download all assets |
| 8 | 🧐 EIC | `/eic` | Final review and approval |
| 9 | 🎨 Thumbnail | `/thumbnail` | Generate thumbnail prompts |
| 10 | 🔍 SEO | `/seo` | Optimize for YouTube search |

---

## 🤖 Meet the Agents

### Research Team
| Agent | Persona | Specialty |
|-------|---------|-----------|
| 📡 **Scout** | Trend Hunter | Finds viral-worthy topics, checks YouTube competition |
| 🎯 **Prompt** | Research Architect | Transforms topics into focused research questions |
| 🕵️ **Sherlock** | Investigative Journalist | Deep research with YouTube video evidence |

### Creative Team
| Agent | Persona | Specialty |
|-------|---------|-----------|
| ✍️ **Sorkin** | Narrative Architect | Word-count matched scripts with emotional hooks |
| 🎬 **Spielberg** | Documentary Filmmaker | Visual directions with source links |
| 🎨 **Canvas** | Thumbnail Designer | Click-worthy thumbnail AI prompts |
| 🔍 **Ranker** | SEO Optimizer | YouTube-optimized titles and descriptions |

### Technical Team
| Agent | Persona | Specialty |
|-------|---------|-----------|
| 🦅 **Hunter** | Asset Finder | URL verification, timestamp extraction |
| 💾 **Vault** | Digital Librarian | Downloads clips, screenshots, transcripts |

### Quality Control
| Agent | Persona | Specialty |
|-------|---------|-----------|
| 🧐 **Chief** | Editor-in-Chief | 10-phase deep audit, catches every mistake |

---

## 📁 Project Structure

```
your-project/
├── topic_brief.md       # Topic Scout output
├── prompt.md            # Research prompts
├── truth_dossier.md     # Investigator findings
├── voice_script.md      # Narration script
├── narrative_script.md  # Full narrative
├── master_script.md     # Script + Visual directions
├── video_direction.md   # Visual-only guide
├── asset_manifest.md    # All assets with URLs
├── assets/              # Downloaded files
│   ├── 001_intro.mp4
│   ├── 002_chart.png
│   └── ...
├── correction_log.md    # EIC feedback (if any)
└── review_report.md     # Final review
```

---

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
# Video Production Settings
target_duration: 30          # Minutes
video_format: "investigative" # investigative, explainer, documentary

# Localization
audio_language: "English"
scope: "national"            # international, national, regional
country: "India"
region: "Telangana"

# Focus
industry_tag: "political"    # political, finance, crime, tech, etc.
```

---

## 🌟 Features

### ✅ Multi-CLI Support
Works with Gemini CLI, Qwen CLI, and Claude Code out of the box.

### ✅ YouTube Evidence
Automatically extracts timestamps from YouTube videos using caption analysis.

### ✅ Smart Asset Management
- Downloads only the relevant 30-second clips, not full videos
- Screenshots articles with highlighted quotes
- PDF page extraction with keyword search

### ✅ Quality Control
EIC agent performs 10-phase deep audit:
- URL verification
- Timestamp validation
- Cross-reference checks
- Word count compliance

### ✅ Correction Workflow
If mistakes are found, each agent has a `[CM] Correct Mistakes` option to fix issues and re-run.

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Areas We Need Help
- 🌐 Translations (agents in other languages)
- 🎨 UI/Dashboard for non-CLI users
- 🔌 Integration with video editing software
- 📊 Analytics and reporting

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Vamshi Krishna**
- Email: vamshikrishna131437@gmail.com
- GitHub: [@vamshikrishna131437](https://github.com/vamshikrishna131437)

---

## 🙏 Acknowledgments

Built for the AI agent community. Special thanks to:
- Google Gemini CLI team
- Qwen team
- Anthropic Claude team

---

<p align="center">
  <b>⭐ Star this repo if you find it useful!</b>
</p>