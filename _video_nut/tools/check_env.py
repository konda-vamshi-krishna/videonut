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
        print(f"✅ {name} found at: {path}")
        return True
    else:
        print(f"❌ {name} NOT found in PATH.")
        return False

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"✅ Python module '{module_name}' is installed.")
        return True
    except ImportError:
        print(f"❌ Python module '{module_name}' is MISSING.")
        return False

def main():
    print("🔍 VideoNut Environment Check...")
    print("-" * 30)

    all_good = True

    # 1. Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required.")
        all_good = False
    else:
        print(f"✅ Python Version: {sys.version}")

    # 2. Check FFmpeg
    if not check_command("ffmpeg", "FFmpeg"):
        # Check local bin fallback
        local_bin = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg.exe")
        if os.path.exists(local_bin):
             print(f"✅ FFmpeg found in local bin: {local_bin}")
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
            print(f"✅ Tool found: {tool_name}")
        else:
            print(f"❌ Tool missing: {tool_name} at {tool_path}")
            all_good = False

    print("-" * 30)
    if all_good:
        print("🚀 System is READY for VideoNut Agents.")
        sys.exit(0)
    else:
        print("⚠️ System has ISSUES. Please fix missing dependencies.")
        sys.exit(1)

if __name__ == "__main__":
    main()