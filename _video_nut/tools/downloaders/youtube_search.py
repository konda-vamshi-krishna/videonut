#!/usr/bin/env python3
"""
YouTube Search Tool for VideoNut
Searches YouTube for videos matching a query and returns structured results.
Uses youtube-search-python library for searching without API key.
"""

import sys
import argparse
import json
from datetime import datetime

try:
    from youtubesearchpython import VideosSearch, Video
except ImportError:
    print("Error: youtube-search-python not installed. Install with: pip install youtube-search-python")
    sys.exit(1)


def search_youtube(query, max_results=10, filter_year=None):
    """
    Search YouTube for videos matching the query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 10)
        filter_year: Optional year to filter results (e.g., 2018 for videos from 2018)
    
    Returns:
        List of video dictionaries with title, url, duration, views, upload_date, channel
    """
    try:
        videos_search = VideosSearch(query, limit=max_results * 2)  # Get extra to filter
        results = videos_search.result()
        
        videos = []
        for video in results.get('result', []):
            video_data = {
                'title': video.get('title', 'Unknown'),
                'url': video.get('link', ''),
                'video_id': video.get('id', ''),
                'duration': video.get('duration', 'Unknown'),
                'views': video.get('viewCount', {}).get('text', 'Unknown'),
                'upload_date': video.get('publishedTime', 'Unknown'),
                'channel': video.get('channel', {}).get('name', 'Unknown'),
                'description': video.get('descriptionSnippet', [{}])[0].get('text', '') if video.get('descriptionSnippet') else '',
                'thumbnail': video.get('thumbnails', [{}])[0].get('url', '') if video.get('thumbnails') else ''
            }
            
            # Filter by year if specified
            if filter_year:
                upload_text = video_data['upload_date'].lower()
                # Check if it contains year info
                if str(filter_year) in upload_text or f"{filter_year}" in video_data['title']:
                    videos.append(video_data)
                elif 'year' in upload_text:
                    # Try to parse "X years ago"
                    try:
                        years_ago = int(upload_text.split()[0])
                        current_year = datetime.now().year
                        video_year = current_year - years_ago
                        if video_year <= filter_year:
                            videos.append(video_data)
                    except:
                        pass
            else:
                videos.append(video_data)
            
            if len(videos) >= max_results:
                break
        
        return videos
        
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
    """Get detailed information about a specific video"""
    try:
        video_info = Video.getInfo(video_url)
        return {
            'title': video_info.get('title', 'Unknown'),
            'duration_seconds': video_info.get('duration', {}).get('secondsText', 'Unknown'),
            'views': video_info.get('viewCount', {}).get('text', 'Unknown'),
            'upload_date': video_info.get('publishDate', 'Unknown'),
            'channel': video_info.get('channel', {}).get('name', 'Unknown'),
            'description': video_info.get('description', '')[:500],
            'is_live': video_info.get('isLiveNow', False),
            'category': video_info.get('category', 'Unknown')
        }
    except Exception as e:
        print(f"Error getting video details: {str(e)}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Search YouTube for videos. Returns video titles, URLs, and metadata.",
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
