#!/usr/bin/env python3
"""
PDF Page Screenshotter for VideoNut
Takes screenshots of specific PDF pages, optionally highlighting search terms.
Uses Playwright to render PDFs in browser for high-quality screenshots.

USAGE:
  # Screenshot specific page from PDF
  python pdf_screenshotter.py --url "https://example.com/report.pdf" --page 3 --output "page3.png"
  
  # Search for term and screenshot the page where it's found
  python pdf_screenshotter.py --url "https://example.com/report.pdf" --search "Prime Minister" --output "pm_quote.png"
"""

import sys
import os
import argparse
import requests
import io
import time
from random import uniform
from pypdf import PdfReader

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)


def download_pdf_to_temp(url, temp_path):
    """Download PDF to a temporary file."""
    delay = uniform(1, 2)
    print(f"⏳ Rate limiting: Waiting {delay:.2f} seconds...")
    time.sleep(delay)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    with open(temp_path, 'wb') as f:
        f.write(response.content)
    
    return temp_path


def find_page_with_term(pdf_path, search_term):
    """Find the first page containing the search term."""
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        search_lower = search_term.lower()
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and search_lower in page_text.lower():
                return i + 1  # Return 1-indexed page number
    
    return None


def screenshot_pdf_page(pdf_path, page_number, output_path, search_term=None, width=1280, height=1600):
    """
    Take a screenshot of a specific PDF page using browser rendering.
    
    Args:
        pdf_path: Local path to PDF file
        page_number: Page to screenshot (1-indexed)
        output_path: Where to save the screenshot
        search_term: Optional term to highlight on the page
        width: Viewport width
        height: Viewport height
    """
    result = {
        'success': False,
        'page': page_number,
        'search_found': False,
        'message': '',
        'output_path': output_path
    }
    
    # Verify PDF exists and page is valid
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        total_pages = len(reader.pages)
        
        if page_number < 1 or page_number > total_pages:
            result['message'] = f"Page {page_number} not found. PDF has {total_pages} pages."
            return result
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': width, 'height': height}
        )
        page = context.new_page()
        
        try:
            # Open PDF in browser using file:// protocol
            abs_path = os.path.abspath(pdf_path)
            pdf_url = f"file:///{abs_path.replace(os.sep, '/')}"
            
            print(f"🌐 Opening PDF in browser...")
            page.goto(pdf_url, timeout=30000, wait_until='networkidle')
            
            # Wait for PDF to render
            page.wait_for_timeout(3000)
            
            # Navigate to specific page
            # Most PDF viewers use #page=N in URL
            if page_number > 1:
                page.goto(f"{pdf_url}#page={page_number}", timeout=30000)
                page.wait_for_timeout(2000)
            
            # If search term provided, try to find and highlight
            if search_term:
                print(f"🔍 Searching for '{search_term}'...")
                # Use browser's find function (Ctrl+F simulation)
                # This is a workaround since direct PDF text selection is complex
                page.keyboard.press("Control+f")
                page.wait_for_timeout(500)
                page.keyboard.type(search_term)
                page.wait_for_timeout(1000)
                page.keyboard.press("Escape")
                result['search_found'] = True
            
            # Take screenshot
            print(f"📸 Taking screenshot of page {page_number}...")
            page.screenshot(path=output_path, full_page=False)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                result['success'] = True
                result['message'] = f"Screenshot saved: {output_path}"
                print(f"✅ {result['message']}")
            else:
                result['message'] = "Screenshot file is empty or not created"
                
        except Exception as e:
            result['message'] = f"Error: {str(e)}"
            print(f"❌ {result['message']}")
            
        finally:
            browser.close()
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Screenshot specific pages from PDF documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Screenshot specific page
  python pdf_screenshotter.py --url "https://example.com/report.pdf" --page 3 --output "page3.png"
  
  # Auto-find page with search term and screenshot
  python pdf_screenshotter.py --url "https://example.com/report.pdf" --search "Prime Minister" --output "pm_quote.png"
  
  # Screenshot local PDF file
  python pdf_screenshotter.py --file "report.pdf" --page 5 --output "page5.png"
        """
    )
    
    parser.add_argument("--url", "-u", help="URL of the PDF document")
    parser.add_argument("--file", "-f", help="Local path to PDF file")
    parser.add_argument("--page", "-p", type=int, help="Page number to screenshot (1-indexed)")
    parser.add_argument("--search", "-s", help="Search for term and screenshot that page")
    parser.add_argument("--output", "-o", required=True, help="Output file path for screenshot")
    parser.add_argument("--width", type=int, default=1280, help="Viewport width (default: 1280)")
    parser.add_argument("--height", type=int, default=1600, help="Viewport height (default: 1600)")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.url and not args.file:
        print("Error: Either --url or --file must be provided")
        sys.exit(1)
    
    if not args.page and not args.search:
        print("Error: Either --page or --search must be provided")
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Get PDF file (download if URL provided)
    if args.url:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.temp')
        os.makedirs(temp_dir, exist_ok=True)
        pdf_path = os.path.join(temp_dir, 'temp_pdf.pdf')
        
        print(f"📥 Downloading PDF from {args.url}...")
        try:
            download_pdf_to_temp(args.url, pdf_path)
            print(f"✅ PDF downloaded")
        except Exception as e:
            print(f"❌ Failed to download PDF: {e}")
            sys.exit(1)
    else:
        pdf_path = args.file
        if not os.path.exists(pdf_path):
            print(f"Error: File not found: {pdf_path}")
            sys.exit(1)
    
    # Determine page number
    page_number = args.page
    if args.search:
        print(f"🔍 Searching for '{args.search}' in PDF...")
        found_page = find_page_with_term(pdf_path, args.search)
        if found_page:
            page_number = found_page
            print(f"✅ Found '{args.search}' on page {page_number}")
        else:
            print(f"❌ '{args.search}' not found in PDF")
            sys.exit(1)
    
    # Take screenshot
    result = screenshot_pdf_page(
        pdf_path, 
        page_number, 
        args.output,
        search_term=args.search,
        width=args.width,
        height=args.height
    )
    
    if result['success']:
        sys.exit(0)
    else:
        print(f"❌ Failed: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
