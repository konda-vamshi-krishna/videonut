#!/usr/bin/env python3
"""
YouTube Clip Grabber for VideoNut

Downloads specific clip segments from YouTube videos using the native yt-dlp Python API.
Guarantees frame-accurate cuts using keyframe cutting and ffmpeg. Logs downloaded clips 
to the audit log.

Usage:
    python clip_grabber.py --url "https://youtube.com/watch?v=xxx" --start 10 --end 30 --output "./Projects/test/assets/clips/scene1.mp4"
"""

import os
import sys
import argparse
import platform
import shutil
from pathlib import Path

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Set path for importing audit_logger
vn_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(vn_root))

try:
    from tools.logging import audit_logger
    has_audit_logger = True
except ImportError:
    has_audit_logger = False

# Try to import yt_dlp
try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
    has_ytdlp = True
except ImportError:
    has_ytdlp = False


def log_action_to_audit(project_path, action, url="", local_path="", status="ok", details=""):
    """Wrapper for logging to audit trail if available."""
    if has_audit_logger:
        audit_logger.log_action(
            project_path=project_path,
            category="download",
            action=action,
            url=url,
            local_path=local_path,
            status=status,
            details=details
        )


def parse_time_to_seconds(time_str) -> float:
    """
    Parses a time string formatted as HH:MM:SS, MM:SS, or seconds into float seconds.
    """
    if not time_str:
        return 0.0
    try:
        return float(time_str)
    except ValueError:
        pass
        
    parts = str(time_str).split(':')
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")
    raise ValueError(f"Invalid time format: {time_str}")


def find_ffmpeg_executable(ffmpeg_arg=None):
    """Resolve the path of ffmpeg."""
    if ffmpeg_arg and os.path.exists(ffmpeg_arg):
        return ffmpeg_arg
        
    # Check in PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
        
    # Check local tools/bin folder
    base_dir = Path(__file__).parent.parent.parent
    ffmpeg_exe = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
    local_ffmpeg = base_dir / "tools" / "bin" / ffmpeg_exe
    if local_ffmpeg.exists():
        return str(local_ffmpeg)
        
    # Check another common local layout: root bin folder
    local_bin_ffmpeg = base_dir / "bin" / ffmpeg_exe
    if local_bin_ffmpeg.exists():
        return str(local_bin_ffmpeg)
        
    return None


def download_clip(url, start_time_str, end_time_str, output_path, ffmpeg_path=None, project_dir=None):
    """
    Downloads a precise segment of a video using native yt_dlp API.
    """
    if not project_dir:
        project_dir = str(Path(output_path).parent.parent)

    if not has_ytdlp:
        print("Error: yt-dlp is not installed. Please install it (pip install yt-dlp).")
        log_action_to_audit(project_dir, "Download failed: yt-dlp missing", url=url, status="failed")
        sys.exit(1)

    # Resolve ffmpeg executable
    resolved_ffmpeg = find_ffmpeg_executable(ffmpeg_path)
    if not resolved_ffmpeg:
        print("⚠️ Warning: ffmpeg not found. Keyframe cuts and format merging might fail.")
    else:
        print(f"[WORKFLOW] Using ffmpeg: {resolved_ffmpeg}")

    # Parse timestamps
    try:
        start_secs = parse_time_to_seconds(start_time_str)
        end_secs = parse_time_to_seconds(end_time_str)
    except Exception as e:
        print(f"Error parsing timestamps: {e}")
        log_action_to_audit(project_dir, f"Download failed: invalid timestamps: {e}", url=url, status="failed")
        sys.exit(1)

    if start_secs >= end_secs:
        print(f"Error: Start time ({start_time_str}) must be less than end time ({end_time_str}).")
        log_action_to_audit(project_dir, "Download failed: start >= end time", url=url, status="failed")
        sys.exit(1)

    print(f"📥 Preparing to download clip: {start_time_str} ({start_secs}s) to {end_time_str} ({end_secs}s)")
    
    # Ensure output folder exists
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Use a temporary file path then rename on success (atomic download)
    temp_output = out_file.with_suffix(".tmp.mp4")

    # Native yt-dlp Options
    ydl_opts = {
        # Format: best video that is <= 1080p, merged with best audio, or fallback to best
        'format': 'bestvideo[height<=1080]+bestaudio/best',
        # Slicing ranges configuration
        'download_ranges': download_range_func(None, [(start_secs, end_secs)]),
        'force_keyframes_at_cuts': True,
        'outtmpl': str(temp_output),
        'quiet': False,
        'no_warnings': False,
    }

    if resolved_ffmpeg:
        ydl_opts['ffmpeg_location'] = resolved_ffmpeg
        
    try:
        # Run yt-dlp downloader in-process
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Validate that the file was created and is not empty
        if temp_output.exists():
            file_size = temp_output.stat().st_size
            if file_size == 0:
                raise IOError("Downloaded file is 0 bytes")
                
            # Rename temp file to target output path
            if out_file.exists():
                out_file.unlink() # remove old file if exists
            temp_output.replace(out_file)
            
            print(f"[OK] Download successful. File saved to {out_file} ({file_size:,} bytes)")
            log_action_to_audit(
                project_dir, 
                f"Downloaded video clip [{start_time_str} to {end_time_str}]", 
                url=url, 
                local_path=str(out_file), 
                status="ok"
            )
        else:
            raise IOError("Temp output file was not created by yt-dlp")
            
    except Exception as e:
        print(f"[FAIL] Error downloading clip: {e}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except Exception:
                pass
        log_action_to_audit(
            project_dir, 
            f"Failed to download video clip: {e}", 
            url=url, 
            status="failed", 
            details=str(e)
        )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download a video clip segment from YouTube using native yt-dlp API.")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--start", required=True, help="Start time (e.g. 10 or 00:00:10)")
    parser.add_argument("--end", required=True, help="End time (e.g. 30 or 00:00:30)")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg executable")
    parser.add_argument("--project-dir", help="Project directory path for logging")

    args = parser.parse_args()

    download_clip(
        url=args.url,
        start_time_str=args.start,
        end_time_str=args.end,
        output_path=args.output,
        ffmpeg_path=args.ffmpeg,
        project_dir=args.project_dir
    )


if __name__ == "__main__":
    main()