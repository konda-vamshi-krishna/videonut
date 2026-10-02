import shutil
import sys
import os
import subprocess

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def check_command(cmd, name):
    path = shutil.which(cmd)
    if path:
        print(f"[OK] {name} found at: {path}")
        return True
    else:
        print(f"[FAIL] {name} NOT found in PATH.")
        return False

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"[OK] Python module '{module_name}' is installed.")
        return True
    except ImportError:
        print(f"[FAIL] Python module '{module_name}' is MISSING.")
        return False

def main():
    print("[SCAN] VideoNut Environment Check...")
    print("-" * 30)

    all_good = True

    # 1. Check Python version
    if sys.version_info < (3, 8):
        print("[FAIL] Python 3.8+ is required.")
        all_good = False
    else:
        print(f"[OK] Python Version: {sys.version}")

    # 2. Check FFmpeg
    if not check_command("ffmpeg", "FFmpeg"):
        # Check local bin fallback
        local_bin = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg.exe")
        if os.path.exists(local_bin):
             print(f"[OK] FFmpeg found in local bin: {local_bin}")
        else:
             print("   (Please install FFmpeg or place it in tools/bin/)")
             all_good = False

    # 3. Check Python Packages
    if not check_import("yt_dlp"): all_good = False
    if not check_import("playwright"): all_good = False
    if not check_import("requests"): all_good = False
    if not check_import("bs4"): all_good = False
    if not check_import("youtube_transcript_api"): all_good = False
    if not check_import("pypdf"): all_good = False

    # 4. Check for new tools
    tools_dir = os.path.join(os.path.dirname(__file__), "downloaders")
    new_tools = [
        ("caption_reader.py", os.path.join(tools_dir, "caption_reader.py")),
    ]

    for tool_name, tool_path in new_tools:
        if os.path.exists(tool_path):
            print(f"[OK] Tool found: {tool_name}")
        else:
            print(f"[FAIL] Tool missing: {tool_name} at {tool_path}")
            all_good = False

    # 5. Narration (TTS) readiness - warnings only, never fatal.
    #    The pipeline always has a free fallback, so a missing key must not
    #    block the whole environment check.
    print("-" * 30)
    print("[SCAN] Narration (Narrator agent) readiness...")
    try:
        audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        sys.path.insert(0, audio_dir)
        from providers import available_providers  # noqa: E402

        status = available_providers("English")
        ready_paid = [n for n, (ok, _) in status.items()
                      if ok and n not in ("mock", "edge", "piper")]
        for name, (ok, reason) in status.items():
            mark = "[OK]" if ok else "[--]"
            print(f"  {mark} tts:{name:<11} {reason}")
        if ready_paid:
            print(f"  [OK] Production narration available via: {', '.join(ready_paid)}")
        else:
            print("  [WARN] No production TTS provider configured.")
            print("         Narration will fall back to free/placeholder audio.")
            print("         Copy .env.example to .env and add ELEVENLABS_API_KEY,")
            print("         SARVAM_API_KEY (Indic), GEMINI_API_KEY or OPENAI_API_KEY.")
    except Exception as e:
        print(f"  [WARN] Could not probe TTS providers: {e}")

    print("-" * 30)
    if all_good:
        print("[RUN] System is READY for VideoNut Agents.")
        sys.exit(0)
    else:
        print("⚠️ System has ISSUES. Please fix missing dependencies.")
        sys.exit(1)

if __name__ == "__main__":
    main()