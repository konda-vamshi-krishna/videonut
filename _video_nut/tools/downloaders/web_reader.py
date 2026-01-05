import sys
import argparse
import time
from random import uniform
from playwright.sync_api import sync_playwright

def read_webpage(url):
    try:
        # Add random delay to implement rate limiting
        delay = uniform(1, 3)  # Random delay between 1-3 seconds
        print(f"Rate limiting: Waiting {delay:.2f} seconds before accessing {url}")
        time.sleep(delay)

        with sync_playwright() as p:
            # Launch browser (headless by default)
            browser = p.chromium.launch()
            page = browser.new_page()

            # Set additional headers to appear more like a real user
            page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })

            # Navigate with a reasonable timeout
            page.goto(url, timeout=30000)

            # Wait for content to load (basic heuristic)
            page.wait_for_load_state("domcontentloaded")

            # Get the text content
            # We use evaluate to get innerText which mimics what a user sees (hidden text is ignored)
            text = page.evaluate("document.body.innerText")

            # Basic cleanup: Remove excessive newlines
            clean_text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

            # Smart truncation: Preserve intro AND conclusion (critical for research)
            MAX_TOTAL = 40000  # Increased from 25000
            INTRO_SIZE = 8000  # First portion (hook/summary)
            OUTRO_SIZE = 8000  # Last portion (conclusion/recommendations)
            
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

            browser.close()

    except Exception as e:
        print(f"Error reading webpage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    read_webpage(args.url)
