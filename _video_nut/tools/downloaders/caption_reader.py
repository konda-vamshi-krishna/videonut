#!/usr/bin/env python3
"""
YouTube Caption/Transcript Reader for VideoNut

Extracts captions from YouTube videos with automatic retry and a local audio 
transcription fallback using faster-whisper/whisper if official captions are disabled 
or blocked. Logs fetches to the audit trail.

Usage:
    python caption_reader.py --url "https://youtube.com/watch?v=xxx"
    python caption_reader.py --url "https://youtube.com/watch?v=xxx" --timestamps
    python caption_reader.py --url "https://youtube.com/watch?v=xxx" --search "electoral bonds"
"""

import sys
import os
import argparse
import json
import re
import time
from random import uniform
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

# Try imports for fallback transcription
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    has_api = True
except ImportError:
    has_api = False


def log_action_to_audit(project_path, action, url="", local_path="", status="ok", details=""):
    """Wrapper for logging to audit trail if available."""
    if has_audit_logger:
        audit_logger.log_action(
            project_path=project_path,
            category="read",
            action=action,
            url=url,
            local_path=local_path,
            status=status,
            details=details
        )


def extract_video_id(url):
    """
    Extract YouTube video ID from various URL formats
    """
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11,12})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11,12})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11,12})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11,12})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None


def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def _fetch_with_retry(video_id, languages=None):
    """Fetch transcript data with automatic retry and backoff on connection/SSL errors."""
    if not has_api:
        raise ImportError("youtube_transcript_api is not installed.")
        
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            api = YouTubeTranscriptApi()
            if languages:
                return api.fetch(video_id, languages=languages)
            else:
                return api.fetch(video_id)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = uniform(1, 3)
                print(f"⚠️ YouTube transcript fetch attempt {attempt+1} failed: {str(e)}. Retrying in {delay:.2f} seconds...", file=sys.stderr)
                time.sleep(delay)
                
    raise last_error


# Fallback Local Transcription helper structures
class TranscriptEntry:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


def download_audio_stream(video_id, output_audio_path):
    """Downloads audio stream using yt_dlp."""
    import yt_dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_audio_path,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])


def transcribe_audio_locally(audio_path) -> list[TranscriptEntry]:
    """Transcribes local audio using faster-whisper or standard whisper."""
    # Try faster-whisper
    try:
        from faster_whisper import WhisperModel
        print("🎙️ Local transcript fallback: Transcribing with faster-whisper (tiny model)...")
        # tiny model on cpu is extremely fast and light
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        entries = []
        for segment in segments:
            entries.append(TranscriptEntry(
                text=segment.text,
                start=segment.start,
                duration=segment.end - segment.start
            ))
        return entries
    except Exception as e:
        print(f"⚠️ faster-whisper transcription failed/missing: {e}. Trying OpenAI whisper fallback...")
        
    # Try standard whisper
    try:
        import whisper
        print("🎙️ Local transcript fallback: Transcribing with standard whisper (tiny model)...")
        model = whisper.load_model("tiny")
        result = model.transcribe(audio_path)
        
        entries = []
        for segment in result.get('segments', []):
            entries.append(TranscriptEntry(
                text=segment['text'],
                start=segment['start'],
                duration=segment['end'] - segment['start']
            ))
        return entries
    except Exception as whisper_err:
        raise RuntimeError(f"Local transcription failed. faster-whisper not available, standard whisper failed: {whisper_err}")


def fetch_captions_via_transcription(video_id) -> list[TranscriptEntry]:
    """Downloads and transcribes audio locally if official transcripts fail."""
    import tempfile
    
    temp_dir = Path(tempfile.gettempdir())
    audio_path = str(temp_dir / f"yt_audio_temp_{video_id}.mp3")
    
    try:
        download_audio_stream(video_id, audio_path)
        
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise IOError("Downloaded audio file is empty or does not exist")
            
        transcript_data = transcribe_audio_locally(audio_path)
        return transcript_data
    finally:
        # Cleanup
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass


