# The VideoNut Video Production Agency: User Guide

Welcome to your AI-powered production studio. This system transforms a simple idea into a fully researched, scripted, and asset-ready video project using five specialized AI agents.

This guide walks you through the entire lifecycle using a real-world example: **"The Irony of OpenAI using Google's Transformer."**

---

## 🎭 The Cast (Your AI Team)

1.  **🕵️ The Investigator:** Research & Facts. (Finds the story).
2.  **✍️ The Scriptwriter:** Narrative & Emotion. (Writes the words).
3.  **🎬 The Director:** Vision & Sourcing. (Visualizes the story).
4.  **🦅 The Scavenger:** Asset Hunting. (Finds the clips/images).
5.  **💾 The Archivist:** Asset Storage. (Downloads the files).
6.  **🧐 The Editor-in-Chief (EIC):** Quality Control. (Validates everything).

---

## 🚀 The Workflow: From Zero to Hero

### Step 1: The Brief (Investigator)
...

### Step 2: The Soul (Scriptwriter)
**Goal:** Turn the dry dossier into a human "Narrative Script."

1.  **Type:** `/scriptwriter`
2.  **Agent Action:** Sorkin reads the `truth_dossier.md`. He crafts the hook, ensures the 360-degree perspective, and writes the emotional narration.
3.  **Result:** A file is created at `_output/narrative_script.md`.

### Step 3: The Vision (Director)
**Goal:** Turn the narration into a cinematic "Master Script" with visual links.

1.  **Type:** `/director`
2.  **Agent Action:** Spielberg reads the `narrative_script.md`. He designs shots for every paragraph and finds the specific source URLs for the evidence.
3.  **Result:** A file is created at `_output/master_script.md`.

---

### Step 3: The Quality Check (Editor-in-Chief)
**Goal:** Ensure the script is accurate and entertaining before hunting for assets.

1.  **Type:** `/eic`
2.  **Agent Says:** "The desk is clear, Producer. Chief here."
3.  **You Select:** `[RV] Review Project Status` (Type `RV` or `2`).
4.  **Agent Action:** The Chief reads both the Dossier and the Script. He checks:
    *   **Fact Check:** Is the 2017 date correct?
    *   **Narrative Check:** Is the hook boring?
5.  **Result:** He gives you a Pass/Fail report.
    *   *If Fail:* You go back to `/director` and ask for edits.
    *   *If Pass:* You proceed to Step 4.
6.  **Next:** Dismiss the agent with `DA`.

---

### Step 4: The Hunt (Scavenger)
**Goal:** Find real URLs for every visual described in the script.

1.  **Type:** `/scavenger`
2.  **Agent Says:** "Eyes in the sky... Hunter online."
3.  **You Select:** `[FA] Find Assets` (Type `FA` or `2`).
4.  **Agent Action:** Hunter reads the `master_script.md`. For every "Visual" line, he searches YouTube, Google Images, or Twitter.
    *   *Script:* "Show the 'Attention Is All You Need' paper abstract."
    *   *Hunter:* Finds the arXiv PDF link or a screenshot URL.
5.  **Result:** A file is created at `_output/asset_manifest.md` containing a list of links.
6.  **Next:** Dismiss the agent with `DA`.

---

### Step 5: The Heist (Archivist)
**Goal:** Download all the files to your hard drive.

1.  **Type:** `/archivist`
2.  **Agent Says:** "Vault online."
3.  **You Select:** `[DL] Download Assets` (Type `DL` or `2`).
4.  **Agent Action:** Vault reads the `asset_manifest.md`. He uses tools (like `yt-dlp` or `wget`) to physically download the images and videos.
5.  **Result:** Your assets appear in `_output/raw_assets/` organized by scene.
6.  **Next:** Dismiss the agent with `DA`.

---

## 🎉 Conclusion

You now have:
1.  A researched Dossier.
2.  A cinematic Script.
3.  A folder full of Video/Image assets.

**You are ready to edit!** Open your video editor (Premiere, Davinci) and drag in the files.
