#!/usr/bin/env python3
"""
YouTube Search Tool for VideoNut
Searches YouTube for videos matching a query and returns structured results.
Uses yt-dlp for reliable, actively maintained YouTube searching.
"""

import sys
import argparse
import json
import subprocess
import re
import os
from datetime import datetime

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def search_youtube(query, max_results=10, filter_year=None):
    """
    Search YouTube for videos matching the query using yt-dlp.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 10)
        filter_year: Optional year to filter results (e.g., 2018 for videos from 2018)
    
    Returns:
        List of video dictionaries with title, url, duration, views, upload_date, channel
    """
    try:
        # Use yt-dlp to search YouTube
        search_query = f"ytsearch{max_results * 3}:{query}"  # Get extra for filtering and view-sorting
        
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--ignore-errors",
            search_query
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        if result.returncode != 0 and not result.stdout:
            print(f"Error: yt-dlp search failed", file=sys.stderr)
            return []
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                video = json.loads(line)
                
                # Extract duration - yt-dlp provides it in seconds
                duration_secs = video.get('duration')
                if duration_secs:
                    mins, secs = divmod(int(duration_secs), 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0:
                        duration_str = f"{hours}:{mins:02d}:{secs:02d}"
                    else:
                        duration_str = f"{mins}:{secs:02d}"
                else:
                    duration_str = "Unknown"
                
                # Format view count
                view_count = video.get('view_count')
                if view_count:
                    if view_count >= 1000000:
                        views_str = f"{view_count/1000000:.1f}M views"
                    elif view_count >= 1000:
                        views_str = f"{view_count/1000:.1f}K views"
                    else:
                        views_str = f"{view_count} views"
                else:
                    views_str = "Unknown"
                
                video_data = {
                    'title': video.get('title', 'Unknown'),
                    'url': video.get('url') or f"https://www.youtube.com/watch?v={video.get('id', '')}",
                    'video_id': video.get('id', ''),
                    'duration': duration_str,
                    'duration_seconds': duration_secs,
                    'views': views_str,
                    'view_count': view_count,
                    'upload_date': video.get('upload_date', 'Unknown'),
                    'channel': video.get('channel') or video.get('uploader', 'Unknown'),
                    'description': (video.get('description') or '')[:200],
                    'thumbnail': video.get('thumbnail', '')
                }
                
                # Filter by year if specified
                if filter_year:
                    upload_date = video_data['upload_date']
                    if upload_date and upload_date != 'Unknown':
                        # yt-dlp provides date as YYYYMMDD
                        try:
                            video_year = int(upload_date[:4])
                            if video_year != filter_year:
                                continue
                        except (ValueError, TypeError):
                            pass
                
                videos.append(video_data)
                
                if len(videos) >= max_results:
                    break
                    
            except json.JSONDecodeError:
                continue
        
        return videos
        
    except subprocess.TimeoutExpired:
        print("Error: YouTube search timed out", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Error: yt-dlp not found. Install with: pip install yt-dlp", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error searching YouTube: {str(e)}", file=sys.stderr)
        return []


def format_results(videos, output_format='text'):
    """Format results for display"""
    if output_format == 'json':
        return json.dumps(videos, indent=2, ensure_ascii=False)
    
    # Text format
    output = []
    output.append(f"\n[WORKFLOW] YouTube Search Results ({len(videos)} videos found)\n")
    output.append("=" * 60)
    
    for i, video in enumerate(videos, 1):
        output.append(f"\n📹 Result {i}:")
        output.append(f"   Title: {video['title']}")
        output.append(f"   URL: {video['url']}")
        output.append(f"   Duration: {video['duration']}")
        output.append(f"   Views: {video['views']}")
        output.append(f"   Uploaded: {video['upload_date']}")
        output.append(f"   Channel: {video['channel']}")
        if video['description']:
            output.append(f"   Description: {video['description'][:100]}...")
        output.append("-" * 40)
    
    return '\n'.join(output)


def get_video_details(video_url):
    """Get detailed information about a specific video using yt-dlp"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            video_url
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode != 0:
            return None
            
        video_info = json.loads(result.stdout)
        
        duration_secs = video_info.get('duration', 0)
        
        return {
            'title': video_info.get('title', 'Unknown'),
            'duration_seconds': duration_secs,
            'views': video_info.get('view_count', 'Unknown'),
            'upload_date': video_info.get('upload_date', 'Unknown'),
            'channel': video_info.get('channel') or video_info.get('uploader', 'Unknown'),
            'description': (video_info.get('description') or '')[:500],
            'is_live': video_info.get('is_live', False),
            'category': video_info.get('categories', ['Unknown'])[0] if video_info.get('categories') else 'Unknown'
        }
    except Exception as e:
        print(f"Error getting video details: {str(e)}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Search YouTube for videos using yt-dlp. Returns video titles, URLs, and metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_search.py --query "electoral bonds interview"
  python youtube_search.py --query "electoral bonds" --max 5 --year 2018
  python youtube_search.py --query "Raghuram Rajan interview" --json
  python youtube_search.py --video-url "https://youtube.com/watch?v=xxx" --details
  python youtube_search.py --query "electoral bonds" --download-transcripts-dir "./Projects/my_project/assets/transcripts"
        """
    )
    
    parser.add_argument("--query", "-q", help="Search query for YouTube videos")
    parser.add_argument("--max", "-m", type=int, default=10, help="Maximum number of results (default: 10)")
    parser.add_argument("--year", "-y", type=int, help="Filter videos from a specific year (e.g., 2018)")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    parser.add_argument("--video-url", help="Get details for a specific video URL")
    parser.add_argument("--details", "-d", action="store_true", help="Get detailed info for video URL")
    parser.add_argument("--sort-views", action="store_true", help="Sort results by view count (highest first)")
    parser.add_argument("--download-transcripts-dir", help="Directory path to save transcripts of search results")
    
    args = parser.parse_args()
    
    if args.video_url and args.details:
        # Get details for specific video
        details = get_video_details(args.video_url)
        if details:
            if args.json:
                print(json.dumps(details, indent=2, ensure_ascii=False))
            else:
                print("\n📺 Video Details:")
                for key, value in details.items():
                    print(f"   {key}: {value}")
        else:
            print("Error: Could not retrieve video details")
            sys.exit(1)
    elif args.query:
        # Search for videos
        videos = search_youtube(args.query, args.max, args.year)
        
        if not videos:
            print(f"No videos found for query: {args.query}")
            sys.exit(0)
        
        # Sort by view count if requested
        if args.sort_views:
            videos.sort(key=lambda v: v.get('view_count') or 0, reverse=True)
            # Trim to max after sorting
            videos = videos[:args.max]
        
        output_format = 'json' if args.json else 'text'
        print(format_results(videos, output_format))
        
        # Download transcripts if directory is specified
        if args.download_transcripts_dir:
            os.makedirs(args.download_transcripts_dir, exist_ok=True)
            print(f"\n📥 Automatically downloading transcripts for top {len(videos)} videos to {args.download_transcripts_dir}...")
            tools_dir = os.path.dirname(os.path.abspath(__file__))
            caption_reader_path = os.path.join(tools_dir, "caption_reader.py")
            
            for video in videos:
                video_url = video['url']
                video_id = video['video_id']
                if not video_id:
                    continue
                output_file = os.path.join(args.download_transcripts_dir, f"{video_id}_transcript.txt")
                print(f"   Downloading transcript for: {video['title']} ({video_url})")
                
                cmd = [
                    sys.executable,
                    caption_reader_path,
                    "--url", video_url,
                    "--timestamps"
                ]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if res.returncode == 0:
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(res.stdout)
                        print(f"   [OK] Saved transcript: {output_file}")
                    else:
                        print(f"   [FAIL] Failed to get transcript for {video_id}: {res.stderr.strip() if res.stderr else 'Unknown error'}")
                except Exception as e:
                    print(f"   [FAIL] Error downloading transcript for {video_id}: {e}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
