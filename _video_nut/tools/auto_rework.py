import os
import sys
import json

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Stage order mapping
STAGE_ORDER = [
    "investigation",
    "scriptwriting",
    "direction",
    "scavenging",
    "visionary",
    "archiving"
]

AGENT_TO_STAGE = {
    "investigator": "investigation",
    "scriptwriter": "scriptwriting",
    "director": "direction",
    "scavenger": "scavenging",
    "visionary": "visionary",
    "archivist": "archiving"
}

def parse_review_result(project_path):
    """
    Reads review_result.json and finds the first failed stage.
    """
    result_path = os.path.join(project_path, "review_result.json")
    if not os.path.exists(result_path):
        return None, "No review_result.json found in project folder."
        
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return None, f"Failed to parse review_result.json: {str(e)}"
        
    verdict = data.get("verdict", "").upper()
    if verdict not in ["REJECTED", "NEEDS WORK", "FAILED"]:
        return None, f"Project approved or has a non-failure verdict: '{verdict}'"
        
    failed_agents = data.get("failed_agents", [])
    if not failed_agents:
        # Check rerun_from as a fallback
        rerun_from = data.get("rerun_from", "")
        if rerun_from:
            stage = AGENT_TO_STAGE.get(rerun_from.lower(), rerun_from.lower())
            if stage in STAGE_ORDER:
                return stage, f"EIC requested rerun starting from agent '{rerun_from}'"
        return None, "Verdict indicates failure, but no failed_agents or rerun_from was specified."
        
    # Find the earliest failed stage in pipeline order
    earliest_stage_idx = len(STAGE_ORDER)
    earliest_agent = None
    
    for item in failed_agents:
        agent_name = item.get("agent", "").lower()
        stage = AGENT_TO_STAGE.get(agent_name, agent_name)
        if stage in STAGE_ORDER:
            idx = STAGE_ORDER.index(stage)
            if idx < earliest_stage_idx:
                earliest_stage_idx = idx
                earliest_agent = agent_name

    if earliest_agent:
        failed_stage = STAGE_ORDER[earliest_stage_idx]
        return failed_stage, f"Failed agent '{earliest_agent}' maps to stage '{failed_stage}'"
        
    return None, "Could not map failed agents to any pipeline stages."

def apply_rework_checkpoints(project_path, fail_stage):
    """
    Resets the workflow checkpoint file to mark the failed stage and all downstream stages as incomplete.
    """
    checkpoint_file = os.path.join(project_path, ".workflow_checkpoint.json")
    if not os.path.exists(checkpoint_file):
        return False, "Checkpoint file does not exist."
        
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoints = json.load(f)
    except Exception as e:
        return False, f"Could not read checkpoint file: {str(e)}"

    fail_idx = STAGE_ORDER.index(fail_stage)
    
    # Checkpoint keys matching stages
    stage_to_key = {
        "investigation": "investigation_complete",
        "scriptwriting": "scriptwriting_complete",
        "direction": "direction_complete",
        "scavenging": "scavenging_complete",
        "visionary": "visionary_complete",
        "archiving": "archiving_complete"
    }

    print(f"🔄 Resetting checkpoints starting from stage: '{fail_stage}'")
    for idx in range(fail_idx, len(STAGE_ORDER)):
        stage_name = STAGE_ORDER[idx]
        key = stage_to_key.get(stage_name)
        if key in checkpoints:
            checkpoints[key] = False
            print(f"  - Set {key} = False")
            
    # Update last_step to the step before the failure
    if fail_idx > 0:
        checkpoints["last_step"] = STAGE_ORDER[fail_idx - 1]
    else:
        checkpoints["last_step"] = "none"
        
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoints, f, indent=2)
        return True, "Checkpoints successfully reset for rework."
    except Exception as e:
        return False, f"Failed to save updated checkpoints: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_rework.py <project_path>")
        sys.exit(1)
        
    project_path = sys.argv[1]
    if not os.path.exists(project_path):
        print(f"❌ Project path '{project_path}' does not exist.")
        sys.exit(1)
        
    fail_stage, msg = parse_review_result(project_path)
    if not fail_stage:
        print(f"✅ Rework not required: {msg}")
        sys.exit(0)
        
    print(f"🚨 Rework required: {msg}")
    success, reset_msg = apply_rework_checkpoints(project_path, fail_stage)
    
    if success:
        print(f"✅ Rework initialized successfully: {reset_msg}")
        # Print fail stage in a special tag for parent orchestrator parsing
        print(f"RERUN_STAGE:{fail_stage}")
        sys.exit(0)
    else:
        print(f"❌ Rework initialization failed: {reset_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
