#!/usr/bin/env python3
"""
VideoNut Workflow Orchestrator
Automates the agent workflow while maintaining manual control options,
programmatic agent execution, parallel processing, validation gates, and auto-rework.
"""
import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
import shutil
import concurrent.futures

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

STAGE_ORDER = [
    "investigation",
    "scriptwriting",
    "voiceover",
    "direction",
    "scavenging",
    "visionary",
    "archiving"
]

class VideoNutOrchestrator:
    def __init__(self, project_path, cli_runner="auto", force=False, rework_limit=3,
                 skip_voice=False, voice_provider=None):
        self.project_path = os.path.abspath(project_path)
        self.project_name = os.path.basename(self.project_path)
        self.checkpoint_file = os.path.join(self.project_path, ".workflow_checkpoint.json")
        self.force = force
        self.rework_limit = rework_limit
        self.skip_voice = skip_voice
        self.voice_provider = voice_provider
        
        # Determine CLI runner
        self.cli_runner = self.detect_cli_runner(cli_runner)
        self.checkpoints = self.load_checkpoints()
        self.ensure_config_sync()
        
    def detect_cli_runner(self, requested):
        if requested in ["claude", "gemini", "opencode", "qwen", "mock"]:
            return requested
            
        # Auto-detect best CLI
        for cli in ["claude", "gemini", "opencode", "qwen"]:
            if shutil.which(cli):
                print(f"[SCAN] Auto-detected CLI runner: '{cli}'")
                return cli
                
        print("⚠️  No CLI runners (claude, gemini, opencode, qwen) found in PATH.")
        print("Fallback to 'mock' mode for local verification.")
        return "mock"
        
    def load_checkpoints(self):
        """Load workflow progress from checkpoint file"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Set defaults for new fields
                    if "rework_iterations" not in data:
                        data["rework_iterations"] = 0
                    return data
            except Exception:
                pass
        return {
            "investigation_complete": False,
            "scriptwriting_complete": False, 
            "voiceover_draft_complete": False,
            "voiceover_final_complete": False,
            "direction_complete": False,
            "visionary_complete": False,
            "scavenging_complete": False,
            "archiving_complete": False,
            "last_step": "none",
            "rework_iterations": 0
        }
    
    def save_checkpoints(self):
        """Save workflow progress to checkpoint file"""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoints, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save checkpoints: {str(e)}")
            
    def ensure_config_sync(self):
        """Ensure config.yaml has current_project set correctly"""
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if not os.path.exists(config_path):
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("current_project:"):
                    lines[i] = f'current_project: "{self.project_name}"\n'
                    updated = True
                    
            if updated:
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"[CONFIG]  Synced config.yaml with current_project = '{self.project_name}'")
        except Exception as e:
            print(f"⚠️  Failed to sync config.yaml: {str(e)}")

    def voice_draft_enabled(self):
        """Read voice.draft_pass from config.yaml (default: enabled)."""
        if self.skip_voice:
            return False
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if not os.path.exists(config_path):
            return True
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                in_voice_block = False
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("voice:"):
                        in_voice_block = True
                        continue
                    if in_voice_block:
                        if stripped and not line.startswith((" ", "\t")):
                            break
                        if stripped.startswith("enabled:") and "false" in stripped.lower():
                            return False
                        if stripped.startswith("draft_pass:"):
                            return "false" not in stripped.lower()
        except Exception:
            pass
        return True

    def run_agent_cli(self, agent_name):
        """
        Executes an agent command using the designated CLI runner.
        """
        if self.cli_runner == "mock":
            return self.run_mock_agent(agent_name)
            
        cmd_parts = []
        if self.cli_runner == "claude":
            cmd_parts = ["claude", "-p", f"Run {agent_name} for project {self.project_name}"]
        elif self.cli_runner == "gemini":
            cmd_parts = ["gemini", "-p", f"Run {agent_name} for project {self.project_name}"]
        elif self.cli_runner == "opencode":
            cmd_parts = ["opencode", "run", agent_name]
        elif self.cli_runner == "qwen":
            cmd_parts = ["qwen", agent_name]
            
        cmd_str = " ".join(cmd_parts)
        print(f"[AGENT] Programmatically invoking agent: '{agent_name}' using {self.cli_runner}...")
        print(f"   Command: {cmd_str}")
        
        try:
            # We run relative to the workspace root directory
            workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # NOTE: `shell=True` with a LIST is a cross-platform footgun - on POSIX
            # only cmd_parts[0] is executed and every other element is dropped, so the
            # agent silently runs with no prompt. Always pass the list with shell=False.
            result = subprocess.run(
                cmd_parts,
                shell=False,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                cwd=workspace_root
            )
            
            if result.returncode == 0:
                print(f"[OK] Agent '{agent_name}' completed execution successfully.")
                return True
            else:
                print(f"[FAIL] Agent '{agent_name}' execution failed.")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
        except Exception as e:
            print(f"[FAIL] Subprocess execution error for agent '{agent_name}': {str(e)}")
            return False

    def run_mock_agent(self, agent_name):
        """
        Simulates agent execution by creating valid mock outputs for testing.
        """
        print(f"[MOCK] [MOCK] Simulating execution for agent '{agent_name}'...")
        
        if agent_name == "investigator":
            file_path = os.path.join(self.project_path, "truth_dossier.md")
            content = """# [INVESTIGATOR] Investigator Report: Truth Dossier
