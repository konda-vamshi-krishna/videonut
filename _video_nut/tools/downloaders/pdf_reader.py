#!/usr/bin/env python3
"""
PDF Document Reader and Searcher for VideoNut

Downloads and parses PDF files from URLs, with layout-aware column parsing and 
table extraction using pdfplumber, falling back to pypdf if pdfplumber is not 
installed. Logs all reads to the audit trail.

Usage:
    python pdf_reader.py --url "https://example.com/report.pdf"
    python pdf_reader.py --url "https://example.com/report.pdf" --search "electoral bonds"
    python pdf_reader.py --url "https://example.com/report.pdf" --output "./Projects/my_project/assets/documents/report.pdf"
"""

import sys
import requests
import io
import time
from random import uniform
import argparse
import re
import os
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

# Try to import pdfplumber
try:
    import pdfplumber
    has_pdfplumber = True
except ImportError:
    has_pdfplumber = False

# Try to import pypdf (required fallback)
try:
    from pypdf import PdfReader
    has_pypdf = True
except ImportError:
    has_pypdf = False


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


def extract_pdf_pages_pdfplumber(pdf_bytes, page_number=None) -> tuple[list[str], str]:
    """Extract page text using pdfplumber with column/layout awareness."""
    pages_text = []
    engine_desc = "pdfplumber"
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        
        if page_number:
            if 1 <= page_number <= total_pages:
                page = pdf.pages[page_number - 1]
                # extract_text(layout=True) helps preserve column structures
                text = page.extract_text(layout=True) or ""
                pages_text.append(text)
            else:
                raise IndexError(f"Page {page_number} out of range (1-{total_pages})")
        else:
            # Smart page selection if full read
            MAX_PAGES = 15
            if total_pages <= MAX_PAGES:
                pages_to_read = list(range(total_pages))
            else:
                first_pages = list(range(min(7, total_pages)))
                last_pages = list(range(max(0, total_pages - 4), total_pages))
                pages_to_read = sorted(set(first_pages + last_pages))
                print(f"📄 PDF has {total_pages} pages. Reading pages {[p+1 for p in pages_to_read]} (pdfplumber smart selection)")
                engine_desc = f"pdfplumber (smart selection: {len(pages_to_read)}/{total_pages} pages)"
                
            for idx in pages_to_read:
                page = pdf.pages[idx]
                text = page.extract_text(layout=True) or ""
                pages_text.append(f"\n--- Page {idx+1} ---\n" + text)
                
    return pages_text, engine_desc


def extract_pdf_pages_pypdf(pdf_bytes, page_number=None) -> tuple[list[str], str]:
    """Fallback page text extractor using pypdf."""
    pages_text = []
    engine_desc = "pypdf"
    
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    
    if page_number:
        if 1 <= page_number <= total_pages:
            page = reader.pages[page_number - 1]
            text = page.extract_text() or ""
            pages_text.append(text)
        else:
            raise IndexError(f"Page {page_number} out of range (1-{total_pages})")
    else:
        MAX_PAGES = 15
        if total_pages <= MAX_PAGES:
            pages_to_read = list(range(total_pages))
        else:
            first_pages = list(range(min(7, total_pages)))
            last_pages = list(range(max(0, total_pages - 4), total_pages))
            pages_to_read = sorted(set(first_pages + last_pages))
            print(f"📄 PDF has {total_pages} pages. Reading pages {[p+1 for p in pages_to_read]} (pypdf smart selection)")
            engine_desc = f"pypdf (smart selection: {len(pages_to_read)}/{total_pages} pages)"
            
        for idx in pages_to_read:
            page = reader.pages[idx]
            text = page.extract_text() or ""
            pages_text.append(f"\n--- Page {idx+1} ---\n" + text)
            
    return pages_text, engine_desc


