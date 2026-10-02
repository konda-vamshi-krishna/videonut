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
    "voiceover",
    "direction",
    "scavenging",
    "visionary",
    "archiving"
]

# Every spelling of an agent the EIC might put in review_result.json, mapped to
# the pipeline stage that has to be re-run.
#
# This used to accept only the canonical lowercase names - but eic.md's own
# "Send Back to Agent" prompt offers the abbreviations SCOUT/PROMPT/INV/SCRIPT/
# DIR/SCAV/ARCH, none of which matched. A verdict naming "INV" resolved to no
# stage, auto_rework printed "Rework not required", and the orchestrator read
# that as approval. Aliases below close that gap; the fail-closed status line
# below stops any remaining mismatch from silently passing.
AGENT_TO_STAGE = {
    # canonical
    "investigator": "investigation",
    "scriptwriter": "scriptwriting",
    "narrator": "voiceover",
    "voiceover": "voiceover",
    "director": "direction",
    "scavenger": "scavenging",
    "visionary": "visionary",
    "archivist": "archiving",
    # abbreviations used in eic.md's menu prompt
    "inv": "investigation",
    "script": "scriptwriting",
    "narr": "voiceover",
    "vo": "voiceover",
    "dir": "direction",
    "scav": "scavenging",
    "vis": "visionary",
    "arch": "archiving",
    # display names
    "the investigator": "investigation",
    "the scriptwriter": "scriptwriting",
    "the narrator": "voiceover",
    "the director": "direction",
    "the scavenger": "scavenging",
    "the visionary": "visionary",
    "the archivist": "archiving",
}

# Agents the EIC scores but that the orchestrator does not own a stage for.
# Blame on these cannot be auto-reset; it must be surfaced to the human instead
# of silently evaporating.
MANUAL_ONLY_AGENTS = {
    "scout": "topic_scout", "topic_scout": "topic_scout", "topicscout": "topic_scout",
    "topic scout": "topic_scout", "the topic scout": "topic_scout",
    "prompt": "prompt", "prompt_agent": "prompt", "promptagent": "prompt",
    "prompt agent": "prompt", "the prompt agent": "prompt",
    "seo": "seo", "thumbnail": "thumbnail", "eic": "eic",
}

class UndeterminedVerdict(Exception):
    """
    The EIC's verdict could not be resolved into an action.

    This exists because the alternative - returning None, the same value used for
    "approved" - made every EIC failure mode read as a pass. The orchestrator now
    halts on this instead of shipping an unreviewed video.
    """