1. What are the key elements?
2. Research question 2: How does this work?
3. Question 3: What are the main points?
4. Question 4: Who is affected?
5. Question 5: Why is this important?
6. Question 6: What does the data show?
7. Question 7: When did it happen?
8. Question 8: Where are the sources?
9. Question 9: How is it resolved?
10. Question 10: What are the implications?
11. Question 11: Who are the experts?
12. Question 12: Is there a counter-narrative?
13. Question 13: What is the timeline?
14. Question 14: How does it impact the future?
15. Question 15: Final summary?

Sources:
- https://example.com/source1
- https://youtube.com/watch?v=dQw4w9WgXcQ
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        elif agent_name == "scriptwriter":
            file_path = os.path.join(self.project_path, "narrative_script.md")
            content = """# [WRITE] Narrative Script
[HOOK]
This is the dramatic opening hook of the documentary video.
[Visual: Montage of historical footage]

[MEAT]
NARRATOR: Here is the core meat and body of the video where we discuss research findings.
We want to expand this script content so that it easily passes the size validation gate, which requires the file to be at least 1KB (1000 bytes).
To do that, we will add some placeholder text explaining the history of computing.
Computing history spans several centuries, starting from manual tools like the abacus, to mechanical engines designed by Charles Babbage and Ada Lovelace.
Ada Lovelace is widely recognized as the world's first computer programmer, having written the first algorithm intended to be executed by a machine.
In the 20th century, computing evolved rapidly with vacuum tubes, transistors, and integrated circuits.
Alan Turing introduced the concept of the Turing Machine, laying the theoretical foundation for modern computer science.
During World War II, machines like Colossus and ENIAC were built for military calculations.
The microcomputer revolution in the 1970s and 1980s brought computing into the home, paving the way for the internet age and mobile computing.
[Visual: Graphs and source documents showing Babbage's Analytical Engine and Ada Lovelace's notes]

[OUTRO]
NARRATOR: Thank you for watching. Don't forget to like and subscribe for more deep dives into history!
[Visual: Outro template with social media handles]
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # The Narrator stage reads voice_script.md, so the mock must produce one.
            voice_path = os.path.join(self.project_path, "voice_script.md")
            voice_content = """# Voice Script (mock)

[HOOK]
(modulation pitch: low speed: slow tone: grave) This is the dramatic opening hook of the documentary. (end modulation)
(pause 2s)
(emphasis) Eight pages. (end emphasis) That is all it took.

[BRIDGE]
To understand what happened next, you have to understand what everyone missed. (pause 1s)

