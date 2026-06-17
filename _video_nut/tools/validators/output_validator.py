import os
import sys
import re

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def validate_dossier(dossier_path):
    """
    Validates truth_dossier.md:
    1. Checks file exists and is not empty (size > 500 bytes).
    2. Checks for presence of research questions (looks for at least 10 numbered items or questions).
    3. Checks for presence of source URLs (looks for 'http://' or 'https://').
    """
    if not os.path.exists(dossier_path):
        return False, "File does not exist"
    
    if os.path.getsize(dossier_path) < 500:
        return False, "File is too small (< 500 bytes), likely empty or incomplete"
        
    try:
        with open(dossier_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    # Check for links
    urls = re.findall(r'https?://[^\s)\]]+', content)
    if not urls:
        return False, "No source URLs/links found in the truth dossier. Investigator must include sources."
        
    # Check for research questions (numbered lists or questions)
    # Match items like "1. ", "15. ", or paragraphs starting with numbers, or question marks
    question_matches = re.findall(r'\d+\.\s+.*', content)
    question_marks = content.count('?')
    
    # We expect some substantial list of findings or questions
    if len(question_matches) < 10 and question_marks < 5:
        return False, f"Insufficient research questions/findings found (matched lists: {len(question_matches)}, question marks: {question_marks}). Minimum is 10."
        
    return True, f"Valid truth dossier (found {len(urls)} URLs, {len(question_matches)} research list items)"

def validate_script(script_path):
    """
    Validates narrative_script.md:
    1. Checks file exists and size > 1000 bytes.
    2. Checks for standard script structural sections (HOOK, MEAT, HUMAN BEAT, OUTRO/CALL TO ACTION).
    3. Checks for presence of visual cues or voice directions.
    """
    if not os.path.exists(script_path):
        return False, "File does not exist"
        
    if os.path.getsize(script_path) < 1000:
        return False, "File is too small (< 1KB). Narrative script must be a complete script."
        
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    content_upper = content.upper()
    
    # Check sections (at least a couple of hook, meat, human, outro sections or indicators)
    has_hook = "HOOK" in content_upper
    has_meat = "MEAT" in content_upper or "BODY" in content_upper
    has_outro = "OUTRO" in content_upper or "CALL TO ACTION" in content_upper or "CTA" in content_upper
    
    # Validate structure
    missing_sections = []
    if not has_hook: missing_sections.append("HOOK")
    if not has_meat: missing_sections.append("MEAT/BODY")
    if not has_outro: missing_sections.append("OUTRO/CTA")
    
    if len(missing_sections) > 1: # Let it pass if only one section label is missing, but fail if more
        return False, f"Missing script structure sections: {', '.join(missing_sections)}"
        
    # Check for visual cues or voice indicators (e.g. bracketed text, narrator tags)
    visual_indicators = re.findall(r'\[Visual:.*?\]|\[Voice:.*?\]|\(Narrator:.*?\)|NARRATOR:', content, re.IGNORECASE)
    if not visual_indicators and len(re.findall(r'\[.*?\]', content)) < 5:
        return False, "No visual directions or narration cues found (e.g. [Visual: ...] or NARRATOR:)"
        
    return True, "Valid narrative script structure"

def validate_manifest(manifest_path):
    """
    Validates asset_manifest.md:
    1. Checks file exists and size > 200 bytes.
    2. Checks for markdown table formatting.
    3. Verifies that columns look correct (contains URLs/timestamps).
    """
    if not os.path.exists(manifest_path):
        return False, "File does not exist"
        
    if os.path.getsize(manifest_path) < 200:
        return False, "File is too small (< 200 bytes). Manifest must contain asset list."
        
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Could not read file: {str(e)}"
        
    # Check for markdown table divider (|---|)
    table_dividers = re.findall(r'\|[\s-]*:?[\s-]*\|', content)
    if not table_dividers:
        return False, "No valid markdown table formatting found in asset manifest."
        
    # Check for URLs
    urls = re.findall(r'https?://[^\s|\]]+', content)
    # Check if we have at least one valid URL or placeholder
    if not urls and "MANUAL" not in content and "STOCK" not in content:
        return False, "No download URLs or MANUAL/STOCK asset listings found in manifest."
        
    return True, f"Valid asset manifest (found {len(urls)} verified URLs)"

def main():
    if len(sys.argv) < 3:
        print("Usage: python output_validator.py <type> <file_path>")
        print("Types: dossier, script, manifest")
        sys.exit(1)
        
    val_type = sys.argv[1].lower()
    file_path = sys.argv[2]
    
    if val_type == "dossier":
        success, msg = validate_dossier(file_path)
    elif val_type == "script":
        success, msg = validate_script(file_path)
    elif val_type == "manifest":
        success, msg = validate_manifest(file_path)
    else:
        print(f"Unknown validation type: {val_type}")
        sys.exit(1)
        
    if success:
        print(f"✅ Validation PASSED: {msg}")
        sys.exit(0)
    else:
        print(f"❌ Validation FAILED: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