def read_pdf(url, search_term=None, page_number=None, output_path=None, project_dir=None):
    """
    Read a PDF from URL with optional search and page selection.
    """
    if not project_dir:
        if output_path:
            project_dir = str(Path(output_path).parent.parent)
        else:
            project_dir = "."

    # Rate limiting delay
    delay = uniform(1, 2)
    print(f"Rate limiting: Waiting {delay:.2f} seconds before accessing {url}")
    time.sleep(delay)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        pdf_bytes = response.content

        # Save local copy if output_path is provided
        if output_path:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file then rename (atomic)
            temp_path = out_path.with_suffix(".tmp")
            with open(temp_path, 'wb') as f:
                f.write(pdf_bytes)
            if temp_path.stat().st_size == 0:
                raise IOError("Downloaded PDF file is 0 bytes")
            temp_path.replace(out_path)
            
            print(f"💾 Raw PDF downloaded and saved to: {out_path}")
            log_action_to_audit(project_dir, "Downloaded PDF file", url=url, local_path=str(out_path), status="ok")

        # Select parser engine
        engine = "none"
        pages_text = []
        
        if has_pdfplumber:
            try:
                pages_text, engine = extract_pdf_pages_pdfplumber(pdf_bytes, page_number)
            except Exception as e:
                print(f"⚠️ pdfplumber failed: {e}. Falling back to pypdf...")
                if has_pypdf:
                    pages_text, engine = extract_pdf_pages_pypdf(pdf_bytes, page_number)
                else:
                    raise e
        elif has_pypdf:
            pages_text, engine = extract_pdf_pages_pypdf(pdf_bytes, page_number)
        else:
            raise ImportError("Neither pdfplumber nor pypdf is installed to parse PDF content.")

        total_content = "\n".join(pages_text)

        # 1. If specific page requested
        if page_number:
            print(f"\n--- Page {page_number} extracted via {engine} ---")
            print(total_content)
            log_action_to_audit(
                project_dir,
                f"Read PDF page {page_number}",
                url=url,
                local_path=output_path or "",
                status="ok",
                details=f"Engine: {engine}"
            )
            return
            
        # 2. If search term provided
        if search_term:
            print(f"🔍 Searching for: '{search_term}'")
            search_lower = search_term.lower()
            matches = []
            
            # Reparse page-by-page to know exactly which page the match occurred on
            # We can map each page_text element
            for idx, p_text in enumerate(pages_text):
                # Clean header lines
                p_text_clean = re.sub(r"^--- Page \d+ ---\n", "", p_text)
                if search_lower in p_text_clean.lower():
                    lines = p_text_clean.split('\n')
                    for line_idx, line in enumerate(lines):
                        if search_lower in line.lower():
                            context_start = max(0, line_idx - 2)
                            context_end = min(len(lines), line_idx + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            
                            # Deduce page index
                            # Note: if smart selection is on, page labels are explicitly written
                            page_label_match = re.search(r"^--- Page (\d+) ---", p_text)
                            page_lbl = int(page_label_match.group(1)) if page_label_match else (idx + 1)
                            
                            matches.append({
                                'page': page_lbl,
                                'line': line.strip(),
                                'context': context
                            })

            if matches:
                print(f"\n✅ Found {len(matches)} matches for '{search_term}':\n")
                for match_idx, match in enumerate(matches[:10]):
                    print(f"{'='*60}")
                    print(f"📍 Match {match_idx+1} - Page {match['page']}")
                    print(f"{'='*60}")
                    print(f"Line: {match['line']}")
                    print(f"\nContext:")
                    print(match['context'])
                    print()
                
                if len(matches) > 10:
                    print(f"... and {len(matches) - 10} more matches")
                
                best_page = matches[0]['page']
                print(f"\n📸 Suggested page for screenshot: Page {best_page}")
                print(f"   Use: python pdf_reader.py --url \"{url}\" --page {best_page}")
                
                log_action_to_audit(
                    project_dir,
                    f"Searched PDF for '{search_term}' (Found {len(matches)} matches)",
                    url=url,
                    local_path=output_path or "",
                    status="ok",
                    details=f"Engine: {engine}"
                )
            else:
                print(f"❌ No matches found for '{search_term}'")
                log_action_to_audit(
                    project_dir,
                    f"Searched PDF for '{search_term}' (0 matches)",
                    url=url,
                    local_path=output_path or "",
                    status="skipped"
                )
            return

        # 3. Default: Print truncated full text
        MAX_CHARS = 20000
        if len(total_content) > MAX_CHARS:
            intro = total_content[:8000]
            outro = total_content[-8000:]
            truncated = len(total_content) - MAX_CHARS
            print(f"--- PDF CONTENT START ---")
            print(intro)
            print(f"\n\n[... {truncated:,} characters truncated from middle ...]\n\n")
            print(f"--- PDF CONTENT END ---")
            print(outro)
        else:
            print(total_content)

        log_action_to_audit(
            project_dir,
            f"Parsed PDF content ({len(total_content)} chars)",
            url=url,
            local_path=output_path or "",
            status="ok",
            details=f"Engine: {engine}"
        )

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        log_action_to_audit(project_dir, f"Error downloading PDF: {e}", url=url, status="failed")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        log_action_to_audit(project_dir, f"Error reading PDF: {e}", url=url, status="failed", details=str(e))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Read and search PDF documents from URLs with layout-aware pdfplumber.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read PDF with smart page selection
  python pdf_reader.py --url "https://example.com/report.pdf"
  
  # Search for specific term
  python pdf_reader.py --url "https://example.com/report.pdf" --search "Prime Minister"
  
  # Read specific page
  python pdf_reader.py --url "https://example.com/report.pdf" --page 5
  
  # Save the raw PDF locally
  python pdf_reader.py --url "https://example.com/report.pdf" --output "./Projects/my_project/assets/documents/report.pdf"
        """
    )
    
    parser.add_argument("--url", required=True, help="URL of the PDF document")
    parser.add_argument("--search", "-s", help="Search for specific term and show context")
    parser.add_argument("--page", "-p", type=int, help="Read specific page number (1-indexed)")
    parser.add_argument("--output", "-o", help="Path to save the raw downloaded PDF file")
    parser.add_argument("--project-dir", help="Project directory path for logging")
    
    args = parser.parse_args()
    read_pdf(
        args.url, 
        search_term=args.search, 
        page_number=args.page, 
        output_path=args.output,
        project_dir=args.project_dir
    )


if __name__ == "__main__":
    main()
