# ✍️ Scriptwriter Agent: Sorkin

The Scriptwriter is a specialized creative agent designed to bridge the gap between raw investigative data and cinematic visual direction. It focuses exclusively on the **human element**, **narrative flow**, and **viewer retention**.

## 🎯 Purpose
The primary goal of the Scriptwriter is to humanize the findings of the Investigator. While the Investigator provides the "Truth," the Scriptwriter provides the "Soul." It ensures that all 360-degree perspectives (victims, authorities, systems) are represented with emotional depth and persuasive rhetoric.

## 🛠️ Setup & Dependencies
The Scriptwriter operates within the VideoNut ecosystem and requires the following:
- **Project Structure:** Must have access to the active project's `truth_dossier.md`.
- **Dependencies:** 
  - Python 3.8+
  - VideoNut Core Framework (for file I/O)
  - `config.yaml` with an active `current_project` path.

## 🚀 Usage

### CLI Integration
You can invoke the Scriptwriter directly from the Gemini CLI:
```bash
/scriptwriter
```

### Workflow Execution
1. **Load Agent:** Use `/scriptwriter`.
2. **Execute Command:** Select `[WS] Write Script`.
3. **Input:** Automatically reads the `truth_dossier.md` from the active project.
4. **Output:** Generates `narrative_script.md` in the project folder.

## 🧠 Core Logic: The 360-Degree Perspective
The agent uses a **Recursive Narrative Audit** to ensure:
- **The Hook:** A 45-second high-retention opening.
- **Stakeholder Inclusion:** Dedicated emotional beats for victims found by the "Bloodhound" protocol.
- **Rhetorical Sharpness:** Criticism of authority and systemic issues where supported by facts.

## 📝 Configuration (TOML)
The agent is registered in the CLI via the following TOML structure:
```toml
[scriptwriter]
name = "scriptwriter"
description = "Invoke the Scriptwriter agent (Sorkin)"
agent_path = "_video_nut/agents/creative/scriptwriter.md"
```