#!/usr/bin/env python3
"""
Screenshotter for VideoNut

Takes screenshots of webpages. Bypasses Twitter/X login walls by automatically 
redirecting to available public Nitter mirrors. Logs screenshots taken to the audit trail.

Usage:
    python screenshotter.py --url "https://example.com" --output "./Projects/test/assets/images/screenshot.png"
    python screenshotter.py --url "https://twitter.com/username/status/123456" --output "./Projects/test/assets/images/tweet.png"
"""

import sys
import os
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

try:
    from playwright.sync_api import sync_playwright
    has_playwright = True
except ImportError:
    has_playwright = False

# List of public Nitter mirrors to try in order if one is down
NITTER_MIRRORS = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.net"
]


def log_action_to_audit(project_path, action, url="", local_path="", status="ok", details=""):
    """Wrapper for logging to audit trail if available."""
    if has_audit_logger:
        audit_logger.log_action(
            project_path=project_path,
            category="screenshot",
            action=action,
            url=url,
            local_path=local_path,
            status=status,
            details=details
        )


def bypass_twitter_url(url: str, mirror: str) -> str:
    """Replaces twitter/x domain with a Nitter mirror."""
    resolved_url = url
    for domain in ["twitter.com", "x.com", "mobile.twitter.com", "mobile.x.com"]:
        if domain in resolved_url:
            resolved_url = resolved_url.replace(domain, mirror)
            break
    return resolved_url


def take_screenshot(url, output_path, project_path=None):
    if not project_path:
        project_path = str(Path(output_path).parent.parent)

    if not has_playwright:
        print("Error: Playwright not installed. Install with: pip install playwright && playwright install chromium")
        log_action_to_audit(project_path, "Screenshot failed: Playwright missing", url=url, status="failed")
        sys.exit(1)

    # 1. Enforce rate limit delay
    delay = uniform(1, 2)
    print(f"Waiting {delay:.2f} seconds before capturing screenshot...")
    time.sleep(delay)

    # Ensure output directory exists
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    is_twitter = "twitter.com" in url or "x.com" in url
    urls_to_try = [url]
    
    if is_twitter:
        print("[TWITTER] Twitter/X URL detected. Adding Nitter mirror bypass targets...")
        for mirror in NITTER_MIRRORS:
            urls_to_try.append(bypass_twitter_url(url, mirror))

    # Try downloading with temporary output to avoid leaving partial/empty files
    temp_output = out_file.with_suffix(".tmp.png")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        success = False
        last_error = None
        attempted_url = ""

        # Try URLs (original or Nitter mirrors) until one works
        for target_url in urls_to_try:
            try:
                attempted_url = target_url
                if target_url != url:
                    print(f"[REWORK] Attempting Nitter mirror bypass: {target_url}")
                else:
                    print(f"[SCREENSHOT] Screenshotting: {target_url}")
                
                # Navigate
                page.goto(target_url, timeout=30000)
                
                # Wait for content to settle
                page.wait_for_timeout(3000)
                
                # Take screenshot (full_page=False to avoid massive pages, but captures standard viewport)
                page.screenshot(path=str(temp_output), full_page=False)
                
                # Validate file size
                if temp_output.exists() and temp_output.stat().st_size > 0:
                    success = True
                    break
                else:
                    raise IOError("Screenshot file is empty")
            except Exception as e:
                last_error = e
                print(f"⚠️ Failed for {target_url}: {e}")
                if temp_output.exists():
                    try:
                        temp_output.unlink()
                    except Exception:
                        pass

        browser.close()

        if success:
            # Move temp file to correct location (atomic)
            if out_file.exists():
                out_file.unlink()
            temp_output.replace(out_file)
            
            size = out_file.stat().st_size
            print(f"[OK] Screenshot saved successfully to {out_file} ({size:,} bytes)")
            
            details = f"Loaded URL: {attempted_url}"
            if attempted_url != url:
                details += " (Twitter Login Bypassed via Nitter)"
                
            log_action_to_audit(
                project_path, 
                "Captured webpage screenshot", 
                url=url, 
                local_path=str(out_file), 
                status="ok", 
                details=details
            )
        else:
            print(f"[FAIL] Failed to take screenshot for all attempts: {last_error}")
            log_action_to_audit(
                project_path,
                f"Failed to capture screenshot: {last_error}",
                url=url,
                status="failed",
                details=str(last_error)
            )
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Capture webpage screenshot.")
    parser.add_argument("--url", required=True, help="Webpage URL to capture")
    parser.add_argument("--output", required=True, help="Output image file path")
    parser.add_argument("--project-dir", help="Project directory path for logging")
    args = parser.parse_args()
    
    take_screenshot(args.url, args.output, args.project_dir)


if __name__ == "__main__":
    main()
