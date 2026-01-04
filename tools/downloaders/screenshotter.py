import sys
import os
import argparse
import time
from random import uniform
from playwright.sync_api import sync_playwright

def take_screenshot(url, output_path):
    # Add random delay to implement rate limiting
    delay = uniform(1, 3)  # Random delay between 1-3 seconds
    print(f"Rate limiting: Waiting {delay:.2f} seconds before accessing {url}")
    time.sleep(delay)

    with sync_playwright() as p:
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

        try:
            print(f"Navigating to {url}...")
            page.goto(url, timeout=30000)
            # Wait a bit for dynamic content (e.g., Twitter embeds)
            page.wait_for_timeout(2000)

            page.screenshot(path=output_path, full_page=False)

            # Validate that the file was created and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    print(f"Error: Screenshot file is empty: {output_path}")
                    sys.exit(1)
                else:
                    print(f"File validation: {output_path} created with size {file_size} bytes")
            else:
                print(f"Error: Screenshot file does not exist: {output_path}")
                sys.exit(1)

        except Exception as e:
            print(f"Error taking screenshot: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    take_screenshot(args.url, args.output)
