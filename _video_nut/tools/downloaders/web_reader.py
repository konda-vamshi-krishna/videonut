#!/usr/bin/env python3
"""
Web Page Reader for VideoNut

Scrapes text content from web pages using Trafilatura for clean article extraction 
(boilerplate removal), falling back to Playwright for JavaScript-heavy single-page apps (SPAs)
or when Trafilatura fails. Logs all crawls to the audit log.

Usage:
    python web_reader.py --url "https://example.com/article"
    python web_reader.py --url "https://example.com/article" --project "Projects/my_project"
"""

import sys
import argparse
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

# Try to import trafilatura
try:
    import trafilatura
    has_trafilatura = True
except ImportError:
    has_trafilatura = False


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


def read_webpage(url, project_path=None):
    if not project_path:
        project_path = "."
        
    # Add random delay to implement rate limiting
    delay = uniform(1, 2)
    print(f"Rate limiting: Waiting {delay:.2f} seconds before accessing {url}")
    time.sleep(delay)

    clean_text = None
    engine_used = ""
    error_msg = ""

    # 1. Try Trafilatura first
    if has_trafilatura:
        try:
            print("🕷️ Crawling webpage with Trafilatura...")
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                # Extract text with metadata and basic formatting preserved
                clean_text = trafilatura.extract(downloaded, include_links=True, include_images=False)
                if clean_text:
                    engine_used = "trafilatura"
                    print("✅ Clean text extracted successfully via Trafilatura")
                else:
                    print("⚠️ Trafilatura returned empty content. Trying Playwright fallback...")
            else:
                print("⚠️ Trafilatura failed to download page. Trying Playwright fallback...")
        except Exception as e:
            print(f"⚠️ Trafilatura error: {e}. Trying Playwright fallback...")
            error_msg += f"Trafilatura error: {e}. "
    else:
        print("ℹ️ Trafilatura is not installed. Using Playwright directly...")

    # 2. Playwright Fallback if Trafilatura failed or is missing
    if not clean_text:
        try:
            print("🌐 Launching Playwright headless browser fallback...")
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Set realistic user agent headers
                page.set_extra_http_headers({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                })
                
                # Navigate
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                
                # Extract innerText to get text as seen by a browser user
                text = page.evaluate("document.body.innerText")
                clean_text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
                browser.close()
                
                if clean_text:
                    engine_used = "playwright-fallback"
                    print("✅ Text content extracted successfully via Playwright browser")
                else:
                    raise ValueError("Playwright returned empty page content")
        except Exception as e:
            print(f"❌ Playwright fallback failed: {e}")
            error_msg += f"Playwright error: {e}."
            log_action_to_audit(
                project_path,
                "Failed to crawl webpage",
                url=url,
                status="failed",
                details=error_msg
            )
            sys.exit(1)

    # 3. Output text with smart truncation if needed
    MAX_TOTAL = 40000
    INTRO_SIZE = 8000
    OUTRO_SIZE = 8000
    
    if len(clean_text) > MAX_TOTAL:
        intro = clean_text[:INTRO_SIZE]
        outro = clean_text[-OUTRO_SIZE:]
        truncated_chars = len(clean_text) - MAX_TOTAL
        
        print(f"--- CONTENT START (First {INTRO_SIZE} chars) ---")
        print(intro)
        print(f"\n\n[... {truncated_chars:,} CHARACTERS TRUNCATED - Middle section omitted to preserve intro and conclusion ...]\n\n")
        print(f"--- CONTENT END (Last {OUTRO_SIZE} chars) ---")
        print(outro)
    else:
        print(clean_text)

    log_action_to_audit(
        project_path,
        f"Crawled webpage ({len(clean_text)} chars)",
        url=url,
        status="ok",
        details=f"Engine: {engine_used}"
    )


def main():
    parser = argparse.ArgumentParser(description="Extract clean text from web pages.")
    parser.add_argument("--url", required=True, help="Webpage URL to read")
    parser.add_argument("--project", "-p", help="Project directory path for logging")
    args = parser.parse_args()
    
    read_webpage(args.url, args.project)


if __name__ == "__main__":
    main()