def get_youtube_captions(url, languages=None, with_timestamps=False, search_term=None, project_dir=None):
    """
    Get YouTube video captions/transcript
    """
    if not project_dir:
        project_dir = "."

    if languages is None:
        languages = ['en', 'en-US', 'en-GB', 'hi', 'te', 'ta', 'mr', 'es', 'fr', 'de']
    
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {url}", file=sys.stderr)
        log_action_to_audit(project_dir, "Caption fetch failed: invalid URL", url=url, status="failed")
        sys.exit(1)
    
    transcript_data = None
    fetched_via = ""
    error_details = ""
    
    # 1. Try to fetch from API
    try:
        transcript_data = _fetch_with_retry(video_id, languages=languages)
        fetched_via = "youtube-transcript-api"
        print("✅ Transcript retrieved successfully via YouTube API")
    except Exception as e:
        print(f"⚠️ API transcript fetch failed: {e}. Attempting local Whisper transcription fallback...", file=sys.stderr)
        error_details += f"API failed: {e}. "
        
    # 2. Try local transcription fallback
    if not transcript_data:
        try:
            transcript_data = fetch_captions_via_transcription(video_id)
            fetched_via = "local-whisper-fallback"
            print("✅ Local transcription fallback succeeded")
        except Exception as e:
            print(f"❌ Local transcription fallback failed: {e}", file=sys.stderr)
            error_details += f"Local Whisper failed: {e}."
            log_action_to_audit(
                project_dir,
                "Failed to retrieve captions",
                url=url,
                status="failed",
                details=error_details
            )
            sys.exit(1)
            
    # Format and search
    # If searching for a term, filter and return with timestamps
    if search_term:
        search_lower = search_term.lower()
        matches = []
        for entry in transcript_data:
            if search_lower in entry.text.lower():
                timestamp = format_timestamp(entry.start)
                duration = getattr(entry, 'duration', 0)
                end_timestamp = format_timestamp(entry.start + duration)
                matches.append({
                    'timestamp': timestamp,
                    'end_timestamp': end_timestamp,
                    'start_seconds': entry.start,
                    'text': entry.text
                })
        
        if not matches:
            log_action_to_audit(
                project_dir,
                f"Searched captions for '{search_term}' (0 matches)",
                url=url,
                status="skipped",
                details=f"Method: {fetched_via}"
            )
            return f"No matches found for '{search_term}' in transcript."
        
        output = [f"\n🔍 Found {len(matches)} matches for '{search_term}':\n"]
        for match in matches:
            output.append(f"[{match['timestamp']}] {match['text']}")
        output.append(f"\n📋 Suggested clip range: {matches[0]['timestamp']} - {matches[-1]['end_timestamp']}")
        
        log_action_to_audit(
            project_dir,
            f"Searched captions for '{search_term}' (Found {len(matches)} matches)",
            url=url,
            status="ok",
            details=f"Method: {fetched_via}"
        )
        return '\n'.join(output)
    
    # If with_timestamps, format each line with timestamp
    if with_timestamps:
        output = []
        output.append(f"\n📝 Transcript with Timestamps:\n")
        output.append("=" * 60)
        for entry in transcript_data:
            timestamp = format_timestamp(entry.start)
            output.append(f"[{timestamp}] {entry.text}")
            
        log_action_to_audit(
            project_dir,
            "Fetched timestamped captions",
            url=url,
            status="ok",
            details=f"Method: {fetched_via}"
        )
        return '\n'.join(output)
    
    # Default: plain text format - join all text entries
    plain_text = ' '.join([entry.text for entry in transcript_data])
    
    log_action_to_audit(
        project_dir,
        f"Fetched plain captions ({len(plain_text)} chars)",
        url=url,
        status="ok",
        details=f"Method: {fetched_via}"
    )
    return plain_text