[MEAT]
Here is the core of the story. Computing history spans several centuries, starting from manual tools like the abacus,
to the mechanical engines designed by Charles Babbage and Ada Lovelace.
Ada Lovelace is widely recognised as the world's first computer programmer.
In the twentieth century, computing evolved rapidly with vacuum tubes, transistors, and integrated circuits.
Alan Turing introduced the concept of the Turing Machine, laying the theoretical foundation for modern computer science.
During the Second World War, machines like Colossus and ENIAC were built for military calculations.
(pause 1.5s) (modulation pitch: high speed: fast tone: questioning) So why did nobody see it coming? (end modulation)
The microcomputer revolution of the 1970s and 1980s brought computing into the home.

[HUMAN BEAT]
One engineer described the moment the scale became undeniable. Not as a breakthrough. As a sinking feeling.

[VERDICT]
(modulation pitch: low speed: slow tone: grave) They did not lose because the research was weak.
They lost because they read their own paper too narrowly. (end modulation) (pause 2s)

[CTA]
If this changed how you think about the history of computing, subscribe.

**Total Words:** 210
"""
            with open(voice_path, 'w', encoding='utf-8') as f:
                f.write(voice_content)

        elif agent_name == "director":
            file_path = os.path.join(self.project_path, "master_script.md")
            content = """# [WORKFLOW] Director Master Script
