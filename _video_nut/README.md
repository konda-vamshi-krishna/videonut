# 🎬 VideoNut

<div align="center">

![VideoNut Banner](https://img.shields.io/badge/🎬_VideoNut-AI_Documentary_Pipeline-red?style=for-the-badge&labelColor=black)

### 🚀 Create Professional YouTube Documentaries with AI Agents

[![NPM Version](https://img.shields.io/npm/v/videonut?style=flat-square&logo=npm&logoColor=white&label=npm&color=CB3837)](https://www.npmjs.com/package/videonut)
[![GitHub Stars](https://img.shields.io/github/stars/konda-vamshi-krishna/videonut?style=flat-square&logo=github&color=yellow)](https://github.com/konda-vamshi-krishna/videonut)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Node](https://img.shields.io/badge/Node.js-16+-339933?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org)

**11 Specialized AI Agents** | **Multi-CLI Support** | **Zero Manual Research** | **Production-Ready Assets**

[📦 Install](#-quick-install) • [🎯 Quick Start](#-quick-start) • [🤖 Agents](#-meet-the-agents) • [📖 Docs](#-documentation) • [🤝 Contribute](#-contributing)

</div>

---

## ⚡ One Command Setup

```bash
npx videonut init
```

> **That's it!** This automatically installs Python, FFmpeg, Gemini CLI, and all dependencies.

---

## 🎯 What is VideoNut?

VideoNut transforms your ideas into **production-ready YouTube documentaries** using 11 specialized AI agents:

```
📡 Topic Scout → 🎯 Prompt → 🕵️ Investigator → ✍️ Scriptwriter → 🎬 Director
        ↓
    🎨 Visionary → 🦅 Scavenger → 💾 Archivist → 🧐 EIC → 🎨 Thumbnail → 🔍 SEO
```

### What You Get:
| Output | Description |
|--------|-------------|
| 📋 **Research Dossier** | Fully sourced facts with YouTube video timestamps |
| ✍️ **Complete Script** | Word-count matched narration for your target duration |
| 🎬 **Visual Direction** | Shot-by-shot guide with asset links |
| 📦 **Downloaded Assets** | Video clips, screenshots, PDFs ready for editing |
| 🎨 **Thumbnail Prompts** | AI image generation prompts for click-worthy thumbnails |
| 🔍 **SEO Package** | Optimized titles, descriptions, tags for YouTube |

---

## 📦 Quick Install

### ⚠️ Prerequisites: Install Node.js First

VideoNut requires **Node.js 20+** to run. Choose one method to install:

<details>
<summary><b>📥 Option A: Download from Website (Easiest)</b></summary>

1. Go to **[nodejs.org](https://nodejs.org)**
2. Download the **LTS version** (recommended)
3. Run the installer and follow the prompts
4. Restart your computer
5. Verify installation: `node --version` and `npm --version`

</details>

<details>
<summary><b>💻 Option B: Install via Command Line</b></summary>

**Windows (PowerShell as Administrator):**
```powershell
winget install OpenJS.NodeJS.LTS
```

**macOS:**
```bash
brew install node
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

</details>

---

### Option 1: NPX (Recommended)
```bash
mkdir my-documentary
cd my-documentary
npx videonut init
```

### Option 2: Clone from GitHub
```bash
git clone https://github.com/konda-vamshi-krishna/videonut.git
cd videonut
npm run setup
```

Both methods automatically install:
- ✅ Python (if not installed)

- ✅ FFmpeg & FFprobe
- ✅ Gemini CLI (or your choice)
- ✅ All Python dependencies

---

## 🚀 Quick Start

After installation, open your AI CLI and run:

```bash
# Start with Gemini CLI
gemini

# Then run your first agent
/topic_scout
```

### Agent Pipeline

| # | Agent | Command | What It Does |
|---|-------|---------|--------------|
| 1 | 📡 **Topic Scout** | `/topic_scout` | Find trending topics, create project |
| 2 | 🎯 **Prompt** | `/prompt` | Generate research questions |
| 3 | 🕵️ **Investigator** | `/investigator` | Deep research with sources |
| 4 | ✍️ **Scriptwriter** | `/scriptwriter` | Write narration script |
| 5 | 🎬 **Director** | `/director` | Create visual directions |
| 6 | 🎨 **Visionary** | `/visionary` | Generate AI image and video prompts |
| 7 | 🦅 **Scavenger** | `/scavenger` | Find and verify assets |
| 8 | 💾 **Archivist** | `/archivist` | Download all assets |
| 9 | 🧐 **EIC** | `/eic` | Final quality review |
| 10 | 🎨 **Thumbnail** | `/thumbnail` | Generate thumbnail prompts |
| 11 | 🔍 **SEO** | `/seo` | YouTube optimization |

---

## 🤖 Meet the Agents

<details>
<summary><b>📡 Research Team</b></summary>

| Agent | Persona | What They Do |
|-------|---------|--------------|
| **Scout** | Trend Hunter | Finds viral topics, checks YouTube competition |
| **Prompt** | Research Architect | Creates focused research questions |
| **Sherlock** | Investigator | Deep research with YouTube video timestamps |

</details>

<details>
<summary><b>🎬 Creative Team</b></summary>

| Agent | Persona | What They Do |
|-------|---------|--------------|
| **Sorkin** | Scriptwriter | Word-count matched scripts with hooks |
| **Spielberg** | Director | Visual directions with source links |
| **Visionary** | Visual Prompt Engineer | Detailed prompts for AI image/video scenes |
| **Canvas** | Thumbnail Designer | Click-worthy thumbnail AI prompts |
| **Ranker** | SEO Expert | YouTube-optimized metadata |

</details>

<details>
<summary><b>🔧 Technical Team</b></summary>

| Agent | Persona | What They Do |
|-------|---------|--------------|
| **Hunter** | Scavenger | URL verification, timestamp extraction |
| **Vault** | Archivist | Downloads clips, screenshots, transcripts |
| **Chief** | Editor-in-Chief | 10-phase deep audit, catches every mistake |

</details>

---

## 📁 Output Structure

```
my-documentary/
├── 📋 topic_brief.md        # Topic and angle
├── 📝 truth_dossier.md      # Research with sources
├── ✍️ voice_script.md       # Narration script
├── 🎬 master_script.md      # Script + Visuals
├── 🎨 visual_prompts.md     # Prompts for AI visual generation
├── 📦 asset_manifest.md     # All asset URLs
├── 📂 assets/               # Downloaded files
│   ├── 001_clip.mp4
│   ├── 002_chart.png
│   └── ...
└── ✅ review_report.md      # Final review
```

---

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
target_duration: 30          # Minutes
video_format: "investigative" # investigative, explainer, documentary
audio_language: "English"
country: "India"
industry_tag: "political"    # political, finance, crime, tech
```

---

## 🌟 Why VideoNut?

| Feature | VideoNut | Manual Process |
|---------|----------|----------------|
| Research Time | ~30 mins | 8+ hours |
| Script Writing | Auto-generated | Manual |
| Asset Finding | Verified URLs | Hunt & Hope |
| Downloads | One-click | Individual |
| Quality Check | 10-phase audit | Self-review |

---

## 🤝 Contributing

We welcome contributions! Check out our [Contributing Guide](CONTRIBUTING.md).

### Areas We Need Help:
- 🌐 **Translations** - Agents in other languages
- 🎨 **UI Dashboard** - Web interface for non-CLI users  
- 🔌 **Integrations** - Video editing software plugins
- 📊 **Analytics** - Usage tracking and reporting

---

## 📖 Documentation

- [📘 User Guide](USER_GUIDE.md)
- [🔄 Agent Lifecycle](docs/LIFECYCLE.md)
- [🔍 Audit Report](docs/AUDIT_REPORT.md)

---

## 📝 License

MIT License - Free for personal and commercial use.

---

## 👨‍💻 Author

<div align="center">

**Vamshi Krishna Konda**

[![GitHub](https://img.shields.io/badge/GitHub-konda--vamshi--krishna-181717?style=flat-square&logo=github)](https://github.com/konda-vamshi-krishna)
[![Email](https://img.shields.io/badge/Email-vamshikrishna131437@gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:vamshikrishna131437@gmail.com)

</div>

---

<div align="center">

### ⭐ Star this repo if VideoNut helps you create better content!

**[📦 npm](https://www.npmjs.com/package/videonut)** • **[💻 GitHub](https://github.com/konda-vamshi-krishna/videonut)** • **[🐛 Issues](https://github.com/konda-vamshi-krishna/videonut/issues)**

</div>