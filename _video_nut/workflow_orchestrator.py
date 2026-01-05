#!/usr/bin/env python3
"""
VideoNut Workflow Orchestrator
Automates the agent workflow while maintaining manual control options
"""
import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
import shutil

class VideoNutOrchestrator:
    def __init__(self, project_path):
        self.project_path = project_path
        self.checkpoint_file = os.path.join(project_path, ".workflow_checkpoint.json")
        self.checkpoints = self.load_checkpoints()
        
    def load_checkpoints(self):
        """Load workflow progress from checkpoint file"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            "investigation_complete": False,
            "scriptwriting_complete": False, 
            "direction_complete": False,
            "scavenging_complete": False,
            "archiving_complete": False,
            "last_step": "none"
        }
    
    def save_checkpoints(self):
        """Save workflow progress to checkpoint file"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f, indent=2)
    
    def run_command(self, cmd, description):
        """Execute a command with error handling"""
        print(f"\n🚀 {description}")
        print(f"Command: {cmd}")
        
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=self.project_path
            )
            
            if result.returncode == 0:
                print(f"✅ {description} completed successfully")
                return True
            else:
                print(f"❌ {description} failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error running {description}: {str(e)}")
            return False
    
    def check_prerequisites(self):
        """Check if required files exist for each step"""
        files_needed = {
            "investigation": [],
            "scriptwriting": [os.path.join(self.project_path, "truth_dossier.md")],
            "direction": [os.path.join(self.project_path, "narrative_script.md")],
            "scavenging": [os.path.join(self.project_path, "master_script.md")],
            "archiving": [os.path.join(self.project_path, "asset_manifest.md")]
        }
        
        for step, required_files in files_needed.items():
            for file_path in required_files:
                if not os.path.exists(file_path):
                    print(f"❌ Prerequisite missing for {step}: {file_path}")
                    return False
        return True
    
    def run_investigation(self):
        """Run investigation phase"""
        if self.checkpoints["investigation_complete"]:
            print("⏭️ Investigation already completed, skipping...")
            return True
            
        print("\n🔍 Starting Investigation Phase...")
        # This would typically require user input, so we'll note this step
        print("Please run: /investigator and complete the investigation")
        print("When complete, mark investigation as done by creating truth_dossier.md")
        
        # For automation, we'd need to implement the actual investigator call
        # For now, we'll just check if the output file exists
        dossier_path = os.path.join(self.project_path, "truth_dossier.md")
        if os.path.exists(dossier_path):
            self.checkpoints["investigation_complete"] = True
            self.checkpoints["last_step"] = "investigation"
            self.save_checkpoints()
            print("✅ Investigation step marked as complete")
            return True
        else:
            print("❌ Investigation output not found. Please complete investigation manually.")
            return False
    
    def run_scriptwriting(self):
        """Run scriptwriting phase"""
        if self.checkpoints["scriptwriting_complete"]:
            print("⏭️ Scriptwriting already completed, skipping...")
            return True
            
        print("\n✍️ Starting Scriptwriting Phase...")
        
        # Check if prerequisite exists
        dossier_path = os.path.join(self.project_path, "truth_dossier.md")
        if not os.path.exists(dossier_path):
            print("❌ Prerequisite file missing: truth_dossier.md")
            return False
        
        # Run the scriptwriter
        cmd = f'python -c "import sys; sys.path.append(\'..\'); from tools.downloaders.caption_reader import *; exec(open(\'agents/creative/scriptwriter.md\').read())" 2>/dev/null || echo "Scriptwriter needs manual execution"'
        # More realistic approach - just check if output exists
        script_path = os.path.join(self.project_path, "narrative_script.md")
        
        if os.path.exists(script_path):
            self.checkpoints["scriptwriting_complete"] = True
            self.checkpoints["last_step"] = "scriptwriting"
            self.save_checkpoints()
            print("✅ Scriptwriting step marked as complete")
            return True
        else:
            print("❌ Narrative script not found. Please run scriptwriter manually.")
            return False
    
    def run_direction(self):
        """Run direction phase"""
        if self.checkpoints["direction_complete"]:
            print("⏭️ Direction already completed, skipping...")
            return True
            
        print("\n🎬 Starting Direction Phase...")
        
        # Check if prerequisite exists
        script_path = os.path.join(self.project_path, "narrative_script.md")
        if not os.path.exists(script_path):
            print("❌ Prerequisite file missing: narrative_script.md")
            return False
        
        # Check for output
        master_script_path = os.path.join(self.project_path, "master_script.md")
        if os.path.exists(master_script_path):
            self.checkpoints["direction_complete"] = True
            self.checkpoints["last_step"] = "direction"
            self.save_checkpoints()
            print("✅ Direction step marked as complete")
            return True
        else:
            print("❌ Master script not found. Please run director manually.")
            return False
    
    def run_scavenging(self):
        """Run scavenging phase"""
        if self.checkpoints["scavenging_complete"]:
            print("⏭️ Scavenging already completed, skipping...")
            return True
            
        print("\n🦅 Starting Scavenging Phase...")
        
        # Check if prerequisite exists
        master_script_path = os.path.join(self.project_path, "master_script.md")
        if not os.path.exists(master_script_path):
            print("❌ Prerequisite file missing: master_script.md")
            return False
        
        # Check for output
        manifest_path = os.path.join(self.project_path, "asset_manifest.md")
        if os.path.exists(manifest_path):
            self.checkpoints["scavenging_complete"] = True
            self.checkpoints["last_step"] = "scavenging"
            self.save_checkpoints()
            print("✅ Scavenging step marked as complete")
            return True
        else:
            print("❌ Asset manifest not found. Please run scavenger manually.")
            return False
    
    def run_archiving(self):
        """Run archiving phase"""
        if self.checkpoints["archiving_complete"]:
            print("⏭️ Archiving already completed, skipping...")
            return True
            
        print("\n💾 Starting Archiving Phase...")
        
        # Check if prerequisite exists
        manifest_path = os.path.join(self.project_path, "asset_manifest.md")
        if not os.path.exists(manifest_path):
            print("❌ Prerequisite file missing: asset_manifest.md")
            return False
        
        # Run archivist
        cmd = f'python -c "import sys; sys.path.append(\'..\'); exec(open(\'agents/technical/archivist.md\').read())" 2>/dev/null || echo "Archivist needs manual execution"'
        
        # Check for output directory
        assets_path = os.path.join(self.project_path, "assets")
        if os.path.exists(assets_path):
            self.checkpoints["archiving_complete"] = True
            self.checkpoints["last_step"] = "archiving"
            self.save_checkpoints()
            print("✅ Archiving step marked as complete")
            return True
        else:
            print("❌ Assets directory not found. Please run archivist manually.")
            return False
    
    def run_full_workflow(self):
        """Run the complete VideoNut workflow"""
        print("🎬 Starting VideoNut Video Production Workflow")
        print(f"Project Path: {self.project_path}")
        print(f"Last completed step: {self.checkpoints['last_step']}")
        
        steps = [
            ("Investigation", self.run_investigation),
            ("Scriptwriting", self.run_scriptwriting), 
            ("Direction", self.run_direction),
            ("Scavenging", self.run_scavenging),
            ("Archiving", self.run_archiving)
        ]
        
        for step_name, step_func in steps:
            print(f"\n--- {step_name.upper()} PHASE ---")
            if not step_func():
                print(f"❌ {step_name} phase failed. Workflow stopped.")
                return False
        
        print("\n🎉 All workflow phases completed successfully!")
        print("Your video assets are ready for editing!")
        return True