- Scene 1: Introduction
  [Visual: Montage, Source: https://youtube.com/watch?v=dQw4w9WgXcQ]
  Narration: Welcome to the show.
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        elif agent_name == "visionary":
            file_path = os.path.join(self.project_path, "visual_prompts.md")
            content = """# [VISIONARY] Visual Image Prompts
- Image 1: Cinematic wide shot of retro computers, neon lights, 4k.
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        elif agent_name == "scavenger":
            file_path = os.path.join(self.project_path, "asset_manifest.md")
            content = """# [SCAVENGER] Asset Manifest
This is the list of all video and image assets that need to be downloaded for the video project.
We are specifying the URLs and time ranges for the clips to be trimmed by the Archivist.

| Asset ID | URL | Start | End | Type |
|---|---|---|---|---|
| Scene_1 | https://youtube.com/watch?v=dQw4w9WgXcQ | 00:05 | 00:15 | video |
| Scene_2 | https://youtube.com/watch?v=jNQXAC9IVRw | 01:20 | 01:35 | video |
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        elif agent_name == "archivist":
            assets_dir = os.path.join(self.project_path, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            # Create a dummy asset file to satisfy checks
            dummy_asset = os.path.join(assets_dir, "Scene_1.mp4")
            with open(dummy_asset, 'w', encoding='utf-8') as f:
                f.write("mock video data")
                
        elif agent_name == "eic":
            # On first iteration, EIC will mock fail to test rework loop
            # On subsequent, EIC will approve
            iterations = self.checkpoints.get("rework_iterations", 0)
            result_path = os.path.join(self.project_path, "review_result.json")
            report_path = os.path.join(self.project_path, "review_report.md")
            
            if iterations == 0:
                print("[MOCK] [MOCK] Simulating EIC failure on first pass to test rework loop...")
                result_data = {
                    "verdict": "REJECTED",
                    "total_score": 150,
                    "max_score": 370,
                    "percentage": 40,
                    "failed_agents": [
                        {
                            "agent": "investigator",
                            "score": 20,
                            "max_score": 50,
                            "critical_failures": ["Too short", "Needs more youtube links"],
                            "correction_instructions": "Add more questions and video links to the dossier.",
                            "downstream_impact": ["scriptwriter", "director"]
                        }
                    ],
                    "passed_agents": ["prompt_agent"],
                    "rerun_from": "investigator"
                }
                report_content = "# [FAIL] EIC REJECTION REPORT\nCritical issues found in investigator stage."
            else:
                print(f"[MOCK] [MOCK] Simulating EIC approval (Rework iteration: {iterations})...")
                result_data = {
                    "verdict": "APPROVED",
                    "total_score": 350,
                    "max_score": 370,
                    "percentage": 94,
                    "failed_agents": [],
                    "passed_agents": ["investigator", "scriptwriter", "director", "scavenger", "visionary", "archivist"],
                    "rerun_from": ""
                }
                report_content = "# [OK] EIC APPROVAL REPORT\nAll checks passed!"
                
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
        return True

    def run_validation_gate(self, val_type, file_path):
        """Runs the output_validator.py script as a gate check."""
        validator_script = os.path.join(os.path.dirname(__file__), "tools", "validators", "output_validator.py")
        if not os.path.exists(validator_script):
            print(f"⚠️  Validator script '{validator_script}' not found. Skipping gate.")
            return True
            
        print(f"[GATE]  Running validation gate for '{val_type}' on '{os.path.basename(file_path)}'...")
        try:
            result = subprocess.run(
                [sys.executable, validator_script, val_type, file_path],
                capture_output=True,
                encoding='utf-8'
            )
            if result.returncode == 0:
                print(f"  {result.stdout.strip()}")
                return True
            else:
                print(f"[FAIL] Gate FAILED: {result.stdout.strip()}")
                print(f"  Error Details: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"[FAIL] Error running validator gate: {str(e)}")
            return False

    def run_stale_detection(self):
        """Runs the stale_detector.py script to flag outdated files."""
        detector_script = os.path.join(os.path.dirname(__file__), "tools", "validators", "stale_detector.py")
        if not os.path.exists(detector_script):
            return
            
        print("[SCAN] Scanning for stale pipeline stages...")
        try:
            result = subprocess.run(
                [sys.executable, detector_script, self.project_path],
                capture_output=True,
                encoding='utf-8'
            )
            for line in result.stdout.splitlines():
                if line.startswith("STALE_JSON:"):
                    stale_data = json.loads(line.replace("STALE_JSON:", "").strip())
                    for stage, is_stale in stale_data.items():
                        if is_stale:
                            key = f"{stage}_complete" if stage != "scavenging" else "scavenging_complete"
                            if self.checkpoints.get(key, False):
                                print(f"  - Resetting stale stage '{stage}' to incomplete.")
                                self.checkpoints[key] = False
            self.save_checkpoints()
        except Exception as e:
            print(f"⚠️  Failed to run stale detector: {str(e)}")

    def run_investigation(self):
        if self.checkpoints["investigation_complete"] and not self.force:
            print("[SKIP] Investigation stage already completed, skipping...")
            return True
            
        print("\n[SCAN] --- Phase 1: Investigation ---")
        success = self.run_agent_cli("investigator")
        if not success:
            return False
            
        dossier_path = os.path.join(self.project_path, "truth_dossier.md")
        if not self.run_validation_gate("dossier", dossier_path):
            return False
            
        self.checkpoints["investigation_complete"] = True
        self.checkpoints["last_step"] = "investigation"
        self.save_checkpoints()
        return True
        
    def run_scriptwriting(self):
        if self.checkpoints["scriptwriting_complete"] and not self.force:
            print("[SKIP] Scriptwriting stage already completed, skipping...")
            return True
            
        print("\n[WRITE] --- Phase 2: Scriptwriting ---")
        success = self.run_agent_cli("scriptwriter")
        if not success:
            return False
            
        script_path = os.path.join(self.project_path, "narrative_script.md")
        if not self.run_validation_gate("script", script_path):
            return False

        # The voice script is what the Narrator/TTS stage actually bills for, so it
        # gets its own (stricter) gate: no URLs, no visual directions, real cues.
        voice_script_path = os.path.join(self.project_path, "voice_script.md")
        if os.path.exists(voice_script_path):
            if not self.run_validation_gate("voice", voice_script_path):
                return False
        else:
            print("  [WARN] voice_script.md not found - the Narrator stage will fall back to "
                  "narrative_script.md, which still contains visual directions.")

        self.checkpoints["scriptwriting_complete"] = True
        self.checkpoints["last_step"] = "scriptwriting"
        self.save_checkpoints()
        return True

    def run_voiceover(self, mode="final"):
        """
        Narration stage. Renders voice_script.md into an audio track via
        tools/audio/tts_engine.py.

        mode="draft" : free/local timing pass run BEFORE the Director, so shots are
                       cut against the real runtime instead of a word-count guess.
                       Never fatal - a missing draft must not stop the pipeline.
        mode="final" : production render, run AFTER the EIC approves the script so
                       a rewrite never means paying for the same audio twice.
        """
        checkpoint_key = f"voiceover_{'draft' if mode == 'draft' else 'final'}_complete"

        if self.skip_voice:
            print(f"[SKIP] Voiceover ({mode}) disabled with --skip-voice.")
            return True
        if self.checkpoints.get(checkpoint_key, False) and not self.force:
            print(f"[SKIP] Voiceover ({mode}) already completed, skipping...")
            return True

        engine = os.path.join(os.path.dirname(__file__), "tools", "audio", "tts_engine.py")
        if not os.path.exists(engine):
            print(f"[WARN] tts_engine.py not found at {engine}. Skipping the voiceover stage.")
            return True

        script_path = os.path.join(self.project_path, "voice_script.md")
        if not os.path.exists(script_path):
            script_path = os.path.join(self.project_path, "narrative_script.md")
        if not os.path.exists(script_path):
            print("[WARN] No script available for narration. Skipping the voiceover stage.")
            return mode == "draft"

        label = "Draft (timing pass)" if mode == "draft" else "Final (production render)"
        print(f"\n[VOICE] --- Voiceover: {label} ---")

        cmd = [sys.executable, engine, "--project", self.project_path, "--mode", mode, "--yes"]
        if self.voice_provider:
            cmd += ["--provider", self.voice_provider]
        elif mode == "draft" and self.cli_runner == "mock":
            cmd += ["--provider", "mock"]
        if self.force:
            cmd.append("--force")

        try:
            result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[FAIL] Could not launch the TTS engine: {e}")
            return mode == "draft"

        for line in (result.stdout or "").splitlines():
            print(f"  {line}")
        if result.returncode != 0:
            print(f"[{'WARN' if mode == 'draft' else 'FAIL'}] Voiceover ({mode}) did not complete cleanly.")
            if result.stderr:
                print(f"  STDERR: {result.stderr.strip()[:600]}")
            if mode == "draft":
                print("  Continuing without a draft timing track.")
                return True
            return False

        if mode == "final" and not self.run_narration_gate():
            return False

        self.checkpoints[checkpoint_key] = True
        if mode == "final":
            self.checkpoints["last_step"] = "voiceover"
        self.save_checkpoints()
        return True

    def run_narration_gate(self):
        """Quality gate for generated audio: exists, complete, on-target, not silent."""
        validator = os.path.join(
            os.path.dirname(__file__), "tools", "validators", "audio_validator.py"
        )
        if not os.path.exists(validator):
            print("  [WARN] audio_validator.py not found. Skipping the narration gate.")
            return True
        print("[GATE]  Running narration quality gate...")
        try:
            result = subprocess.run(
                [sys.executable, validator, self.project_path],
                capture_output=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            print(f"  [WARN] Narration gate could not run: {e}")
            return True
        for line in (result.stdout or "").splitlines():
            print(f"  {line}")
        return result.returncode == 0

    def run_direction(self):
        if self.checkpoints["direction_complete"] and not self.force:
            print("[SKIP] Direction stage already completed, skipping...")
            return True
            
        print("\n[WORKFLOW] --- Phase 3: Direction ---")
        success = self.run_agent_cli("director")
        if not success:
            return False
            
        self.checkpoints["direction_complete"] = True
        self.checkpoints["last_step"] = "direction"
        self.save_checkpoints()
        return True

    def run_visionary_stage(self):
        if self.checkpoints.get("visionary_complete", False) and not self.force:
            return True
        success = self.run_agent_cli("visionary")
        if success:
            self.checkpoints["visionary_complete"] = True
            self.save_checkpoints()
            return True
        return False

    def run_scavenging_stage(self):
        if self.checkpoints.get("scavenging_complete", False) and not self.force:
            return True
        success = self.run_agent_cli("scavenger")
        if not success:
            return False
            
        manifest_path = os.path.join(self.project_path, "asset_manifest.md")
        if not self.run_validation_gate("manifest", manifest_path):
            return False
            
        self.checkpoints["scavenging_complete"] = True
        self.save_checkpoints()
        return True

    def run_parallel_visionary_and_scavenger(self):
        run_vis = not self.checkpoints.get("visionary_complete", False) or self.force
        run_scav = not self.checkpoints.get("scavenging_complete", False) or self.force
        
        if not run_vis and not run_scav:
            print("[SKIP] Visionary and Scavenging stages already completed, skipping...")
            return True
            
        print("\n[PARALLEL] --- Phase 4 & 5: Parallel Visionary & Scavenging ---")
        
        def run_one_agent(name, func):
            print(f"[RUN] [Parallel Thread] Spawning {name}...")
            return func()
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            if run_vis:
                futures[executor.submit(run_one_agent, "Visionary", self.run_visionary_stage)] = "Visionary"
            if run_scav:
                futures[executor.submit(run_one_agent, "Scavenger", self.run_scavenging_stage)] = "Scavenger"
                
            success = True
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                res = future.result()
                if res:
                    print(f"[OK] Parallel Thread '{name}' completed successfully!")
                else:
                    print(f"[FAIL] Parallel Thread '{name}' FAILED!")
                    success = False
                    
        if success:
            self.checkpoints["last_step"] = "scavenging" # sets checkpoint pointer
            self.save_checkpoints()
            return True
        return False

    def run_archiving(self):
        if self.checkpoints["archiving_complete"] and not self.force:
            print("[SKIP] Archiving stage already completed, skipping...")
            return True
            
        print("\n[SAVE] --- Phase 6: Archiving ---")
        success = self.run_agent_cli("archivist")
        if not success:
            return False
            
        self.checkpoints["archiving_complete"] = True
        self.checkpoints["last_step"] = "archiving"
        self.save_checkpoints()
        return True

    def run_eic_review_and_rework(self):
        """Runs the EIC quality audit and loops if rework is required."""
        print("\n[EIC] --- Phase 7: Editor-in-Chief Review ---")
        success = self.run_agent_cli("eic")
        if not success:
            print("[FAIL] EIC agent execution failed.")
            return False
            
        # Call auto_rework.py to check for rejections
        rework_script = os.path.join(os.path.dirname(__file__), "tools", "auto_rework.py")
        if not os.path.exists(rework_script):
            print("⚠️  auto_rework.py script not found. Skipping auto-rework check.")
            return True
            
        print("[SCAN] Checking EIC audit verdict...")
        try:
            result = subprocess.run(
                [sys.executable, rework_script, self.project_path],
                capture_output=True,
                encoding='utf-8'
            )
            
            rerun_stage = None
            review_status = None
            for line in (result.stdout or "").splitlines():
                if line.startswith("RERUN_STAGE:"):
                    rerun_stage = line.replace("RERUN_STAGE:", "").strip()
                elif line.startswith("REVIEW_STATUS:"):
                    review_status = line.replace("REVIEW_STATUS:", "").strip().upper()

            # FAIL CLOSED. Approval must be stated, never inferred from silence.
            # Before v1.5.1 the only test was `if rerun_stage:` with an else-branch
            # that printed "EIC APPROVED" - so a missing review_result.json, malformed
            # JSON, an unrecognised verdict, or an agent name the rework engine did
            # not know all resulted in an unreviewed video being declared finished
            # (and, since v1.5, a paid narration render on top of it).
            if review_status is None or review_status == "UNDETERMINED":
                print("\n[FAIL] The EIC verdict could not be resolved. NOT treating this as approval.")
                for line in (result.stdout or "").splitlines():
                    if line.strip():
                        print(f"  {line}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr.strip()[:500]}")
                print("\n  Fix the verdict and re-run with --resume. Checkpoints are untouched.")
                print(f"  Verdict file: {os.path.join(self.project_path, 'review_result.json')}")
                return False

            if rerun_stage:
                # Reload checkpoints from disk to preserve the resets made by auto_rework.py
                self.checkpoints = self.load_checkpoints()
                
                iterations = self.checkpoints.get("rework_iterations", 0)
                if iterations >= self.rework_limit:
                    print(f"\n[ALERT] REWORK LIMIT REACHED ({self.rework_limit} loops).")
                    print("Stopping pipeline and hand control to the user.")
                    print(f"Please review {os.path.join(self.project_path, 'review_report.md')} and correction_log.md.")
                    return False
                    
                self.checkpoints["rework_iterations"] = iterations + 1
                self.save_checkpoints()
                
                print(f"\n[REWORK] EIC Rejected the audit. Triggering Rework Loop #{iterations + 1} starting from stage '{rerun_stage}'...")
                # Loop back: re-run the pipeline from the rerun_stage
                return "loop_back"
            elif review_status == "REWORK":
                # auto_rework said rework but could not emit a stage - do not proceed.
                print("\n[FAIL] EIC requested rework but no stage was resolved.")
                return False
            else:
                print("\n[SUCCESS] EIC APPROVED! No rework required.")
                self.checkpoints["rework_iterations"] = 0
                self.save_checkpoints()
                return True
        except Exception as e:
            print(f"[FAIL] Error during auto-rework checking: {str(e)}")
            return False

    def run_full_workflow(self):
        """Run the complete VideoNut workflow"""
        print("[WORKFLOW] Starting VideoNut Programmatic Video Production Workflow")
        print(f"Project Path: {self.project_path}")
        print(f"Selected Runner: '{self.cli_runner}'")
        
        # 1. Stale detection and reset
        self.run_stale_detection()
        print(f"Last completed step: {self.checkpoints['last_step']}")
        
        # Core pipeline sequence
        while True:
            # Reload checkpoints to get any resets from auto_rework
            self.checkpoints = self.load_checkpoints()
            
            # Stage 1: Investigation
            if not self.run_investigation():
                return False
                
            # Stage 2: Scriptwriting
            if not self.run_scriptwriting():
                return False

            # Stage 2.5: Draft voiceover (free timing pass, feeds the Director)
            if self.voice_draft_enabled():
                self.run_voiceover("draft")

            # Stage 3: Direction
            if not self.run_direction():
                return False
                
            # Stage 4 & 5: Parallel Visionary and Scavenging
            if not self.run_parallel_visionary_and_scavenger():
                return False
                
            # Stage 6: Archiving
            if not self.run_archiving():
                return False
                
            # Stage 7: EIC Audit and Rework Loop check
            verdict = self.run_eic_review_and_rework()
            if verdict == "loop_back":
                # Checkpoints were reset, we just restart the loop
                # Disable force mode so it only runs what is reset (not everything)
                self.force = False
                # A rejected script invalidates any narration rendered from it.
                self.checkpoints["voiceover_draft_complete"] = False
                self.checkpoints["voiceover_final_complete"] = False
                self.save_checkpoints()
                continue
            elif not verdict:
                return False
            else:
                # approved!
                break

        # Stage 8: Final narration - rendered only once the EIC has signed off on
        # the script, so a rewrite never means paying for the same audio twice.
        if not self.run_voiceover("final"):
            print("[FAIL] Final voiceover stage failed. Scripts and assets are intact; "
                  "fix the reported issue and re-run with --resume.")
            return False
                
        print("\n[SUCCESS] Complete video production pipeline finished successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description="VideoNut Workflow Orchestrator")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--cli", default="auto", choices=["claude", "gemini", "opencode", "qwen", "auto", "mock"], help="CLI runner to use")
    parser.add_argument("--force", action="store_true", help="Force running stages even if complete")
    parser.add_argument("--rework-limit", type=int, default=3, help="Max EIC rework iterations")
    parser.add_argument("--skip-voice", action="store_true",
                        help="Skip the narration (TTS) stages entirely")
    parser.add_argument("--voice-provider",
                        help="Force a TTS provider: elevenlabs|sarvam|gemini|openai|piper|edge|mock")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--status", action="store_true", help="Show current workflow status")
    parser.add_argument("--next", action="store_true", help="Show what to do next")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(f"[FAIL] Project directory does not exist: {args.project}")
        sys.exit(1)
        
    orchestrator = VideoNutOrchestrator(
        project_path=args.project,
        cli_runner=args.cli,
        force=args.force,
        rework_limit=args.rework_limit,
        skip_voice=args.skip_voice,
        voice_provider=args.voice_provider,
    )
    
    # Status command - show current progress
    if args.status:
        print("📊 VideoNut Workflow Status")
        print("=" * 50)
        print(f"Project: {args.project}")
        print(f"Last step: {orchestrator.checkpoints['last_step']}")
        print(f"Rework iterations: {orchestrator.checkpoints.get('rework_iterations', 0)}")
        print()
        
        status_icons = {True: "[OK]", False: "[WAIT]"}
        steps = [
            ("Investigation", "investigation_complete", "truth_dossier.md"),
            ("Scriptwriting", "scriptwriting_complete", "narrative_script.md"),
            ("Voiceover (draft timing)", "voiceover_draft_complete", "assets/audio/narration/narration_draft.mp3"),
            ("Direction", "direction_complete", "master_script.md"),
            ("Visioning (AI Prompts)", "visionary_complete", "visual_prompts.md"),
            ("Scavenging", "scavenging_complete", "asset_manifest.md"),
            ("Archiving", "archiving_complete", "assets/"),
            ("Voiceover (final)", "voiceover_final_complete", "assets/audio/narration/narration_full.mp3"),
        ]
        
        for step_name, checkpoint_key, output_file in steps:
            is_complete = orchestrator.checkpoints.get(checkpoint_key, False)
            icon = status_icons[is_complete]
            status = "Complete" if is_complete else "Pending"
            print(f"  {icon} {step_name}: {status} → {output_file}")
        
        print()
        sys.exit(0)
    
    # Next command - show what to do next
    if args.next:
        print("🎯 What to Do Next")
        print("=" * 50)
        
        next_steps = {
            "none": ("Investigation", "investigator", "Create truth_dossier.md with research findings"),
            "investigation": ("Scriptwriting", "scriptwriter", "Create narrative_script.md from the dossier"),
            "scriptwriting": ("Direction", "director", "Create master_script.md with visual directions "
                              "(a draft narration runs first for real timings)"),
            "voiceover": ("EIC Review", "eic", "Narration rendered - audit the full package"),
            "direction": ("Visioning (AI Prompts) & Scavenging", "visionary / scavenger", "Create visual_prompts.md & asset_manifest.md"),
            "scavenging": ("Archiving", "archivist", "Download all assets to assets/ folder"),
            "archiving": ("EIC Review", "eic", "Audit all assets and scripts"),
            "eic": ("Final Narration", "narrator", "Render the production voiceover from voice_script.md"),
        }
        
        last_step = orchestrator.checkpoints['last_step']
        step_name, command, description = next_steps.get(last_step, next_steps["none"])
        
        print(f"[MATCH] Current position: After '{last_step}'")
        print(f"👉 Next step: {step_name}")
        if command:
            print(f"🔧 Command: {orchestrator.cli_runner} {command}")
        print(f"📝 What to do: {description}")
        print()
        sys.exit(0)
        
    success = orchestrator.run_full_workflow()
    
    if success:
        print(f"\n[OK] Workflow completed! Checkpoint file: {orchestrator.checkpoint_file}")
    else:
        print(f"\n[FAIL] Workflow failed. Checkpoint file: {orchestrator.checkpoint_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()