#!/usr/bin/env python3
"""
YouTube Caption/Transcript Reader for VideoNut
Extracts captions from YouTube videos with optional timestamp display.
"""

import sys
import argparse
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter, JSONFormatter
import re


def extract_video_id(url):
    """
    Extract YouTube video ID from various URL formats
    """
    # Patterns for different YouTube URL formats
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


def get_youtube_captions(url, languages=None, with_timestamps=False, search_term=None):
    """
    Get YouTube video captions/transcript
    
    Args:
        url: YouTube video URL
        languages: List of preferred language codes
        with_timestamps: If True, include timestamps with each line
        search_term: If provided, only return lines containing this term (with timestamps)
    
    Returns:
        Formatted transcript string
    """
    if languages is None:
        # Default to English and other common languages
        languages = ['en', 'en-US', 'en-GB', 'hi', 'te', 'ta', 'mr', 'es', 'fr', 'de']
    
    video_id = extract_video_id(url)
    
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {url}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Instantiate the API class
        api = YouTubeTranscriptApi()
        
        # Fetch the transcript data directly using the instance method
        transcript_data = api.fetch(video_id, languages=languages)
        
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
                return f"No matches found for '{search_term}' in transcript."
            
            output = [f"\n🔍 Found {len(matches)} matches for '{search_term}':\n"]
            for match in matches:
                output.append(f"[{match['timestamp']}] {match['text']}")
            output.append(f"\n📋 Suggested clip range: {matches[0]['timestamp']} - {matches[-1]['end_timestamp']}")
            return '\n'.join(output)
        
        # If with_timestamps, format each line with timestamp
        if with_timestamps:
            output = []
            output.append(f"\n📝 Transcript with Timestamps:\n")
            output.append("=" * 60)
            for entry in transcript_data:
                timestamp = format_timestamp(entry.start)
                output.append(f"[{timestamp}] {entry.text}")
            return '\n'.join(output)
        
        # Default: plain text format - join all text entries
        plain_text = ' '.join([entry.text for entry in transcript_data])
        
        return plain_text
        
    except Exception as e:
        print(f"Error retrieving captions: {str(e)}", file=sys.stderr)
        sys.exit(1)


def find_timestamp_for_quote(url, quote, context_seconds=30):
    """
    Find the timestamp where a specific quote appears in the video.
    Returns the start and end timestamps for a clip containing that quote.
    
    Args:
        url: YouTube video URL
        quote: The quote to search for
        context_seconds: How many seconds of context to include before/after
    
    Returns:
        Dict with start_time, end_time, and surrounding text
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None
    
    try:
        api = YouTubeTranscriptApi()
        # Use fetch to get the default transcript or specify languages
        transcript_data = api.fetch(video_id)
        
        quote_lower = quote.lower()
        
        for i, entry in enumerate(transcript_data):
            if quote_lower in entry.text.lower():
                # Found the quote
                start_time = max(0, entry.start - context_seconds)
                end_time = entry.start + getattr(entry, 'duration', 5) + context_seconds
                
                # Get surrounding context
                context_entries = []
                for j in range(max(0, i-3), min(len(transcript_data), i+4)):
                    context_entries.append({
                        'timestamp': format_timestamp(transcript_data[j].start),
                        'text': transcript_data[j].text
                    })
                
                return {
                    'found': True,
                    'quote': entry.text,
                    'timestamp': format_timestamp(entry.start),
                    'clip_start': format_timestamp(start_time),
                    'clip_end': format_timestamp(end_time),
                    'context': context_entries
                }
        
        return {'found': False, 'message': f"Quote not found: {quote}"}
        
    except Exception as e:
        return {'found': False, 'message': str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Extract captions from YouTube videos with optional timestamps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get plain transcript
  python caption_reader.py --url "https://youtube.com/watch?v=xxx"
  
  # Get transcript with timestamps
  python caption_reader.py --url "https://youtube.com/watch?v=xxx" --timestamps
  
  # Search for specific term and get timestamps
  python caption_reader.py --url "https://youtube.com/watch?v=xxx" --search "electoral bonds"
  
  # Find timestamp for a specific quote
  python caption_reader.py --url "https://youtube.com/watch?v=xxx" --find-quote "corruption" --json
        """
    )
    
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--languages", nargs="*", default=None, 
                       help="Preferred language codes (e.g., en hi te). Default: en and Indian languages")
    parser.add_argument("--timestamps", "-t", action="store_true",
                       help="Include timestamps with each line")
    parser.add_argument("--search", "-s", help="Search for specific term and show timestamps")
    parser.add_argument("--find-quote", "-f", help="Find exact timestamp for a quote")
    parser.add_argument("--context", "-c", type=int, default=30,
                       help="Seconds of context around found quote (default: 30)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.find_quote:
        # Find timestamp for specific quote
        result = find_timestamp_for_quote(args.url, args.find_quote, args.context)
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
        # Get transcript
        captions = get_youtube_captions(
            args.url, 
            args.languages, 
            with_timestamps=args.timestamps,
            search_term=args.search
        )
        print(captions)


if __name__ == "__main__":
    main()