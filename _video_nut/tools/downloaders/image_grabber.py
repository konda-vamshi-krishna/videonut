import os
import sys
import requests
import argparse
import mimetypes

# Enforce UTF-8 output encoding for Windows terminal safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from urllib.parse import urlparse

def is_safe_image_type(content_type, url):
    """
    Check if the content type is a safe image type.
    """
    safe_types = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
        'image/webp', 'image/bmp', 'image/svg+xml', 'image/tiff'
    }

    # Check content-type header
    if content_type and content_type.lower() in safe_types:
        return True

    # Fallback: check file extension from URL
    parsed_url = urlparse(url)
    file_ext = os.path.splitext(parsed_url.path)[1].lower()
    mime_type, _ = mimetypes.guess_type(f"dummy{file_ext}")

    if mime_type and mime_type in safe_types:
        return True

    return False

def get_file_size(response):
    """
    Get the file size from the response headers.
    """
    content_length = response.headers.get('content-length')
    if content_length:
        return int(content_length)
    return 0

def download_image(url, output_path):
    """
    Downloads an image from a URL with security validation.
    """
    # Ensure output directory exists if it's not the current directory
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    # Use standard Chrome User-Agent to bypass security filters (e.g. Wikimedia 403 blocks)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"Downloading image from: {url}")

        # Perform stream-based GET request directly to avoid double requests (HEAD + GET)
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        # Validate content type from headers
        content_type = response.headers.get('content-type', '').lower()
        if not is_safe_image_type(content_type, url):
            print(f"Security Error: Content type '{content_type}' is not a safe image type.")
            sys.exit(1)

        # Check file size (limit to 50MB)
        file_size = get_file_size(response)
        if file_size > 50 * 1024 * 1024:  # 50MB
            print(f"Security Error: File size {file_size} bytes exceeds 50MB limit.")
            sys.exit(1)

        # Write file in chunks with size validation
        total_size = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    total_size += len(chunk)
                    if total_size > 50 * 1024 * 1024:  # 50MB limit
                        print(f"Security Error: Downloaded file exceeds 50MB limit.")
                        os.remove(output_path)  # Clean up partial file
                        sys.exit(1)
                    f.write(chunk)

        print(f"Successfully saved to {output_path}")

    except Exception as e:
        print(f"Failed to download image: {e}")
        if "429" in str(e) or "403" in str(e):
            print("💡 Tip: The server is rate-limiting or blocking automated bots. Try downloading the image manually or using a proxy.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download an image.")
    parser.add_argument("--url", required=True, help="Image URL")
    parser.add_argument("--output", required=True, help="Output file path")

    args = parser.parse_args()

    download_image(args.url, args.output)