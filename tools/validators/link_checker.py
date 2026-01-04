import requests
import sys
import time
from random import uniform

def check_link(url):
    # Add random delay to implement rate limiting
    delay = uniform(1, 3)  # Random delay between 1-3 seconds
    print(f"Rate limiting: Waiting {delay:.2f} seconds before checking {url}", file=sys.stderr)
    time.sleep(delay)

    try:
        # More realistic User-Agent to appear like a regular browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)

        if response.status_code == 200:
            return True, "OK"
        else:
            # Retry with GET if HEAD fails (some servers block HEAD)
            response = requests.get(url, headers=headers, timeout=5, stream=True)
            if response.status_code == 200:
                return True, "OK"
            return False, f"Status Code: {response.status_code}"

    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"General error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        success, msg = check_link(url)
        print(f"{'VALID' if success else 'INVALID'}: {msg}")
    else:
        print("Usage: python link_checker.py [URL]")