def find_timestamp_for_quote(url, quote, context_seconds=30, project_dir=None):
    """
    Find the timestamp where a specific quote appears in the video.
    """
    if not project_dir:
        project_dir = "."
        
    video_id = extract_video_id(url)
    if not video_id:
        return {'found': False, 'message': f"Invalid video URL: {url}"}
        
    transcript_data = None
    fetched_via = ""
    
    # Attempt API fetch
    try:
        transcript_data = _fetch_with_retry(video_id)
        fetched_via = "youtube-transcript-api"
    except Exception:
        # Fallback to local transcription
        try:
            transcript_data = fetch_captions_via_transcription(video_id)
            fetched_via = "local-whisper-fallback"
        except Exception as e:
            return {'found': False, 'message': f"Failed to retrieve transcript: {e}"}
            
    quote_lower = quote.lower()
    
    for i, entry in enumerate(transcript_data):
        if quote_lower in entry.text.lower():
            # Found the quote
            start_time = max(0, entry.start - context_seconds)
            duration = getattr(entry, 'duration', 5)
            end_time = entry.start + duration + context_seconds
            
            # Get surrounding context
            context_entries = []
            for j in range(max(0, i-3), min(len(transcript_data), i+4)):
                context_entries.append({
                    'timestamp': format_timestamp(transcript_data[j].start),
                    'text': transcript_data[j].text
                })
            
            log_action_to_audit(
                project_dir,
                f"Found quote timestamp",
                url=url,
                status="ok",
                details=f"Quote: '{quote}'. Method: {fetched_via}"
            )
            
            return {
                'found': True,
                'quote': entry.text,
                'timestamp': format_timestamp(entry.start),
                'clip_start': format_timestamp(start_time),
                'clip_end': format_timestamp(end_time),
                'context': context_entries
            }
            
    log_action_to_audit(
        project_dir,
        f"Quote search returned 0 results",
        url=url,
        status="skipped",
        details=f"Quote: '{quote}'. Method: {fetched_via}"
    )
    return {'found': False, 'message': f"Quote not found: {quote}"}


def main():
    parser = argparse.ArgumentParser(
        description="Extract captions from YouTube videos with optional timestamps and Whisper fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get plain transcript
  python caption_reader.py --url "https://youtube.com/watch?v=xxx"
  
  # Get transcript with timestamps
  python caption_reader.py --url "https://youtube.com/watch?v=xxx" --timestamps
  
  # Search for specific term
  python caption_reader.py --url "https://youtube.com/watch?v=xxx" --search "electoral bonds"
        """
    )
    
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--languages", nargs="*", default=None, 
                       help="Preferred language codes (e.g., en hi te)")
    parser.add_argument("--timestamps", "-t", action="store_true",
                       help="Include timestamps with each line")
    parser.add_argument("--search", "-s", help="Search for specific term and show timestamps")
    parser.add_argument("--find-quote", "-f", help="Find exact timestamp for a quote")
    parser.add_argument("--context", "-c", type=int, default=30,
                       help="Seconds of context around found quote (default: 30)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--project-dir", help="Project directory path for logging")
    
    args = parser.parse_args()
    
    if args.find_quote:
        result = find_timestamp_for_quote(
            args.url, 
            args.find_quote, 
            args.context, 
            project_dir=args.project_dir
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result.get('found'):
                print(f"\n✅ Quote Found!")
                print(f"   Timestamp: {result['timestamp']}")
                print(f"   Text: {result['quote']}")
                print(f"\n🎬 Suggested Clip:")
                print(f"   Start: {result['clip_start']}")
                print(f"   End: {result['clip_end']}")
                print(f"\n📄 Context:")
                for entry in result['context']:
                    print(f"   [{entry['timestamp']}] {entry['text']}")
            else:
                print(f"❌ {result.get('message', 'Quote not found')}")
    else:
        captions = get_youtube_captions(
            args.url, 
            args.languages, 
            with_timestamps=args.timestamps,
            search_term=args.search,
            project_dir=args.project_dir
        )
        print(captions)


if __name__ == "__main__":
    main()