def parse_review_result(project_path):
    """
    Reads review_result.json and finds the first failed stage.
    """
    result_path = os.path.join(project_path, "review_result.json")
    if not os.path.exists(result_path):
        raise UndeterminedVerdict(
            "No review_result.json in the project folder. The EIC either never ran "
            "or failed before writing its verdict - this is NOT an approval."
        )
        
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise UndeterminedVerdict(f"review_result.json is unreadable: {e}")
        
    verdict = data.get("verdict", "").strip().upper()
    if verdict in ("APPROVED", "PASS", "PASSED", "OK"):
        return None, f"EIC verdict is '{verdict}'."
    if verdict not in ("REJECTED", "NEEDS WORK", "NEEDS_WORK", "FAILED", "FAIL"):
        # An unrecognised verdict is NOT an approval. Say so.
        raise UndeterminedVerdict(
            f"Unrecognised EIC verdict {verdict!r}. Expected APPROVED / NEEDS WORK / REJECTED."
        )

    failed_agents = data.get("failed_agents", []) or []
    names = [str(item.get("agent", "")).strip().lower()
             for item in failed_agents if isinstance(item, dict)]
    rerun_from = str(data.get("rerun_from", "") or "").strip().lower()
    if rerun_from:
        names.append(rerun_from)
    names = [n for n in names if n]

    if not names:
        raise UndeterminedVerdict(
            f"EIC verdict is '{verdict}' but neither failed_agents nor rerun_from "
            "names an agent, so there is nothing to reset."
        )

    # Find the earliest failed stage in pipeline order
    earliest_stage_idx = len(STAGE_ORDER)
    earliest_agent = None
    manual_only = []

    for agent_name in names:
        stage = AGENT_TO_STAGE.get(agent_name)
        if stage is None:
            if agent_name in MANUAL_ONLY_AGENTS:
                manual_only.append(MANUAL_ONLY_AGENTS[agent_name])
            continue
        idx = STAGE_ORDER.index(stage)
        if idx < earliest_stage_idx:
            earliest_stage_idx = idx
            earliest_agent = agent_name

    if earliest_agent:
        failed_stage = STAGE_ORDER[earliest_stage_idx]
        note = ""
        if manual_only:
            note = (f" NOTE: the EIC also blamed {', '.join(sorted(set(manual_only)))}, "
                    "which the orchestrator cannot re-run. Run those agents by hand.")
        return failed_stage, (f"Failed agent '{earliest_agent}' maps to stage "
                              f"'{failed_stage}'.{note}")

    if manual_only:
        raise UndeterminedVerdict(
            f"EIC blamed {', '.join(sorted(set(manual_only)))}, which has no automated "
            f"pipeline stage. Re-run /{sorted(set(manual_only))[0]} manually, then re-run the EIC."
        )

    raise UndeterminedVerdict(
        f"EIC verdict is '{verdict}' but none of {names} maps to a pipeline stage. "
        f"Known agents: {', '.join(sorted(set(AGENT_TO_STAGE)))}."
    )

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
        "voiceover": "voiceover_draft_complete",
        "direction": "direction_complete",
        "scavenging": "scavenging_complete",
        "visionary": "visionary_complete",
        "archiving": "archiving_complete"
    }

    print(f"[REWORK] Resetting checkpoints starting from stage: '{fail_stage}'")
    for idx in range(fail_idx, len(STAGE_ORDER)):
        stage_name = STAGE_ORDER[idx]
        key = stage_to_key.get(stage_name)
        if key in checkpoints:
            checkpoints[key] = False
            print(f"  - Set {key} = False")
            
    # A rework at or above the script level invalidates any narration already
    # rendered from that script - otherwise the pipeline ships audio of the old text.
    if fail_stage in ("investigation", "scriptwriting", "voiceover"):
        for key in ("voiceover_draft_complete", "voiceover_final_complete"):
            if key in checkpoints and checkpoints[key]:
                checkpoints[key] = False
                print(f"  - Set {key} = False (script changed, narration is stale)")

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
        print(f"[FAIL] Project path '{project_path}' does not exist.")
        sys.exit(1)
        
    # Every exit path prints exactly one REVIEW_STATUS: line. The orchestrator
    # keys off that line, never off the absence of RERUN_STAGE - the old
    # behaviour, where "no rerun stage" meant "approved", turned every EIC
    # failure mode into a silent pass.
    try:
        fail_stage, msg = parse_review_result(project_path)
    except UndeterminedVerdict as e:
        print(f"[FAIL] Cannot determine the EIC verdict: {e}")
        print("REVIEW_STATUS:UNDETERMINED")
        sys.exit(2)

    if not fail_stage:
        print(f"[OK] Rework not required: {msg}")
        print("REVIEW_STATUS:APPROVED")
        sys.exit(0)

    print(f"[ALERT] Rework required: {msg}")
    success, reset_msg = apply_rework_checkpoints(project_path, fail_stage)

    if success:
        print(f"[OK] Rework initialized successfully: {reset_msg}")
        print("REVIEW_STATUS:REWORK")
        # Print fail stage in a special tag for parent orchestrator parsing
        print(f"RERUN_STAGE:{fail_stage}")
        sys.exit(0)
    else:
        print(f"[FAIL] Rework initialization failed: {reset_msg}")
        print("REVIEW_STATUS:UNDETERMINED")
        sys.exit(2)

if __name__ == "__main__":
    main()
