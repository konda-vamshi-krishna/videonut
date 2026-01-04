#!/usr/bin/env python3
"""
Archive URL Tool for VideoNut

Archives web pages to Archive.is (archive.today) to preserve them before they expire.
News articles especially tend to disappear or go behind paywalls.

Usage:
    python archive_url.py --url "https://example.com/article"
    python archive_url.py --url "https://example.com" --check-only
    python archive_url.py --batch "urls.txt" --output "archived_urls.txt"
"""

import sys
import argparse
import time
import json
from random import uniform

try:
    import requests
except ImportError:
    print("Error: requests not installed. Install with: pip install requests")
    sys.exit(1)


def check_existing_archive(url):
    """
    Check if a URL is already archived on Archive.is.
    Returns the archived URL if found, None otherwise.
    """
    check_url = f"https://archive.is/{url}"
    
    try:
        response = requests.get(check_url, timeout=10, allow_redirects=True)
        
        # If we get redirected to an archived page, it exists
        if response.status_code == 200 and "archive.is" in response.url:
            return response.url
        return None
    except Exception as e:
        print(f"Error checking archive: {e}")
        return None


def archive_url(url, wait_for_complete=True):
    """
    Submit a URL to Archive.is for archiving.
    
    Args:
        url: The URL to archive
        wait_for_complete: Whether to wait for archiving to complete
    
    Returns:
        Dict with status and archived URL
    """
    result = {
        'success': False,
        'original_url': url,
        'archived_url': None,
        'message': ''
    }
    
    # Rate limiting
    delay = uniform(2, 4)
    print(f"Rate limiting: Waiting {delay:.2f} seconds...")
    time.sleep(delay)
    
    # First, check if already archived
    print(f"Checking if {url} is already archived...")
    existing = check_existing_archive(url)
    if existing:
        result['success'] = True
        result['archived_url'] = existing
        result['message'] = "Already archived"
        return result
    
    # Submit to archive.is
    print(f"Submitting {url} to Archive.is...")
    
    archive_submit_url = "https://archive.is/submit/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    data = {
        'url': url,
        'anyway': 1
    }
    
    try:
        response = requests.post(
            archive_submit_url, 
            data=data, 
            headers=headers, 
            timeout=60,
            allow_redirects=True
        )
        
        # Check for the archived URL in response
        if response.status_code == 200:
            # The response URL should be the archived page
            if "archive.is" in response.url or "archive.today" in response.url:
                result['success'] = True
                result['archived_url'] = response.url
                result['message'] = "Successfully archived"
            else:
                # Sometimes archive.is returns a page with the archive link
                # Try to extract it from the page content
                if 'id="SHARE_LONGLINK"' in response.text:
                    # Parse out the archive URL
                    import re
                    match = re.search(r'value="(https://archive\.[^"]+)"', response.text)
                    if match:
                        result['success'] = True
                        result['archived_url'] = match.group(1)
                        result['message'] = "Successfully archived"
                    else:
                        result['message'] = "Archived but couldn't extract URL"
                else:
                    result['message'] = "Submission sent - check archive.is manually"
        else:
            result['message'] = f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        result['message'] = "Request timed out - archive.is may be slow"
    except Exception as e:
        result['message'] = f"Error: {str(e)}"
    
    return result


def archive_batch(urls, output_file=None):
    """
    Archive multiple URLs.
    
    Args:
        urls: List of URLs to archive
        output_file: Optional file to save results
    
    Returns:
        List of results
    """
    results = []
    total = len(urls)
    
    for i, url in enumerate(urls, 1):
        url = url.strip()
        if not url or url.startswith('#'):
            continue
            
        print(f"\n[{i}/{total}] Processing: {url}")
        result = archive_url(url)
        results.append(result)
        
        if result['success']:
            print(f"✅ Archived: {result['archived_url']}")
        else:
            print(f"❌ Failed: {result['message']}")
    
    # Save results if output file specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Archived URLs\n")
            f.write("# Generated by archive_url.py\n\n")
            
            for r in results:
                if r['success']:
                    f.write(f"ORIGINAL: {r['original_url']}\n")
                    f.write(f"ARCHIVED: {r['archived_url']}\n\n")
                else:
                    f.write(f"FAILED: {r['original_url']}\n")
                    f.write(f"REASON: {r['message']}\n\n")
        
        print(f"\n📁 Results saved to: {output_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Archive web pages to Archive.is for permanent preservation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Archive a single URL
  python archive_url.py --url "https://timesofindia.com/article/123"
  
  # Check if URL is already archived (don't create new)
  python archive_url.py --url "https://example.com" --check-only
  
  # Archive multiple URLs from a file
  python archive_url.py --batch "urls.txt" --output "archived.txt"
  
  # Output as JSON
  python archive_url.py --url "https://example.com" --json

Why Archive?
  - News articles often get deleted or moved
  - Paywalls can block access later
  - Creates permanent proof of what was published
  - Essential for journalism and research
        """
    )
    
    parser.add_argument("--url", "-u", help="URL to archive")
    parser.add_argument("--check-only", "-c", action="store_true", 
                        help="Only check if archived, don't create new archive")
    parser.add_argument("--batch", "-b", help="File containing URLs to archive (one per line)")
    parser.add_argument("--output", "-o", help="Output file for batch results")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.url and not args.batch:
        parser.print_help()
        print("\nError: Either --url or --batch is required")
        sys.exit(1)
    
    if args.batch:
        # Batch mode
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                urls = f.readlines()
            results = archive_batch(urls, args.output)
            
            # Summary
            success = sum(1 for r in results if r['success'])
            print(f"\n📊 Summary: {success}/{len(results)} successfully archived")
            
        except FileNotFoundError:
            print(f"Error: File not found: {args.batch}")
            sys.exit(1)
    
    else:
        # Single URL mode
        if args.check_only:
            print(f"Checking archive status for: {args.url}")
            archived = check_existing_archive(args.url)
            
            if archived:
                if args.json:
                    print(json.dumps({'archived': True, 'url': archived}))
                else:
                    print(f"✅ Already archived: {archived}")
            else:
                if args.json:
                    print(json.dumps({'archived': False, 'url': None}))
                else:
                    print("❌ Not archived yet")
        else:
            result = archive_url(args.url)
            
            if args.json:
                print(json.dumps(result))
            else:
                if result['success']:
                    print(f"\n✅ Successfully archived!")
                    print(f"   Original: {result['original_url']}")
                    print(f"   Archived: {result['archived_url']}")
                else:
                    print(f"\n❌ Archive failed: {result['message']}")
                    print(f"   Try manually at: https://archive.is/")


if __name__ == "__main__":
    main()
