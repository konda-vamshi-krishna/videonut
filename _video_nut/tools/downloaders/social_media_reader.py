#!/usr/bin/env python3
"""
Social Media Post Reader for VideoNut

Extracts text content and metadata from Twitter/X posts without requiring API 
keys or login sessions. Uses Nitter public mirrors and ntscraper to scrape tweets 
and perform keyword searches. Logs reads and searches to the audit trail.

Usage:
    python social_media_reader.py --url "https://twitter.com/user/status/123456"
    python social_media_reader.py --search "electoral bonds scam" --output "./Projects/test/tweets.json"
"""

import sys
import os
import argparse
import json
import re
import time
import urllib.parse
from random import uniform
from pathlib import Path
import requests
from bs4 import BeautifulSoup

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

# Try to import ntscraper
try:
    from ntscraper import Nitter as NTNitter
    has_ntscraper = True
except ImportError:
    has_ntscraper = False

NITTER_MIRRORS = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.woodland.cafe"
]


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


def read_tweet_html(url) -> dict:
    """Fallback scraping method parsing Nitter HTML directly using requests."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    last_err = None
    for mirror in NITTER_MIRRORS:
        # Resolve target Nitter URL
        nitter_url = url
        for domain in ["twitter.com", "x.com", "mobile.twitter.com", "mobile.x.com"]:
            nitter_url = nitter_url.replace(domain, mirror)
            
        try:
            print(f"[INVESTIGATOR] Requesting Nitter mirror: {nitter_url}")
            res = requests.get(nitter_url, headers=headers, timeout=15)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Extract content
            content_div = soup.find(class_='tweet-content')
            if not content_div:
                continue
                
            text = content_div.get_text().strip()
            
            fullname_div = soup.find(class_='fullname')
            fullname = fullname_div.get_text().strip() if fullname_div else ""
            
            username_div = soup.find(class_='username')
            username = username_div.get_text().strip() if username_div else ""
            
            date_div = soup.find(class_='tweet-date')
            date_str = ""
            if date_div:
                a_tag = date_div.find('a')
                if a_tag and a_tag.get('title'):
                    date_str = a_tag['title']
                else:
                    date_str = date_div.get_text().strip()
            
            # Extract attachments
            media_urls = []
            attachments = soup.find(class_='attachments')
            if attachments:
                for img in attachments.find_all('img'):
                    if img.get('src'):
                        # Normalize source link relative to mirror
                        src = img['src']
                        if src.startswith('/'):
                            src = f"https://{mirror}{src}"
                        media_urls.append(src)
                for video in attachments.find_all('video'):
                    if video.get('src'):
                        src = video['src']
                        if src.startswith('/'):
                            src = f"https://{mirror}{src}"
                        media_urls.append(src)
                        
            return {
                "author": f"{fullname} ({username})".strip(),
                "text": text,
                "timestamp": date_str,
                "media_urls": media_urls,
                "url": url,
                "scraped_via": f"html-mirror-{mirror}"
            }
        except Exception as e:
            print(f"⚠️ Mirror {mirror} failed: {e}")
            last_err = e
            
    raise last_err or ValueError("Failed to extract tweet from all Nitter mirrors")


def read_tweet_ntscraper(url) -> dict:
    """Primary tweet scraper using ntscraper library."""
    if not has_ntscraper:
        raise ImportError("ntscraper is not installed")
        
    match = re.search(r'/(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/status/(\d+)', url)
    if not match:
        raise ValueError(f"Could not parse status tweet URL: {url}")
        
    username, tweet_id = match.groups()
    
    # Try ntscraper
    nitter = NTNitter()
    print(f"[INVESTIGATOR] Scraping tweet ID {tweet_id} via ntscraper...")
    
    # ntscraper get_tweets with user mode and limit=1
    tweets = nitter.get_tweets(username, mode='user', number=5)
    for tweet in tweets.get('tweets', []):
        # Find matching tweet ID
        # ntscraper ID or link match
        tweet_link = tweet.get('link', '')
        if tweet_id in tweet_link:
            return {
                "author": tweet.get('user', {}).get('name', username),
                "text": tweet.get('text', ''),
                "timestamp": tweet.get('date', ''),
                "media_urls": tweet.get('pictures', []) + tweet.get('videos', []),
                "url": url,
                "scraped_via": "ntscraper"
            }
            
    # If not found in recent user feed, fallback to HTML scrape
    print("⚠️ Tweet not found in recent timeline feed. Falling back to HTML scrape...")
    return read_tweet_html(url)


def read_tweet(url, project_path=None) -> dict:
    """Fetches a single tweet using ntscraper or HTML fallback."""
    if not project_path:
        project_path = "."
        
    delay = uniform(1, 2)
    print(f"Waiting {delay:.2f} seconds before accessing social post...")
    time.sleep(delay)

    scraped_data = None
    
    if has_ntscraper:
        try:
            scraped_data = read_tweet_ntscraper(url)
        except Exception as e:
            print(f"⚠️ ntscraper failed: {e}. Trying raw HTML fallback...")
            
    if not scraped_data:
        try:
            scraped_data = read_tweet_html(url)
        except Exception as e:
            print(f"[FAIL] Scraper failed: {e}")
            log_action_to_audit(project_path, f"Failed to read tweet: {e}", url=url, status="failed")
            sys.exit(1)

    log_action_to_audit(
        project_path,
        f"Read tweet by {scraped_data.get('author')}",
        url=url,
        status="ok",
        details=f"Method: {scraped_data.get('scraped_via')}"
    )
    return scraped_data


def search_tweets(query, max_results=10, project_path=None) -> list[dict]:
    """Searches Nitter mirrors for tweets matching a query."""
    if not project_path:
        project_path = "."
        
    delay = uniform(1, 2)
    print(f"Waiting {delay:.2f} seconds before searching tweets...")
    time.sleep(delay)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    encoded_query = urllib.parse.quote(query)
    results = []
    
    for mirror in NITTER_MIRRORS:
        search_url = f"https://{mirror}/search?f=tweets&q={encoded_query}"
        try:
            print(f"[INVESTIGATOR] Searching Nitter mirror: https://{mirror}")
            res = requests.get(search_url, headers=headers, timeout=15)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            tweet_items = soup.find_all(class_='timeline-item')
            
            for item in tweet_items:
                if len(results) >= max_results:
                    break
                    
                content_div = item.find(class_='tweet-content')
                if not content_div:
                    continue
                text = content_div.get_text().strip()
                
                fullname_div = item.find(class_='fullname')
                fullname = fullname_div.get_text().strip() if fullname_div else ""
                
                username_div = item.find(class_='username')
                username = username_div.get_text().strip() if username_div else ""
                
                date_div = item.find(class_='tweet-date')
                date_str = ""
                if date_div:
                    a_tag = date_div.find('a')
                    date_str = a_tag['title'] if a_tag and a_tag.get('title') else date_div.get_text().strip()
                
                tweet_link_el = item.find(class_='tweet-link')
                tweet_url = f"https://twitter.com{tweet_link_el['href']}" if tweet_link_el else ""
                
                results.append({
                    "author": f"{fullname} ({username})".strip(),
                    "text": text,
                    "timestamp": date_str,
                    "url": tweet_url
                })
                
            if results:
                print(f"[OK] Search yielded {len(results)} tweets on {mirror}")
                log_action_to_audit(
                    project_path,
                    f"Searched tweets for '{query}' (Found {len(results)} matches)",
                    status="ok",
                    details=f"Mirror: {mirror}"
                )
                return results
        except Exception as e:
            print(f"⚠️ Search failed on {mirror}: {e}")
            continue
            
    log_action_to_audit(
        project_path,
        f"Searched tweets for '{query}' (0 matches)",
        status="skipped"
    )
    return results


def main():
    parser = argparse.ArgumentParser(description="Read Twitter/X post text or search posts.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Tweet URL to read")
    group.add_argument("--search", help="Search query keyword")
    
    parser.add_argument("--output", "-o", help="Path to save scraped results as JSON")
    parser.add_argument("--project-dir", help="Project directory path for logging")
    parser.add_argument("--limit", type=int, default=10, help="Maximum search results (default: 10)")
    
    args = parser.parse_args()
    
    if args.url:
        result = read_tweet(args.url, args.project_dir)
        print("\n📢 Tweet Content:")
        print(f"Author:    {result['author']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Text:      {result['text']}")
        if result.get('media_urls'):
            print(f"Media:     {', '.join(result['media_urls'])}")
            
        if args.output:
            out_file = Path(args.output)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n[SAVE] Saved JSON results to: {out_file}")
            
    elif args.search:
        results = search_tweets(args.search, args.limit, args.project_dir)
        print(f"\n[SCAN] Search Results for '{args.search}' ({len(results)} tweets):\n")
        for idx, tweet in enumerate(results):
            print(f"{idx+1}. [{tweet['author']}] ({tweet['timestamp']})")
            print(f"   Text: {tweet['text']}")
            print(f"   URL:  {tweet['url']}\n")
            
        if args.output and results:
            out_file = Path(args.output)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Saved JSON results to: {out_file}")


if __name__ == "__main__":
    main()
