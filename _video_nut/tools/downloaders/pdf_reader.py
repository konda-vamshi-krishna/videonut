import sys
import requests
import io
import time
from random import uniform
from pypdf import PdfReader
import argparse
import re

def read_pdf(url, search_term=None, page_number=None):
    """
    Read a PDF from URL with optional search and page selection.
    
    Args:
        url: URL of the PDF
        search_term: Optional term to search for in the PDF
        page_number: Optional specific page to read (1-indexed)
    """
    # Add random delay to implement rate limiting
    delay = uniform(1, 3)
    print(f"Rate limiting: Waiting {delay:.2f} seconds before accessing {url}")
    time.sleep(delay)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        f = io.BytesIO(response.content)
        reader = PdfReader(f)
        total_pages = len(reader.pages)
        
        print(f"📄 PDF loaded: {total_pages} pages")
        
        # If specific page requested
        if page_number:
            if 1 <= page_number <= total_pages:
                text = reader.pages[page_number - 1].extract_text()
                print(f"\n--- Page {page_number} of {total_pages} ---")
                print(text)
                return
            else:
                print(f"Error: Page {page_number} not found. PDF has {total_pages} pages.")
                sys.exit(1)
        
        # If search term provided, find all occurrences
        if search_term:
            print(f"🔍 Searching for: '{search_term}'")
            matches = []
            search_lower = search_term.lower()
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and search_lower in page_text.lower():
                    # Find the context around the match
                    lines = page_text.split('\n')
                    for j, line in enumerate(lines):
                        if search_lower in line.lower():
                            # Get surrounding context (2 lines before/after)
                            context_start = max(0, j - 2)
                            context_end = min(len(lines), j + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            matches.append({
                                'page': i + 1,
                                'line': line.strip(),
                                'context': context
                            })
            
            if matches:
                print(f"\n✅ Found {len(matches)} matches for '{search_term}':\n")
                for idx, match in enumerate(matches[:10]):  # Limit to first 10 matches
                    print(f"{'='*60}")
                    print(f"📍 Match {idx+1} - Page {match['page']}")
                    print(f"{'='*60}")
                    print(f"Line: {match['line']}")
                    print(f"\nContext:")
                    print(match['context'])
                    print()
                
                if len(matches) > 10:
                    print(f"... and {len(matches) - 10} more matches")
                
                # Suggest best page for screenshot
                best_page = matches[0]['page']
                print(f"\n📸 Suggested page for screenshot: Page {best_page}")
                print(f"   Use: python pdf_reader.py --url \"{url}\" --page {best_page}")
            else:
                print(f"❌ No matches found for '{search_term}'")
            return
        
        # Default: Smart extraction with priority for first and last pages
        MAX_PAGES = 15
        MAX_CHARS = 20000
        
        text = ""
        pages_to_read = []
        
        if total_pages <= MAX_PAGES:
            pages_to_read = list(range(total_pages))
        else:
            # Smart selection: first 7 + last 4
            first_pages = list(range(min(7, total_pages)))
            last_pages = list(range(max(0, total_pages - 4), total_pages))
            pages_to_read = sorted(set(first_pages + last_pages))
            
            print(f"📄 Document has {total_pages} pages. Reading pages: {[p+1 for p in pages_to_read]} (first + last priority)")
        
        for i in pages_to_read:
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += f"\n--- Page {i+1} ---\n{page_text}"
        
        # Smart truncation with intro/conclusion preservation
        if len(text) > MAX_CHARS:
            intro = text[:8000]
            outro = text[-8000:]
            truncated = len(text) - MAX_CHARS
            print(f"--- PDF CONTENT START ---")
            print(intro)
            print(f"\n\n[... {truncated:,} characters truncated from middle ...]\n\n")
            print(f"--- PDF CONTENT END ---")
            print(outro)
        else:
            print(text)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Read and search PDF documents from URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read PDF with smart extraction (first + last pages)
  python pdf_reader.py --url "https://example.com/report.pdf"
  
  # Search for specific term in PDF
  python pdf_reader.py --url "https://example.com/report.pdf" --search "Prime Minister"
  
  # Read specific page
  python pdf_reader.py --url "https://example.com/report.pdf" --page 5
        """
    )
    
    parser.add_argument("--url", required=True, help="URL of the PDF document")
    parser.add_argument("--search", "-s", help="Search for specific term and show context")
    parser.add_argument("--page", "-p", type=int, help="Read specific page number (1-indexed)")
    
    args = parser.parse_args()
    read_pdf(args.url, search_term=args.search, page_number=args.page)


if __name__ == "__main__":
    main()
