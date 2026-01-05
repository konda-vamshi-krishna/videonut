import os
import sys
import subprocess
import argparse

def download_clip(url, start_time, end_time, output_path, ffmpeg_path):
    """
    Downloads a specific clip from a YouTube video using yt-dlp.
    """
    # Ensure output directory exists if it's not the current directory
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    # Construct the yt-dlp command
    # --download-sections "*start-end" downloads only that range
    # --force-keyframes-at-cuts ensures precise cutting (requires ffmpeg)
    cmd = [
        "yt-dlp",
        "--verbose",
        "--download-sections", f"*{start_time}-{end_time}",
        "--force-keyframes-at-cuts",
        "--ffmpeg-location", ffmpeg_path,
        "-o", output_path,
        url
    ]

    print(f"Executing: ", ' '.join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Download successful.")
        print(result.stdout)

        # Validate that the file was created and has content
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                print(f"Error: Downloaded file is empty: {output_path}")
                sys.exit(1)
            else:
                print(f"File validation: {output_path} created with size {file_size} bytes")
        else:
            print(f"Error: Downloaded file does not exist: {output_path}")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("Error during download:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: yt-dlp not found. Please install it (pip install yt-dlp) and ensure it's in your PATH.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a video clip.")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--start", required=True, help="Start time (e.g., 00:00:10 or 10)")
    parser.add_argument("--end", required=True, help="End time (e.g., 00:00:20 or 20)")
    parser.add_argument("--output", required=True, help="Output file path")

    # Try to find ffmpeg in system PATH first
    import shutil
    import platform
    default_ffmpeg = shutil.which("ffmpeg")
    if not default_ffmpeg:
        # Fallback to local bin folder relative to this script
        # Assumes structure: tools/downloaders/clip_grabber.py -> tools/bin/ffmpeg.exe (Windows) or tools/bin/ffmpeg (Unix)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Determine the appropriate executable name based on the platform
        ffmpeg_exe = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
        default_ffmpeg = os.path.join(base_dir, "bin", ffmpeg_exe)

        # If the fallback path doesn't exist, warn the user
        if not os.path.exists(default_ffmpeg):
            print(f"Warning: ffmpeg not found in PATH or at expected location: {default_ffmpeg}")
            print("Please install ffmpeg or place it in the tools/bin/ directory.")

    parser.add_argument("--ffmpeg", default=default_ffmpeg, help="Path to ffmpeg executable")

    args = parser.parse_args()

    download_clip(args.url, args.start, args.end, args.output, args.ffmpeg)