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
from datetime import datetime

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
        search_query = f"ytsearch{max_results * 2}:{query}"  # Get extra to filter
        
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
    output.append(f"\n🎬 YouTube Search Results ({len(videos)} videos found)\n")
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
        """
    )
    
    parser.add_argument("--query", "-q", help="Search query for YouTube videos")
    parser.add_argument("--max", "-m", type=int, default=10, help="Maximum number of results (default: 10)")
    parser.add_argument("--year", "-y", type=int, help="Filter videos from a specific year (e.g., 2018)")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    parser.add_argument("--video-url", help="Get details for a specific video URL")
    parser.add_argument("--details", "-d", action="store_true", help="Get detailed info for video URL")
    
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
        
        output_format = 'json' if args.json else 'text'
        print(format_results(videos, output_format))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