def main():
    parser = argparse.ArgumentParser(description="VideoNut Workflow Orchestrator")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--status", action="store_true", help="Show current workflow status")
    parser.add_argument("--next", action="store_true", help="Show what to do next")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.project):
        print(f"❌ Project directory does not exist: {args.project}")
        sys.exit(1)
    
    orchestrator = VideoNutOrchestrator(args.project)
    
    # Status command - show current progress
    if args.status:
        print("📊 VideoNut Workflow Status")
        print("=" * 50)
        print(f"Project: {args.project}")
        print(f"Last step: {orchestrator.checkpoints['last_step']}")
        print()
        
        status_icons = {True: "✅", False: "⏳"}
        steps = [
            ("Investigation", "investigation_complete", "truth_dossier.md"),
            ("Scriptwriting", "scriptwriting_complete", "narrative_script.md"),
            ("Direction", "direction_complete", "master_script.md"),
            ("Scavenging", "scavenging_complete", "asset_manifest.md"),
            ("Archiving", "archiving_complete", "assets/"),
        ]
        
        for step_name, checkpoint_key, output_file in steps:
            is_complete = orchestrator.checkpoints[checkpoint_key]
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
            "none": ("Investigation", "/investigator", "Create truth_dossier.md with research findings"),
            "investigation": ("Scriptwriting", "/scriptwriter", "Create narrative_script.md from the dossier"),
            "scriptwriting": ("Direction", "/director", "Create master_script.md with visual directions"),
            "direction": ("Scavenging", "/scavenger", "Create asset_manifest.md with URLs"),
            "scavenging": ("Archiving", "/archivist", "Download all assets to assets/ folder"),
            "archiving": ("Complete", None, "🎉 All done! Your video assets are ready for editing."),
        }
        
        last_step = orchestrator.checkpoints['last_step']
        step_name, command, description = next_steps.get(last_step, next_steps["none"])
        
        print(f"📍 Current position: After '{last_step}'")
        print(f"👉 Next step: {step_name}")
        if command:
            print(f"🔧 Command: {command}")
        print(f"📝 What to do: {description}")
        print()
        
        # Check for missing files
        expected_files = {
            "none": [],
            "investigation": [("truth_dossier.md", "Run /investigator to create this file")],
            "scriptwriting": [("narrative_script.md", "Run /scriptwriter to create this file")],
            "direction": [("master_script.md", "Run /director to create this file")],
            "scavenging": [("asset_manifest.md", "Run /scavenger to create this file")],
        }
        
        for filename, hint in expected_files.get(last_step, []):
            filepath = os.path.join(args.project, filename)
            if not os.path.exists(filepath):
                print(f"⚠️  Missing: {filename}")
                print(f"   Fix: {hint}")
        
        sys.exit(0)
    
    if args.resume:
        print("🔄 Resuming workflow from last checkpoint...")
    
    success = orchestrator.run_full_workflow()
    
    if success:
        print(f"\n✅ Workflow completed! Checkpoint file: {orchestrator.checkpoint_file}")
    else:
        print(f"\n❌ Workflow failed. Checkpoint file: {orchestrator.checkpoint_file}")
        print("\n💡 TIP: Run with --next to see what to do next")
        print("💡 TIP: Run with --status to see full progress")
        sys.exit(1)

if __name__ == "__main__":
    main()