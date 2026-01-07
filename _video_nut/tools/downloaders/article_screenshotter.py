#!/usr/bin/env python3
"""
Smart Article Screenshotter for VideoNut
Takes screenshots of news articles with specific quotes highlighted.
Can scroll to specific text, highlight it, and capture focused screenshots.

USAGE:
  # Find and highlight a specific quote
  python article_screenshotter.py --url "https://example.com/article" --quote "exact words to find" --output "quote.png"
  
  # Screenshot without highlighting
  python article_screenshotter.py --url "https://example.com" --quote "text" --no-highlight --output "quote.png"
"""

import sys
import os
import argparse
import time
from random import uniform

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)


def normalize_text(text):
    """Normalize text for comparison - remove extra spaces, newlines."""
    import re
    return re.sub(r'\s+', ' ', text.strip().lower())


def find_quote_in_page(page, quote):
    """
    Find the specific element containing the quote using multiple strategies.
    Returns the element locator or None.
    """
    quote_normalized = normalize_text(quote)
    
    # Strategy 1: Try exact text match with Playwright
    print(f"  Strategy 1: Exact text match...")
    locator = page.get_by_text(quote, exact=False)
    if locator.count() > 0:
        print(f"  ✅ Found with Strategy 1")
        # Convert Locator to ElementHandle for use with page.evaluate()
        try:
            return locator.first.element_handle(timeout=5000)
        except Exception as e:
            print(f"  ⚠️ Could not get element handle: {e}")
            pass
    
    # Strategy 2: Try first few words (in case quote is long)
    words = quote.split()
    if len(words) > 5:
        short_quote = ' '.join(words[:5])
        print(f"  Strategy 2: First 5 words: '{short_quote}'...")
        locator = page.get_by_text(short_quote, exact=False)
        if locator.count() > 0:
            print(f"  ✅ Found with Strategy 2")
            # Convert Locator to ElementHandle for use with page.evaluate()
            try:
                return locator.first.element_handle(timeout=5000)
            except Exception as e:
                print(f"  ⚠️ Could not get element handle: {e}")
                pass
    
    # Strategy 3: JavaScript search across all text nodes
    print(f"  Strategy 3: JavaScript deep search...")
    element_handle = page.evaluate_handle('''(searchText) => {
        const normalizeText = (t) => t.replace(/\\s+/g, ' ').trim().toLowerCase();
        const searchNorm = normalizeText(searchText);
        
        // Search in common content elements
        const selectors = ['p', 'span', 'div', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'li', 'td', 'article'];
        
        for (const selector of selectors) {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                const text = normalizeText(el.innerText || '');
                if (text.includes(searchNorm)) {
                    return el;
                }
            }
        }
        
        // Fallback: search entire body
        const allElements = document.querySelectorAll('*');
        for (const el of allElements) {
            if (el.innerText) {
                const text = normalizeText(el.innerText);
                if (text.includes(searchNorm) && el.innerText.length < 2000) {
                    return el;
                }
            }
        }
        
        return null;
    }''', quote)
    
    if element_handle:
        element = element_handle.as_element()
        if element:
            print(f"  ✅ Found with Strategy 3 (JavaScript)")
            return element
    
    print(f"  ❌ Quote not found with any strategy")
    return None


def take_quote_screenshot(url, output_path, quote=None, highlight=True, width=1280, height=900):
    """
    Take a screenshot of a webpage, focusing on a specific quote.
    
    Args:
        url: URL of the article
        output_path: Where to save the screenshot
        quote: Text to find and focus on (REQUIRED for meaningful screenshot)
        highlight: Whether to highlight the found text
        width: Viewport width
        height: Viewport height
    
    Returns:
        Dict with success status and details
    """
    # Rate limiting
    delay = uniform(1, 2)
    print(f"⏳ Rate limiting: Waiting {delay:.2f} seconds...")
    time.sleep(delay)
    
    result = {
        'success': False,
        'quote_found': False,
        'message': '',
        'output_path': output_path
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': width, 'height': height},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Set headers to appear like real browser
        page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        
        try:
            print(f"🌐 Navigating to {url}...")
            # Use networkidle for better dynamic content handling
            try:
                page.goto(url, timeout=45000, wait_until='networkidle')
            except:
                # Fallback to domcontentloaded if networkidle times out
                print("  ⚠️ networkidle timeout, using domcontentloaded...")
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Wait for dynamic content (increased from 3s to 5s for JS-heavy sites)
            print("  ⏳ Waiting for dynamic content to load...")
            page.wait_for_timeout(5000)
            
            # Try to close cookie popups, modals, and ads
            print("🧹 Closing popups...")
            for selector in [
                'button:has-text("Accept")', 
                'button:has-text("I Agree")', 
                'button:has-text("Got it")',
                'button:has-text("Continue")',
                '.close-button', 
                '[aria-label="Close"]', 
                '.modal-close',
                '.popup-close',
                '#close-btn'
            ]:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click(timeout=1000)
                        page.wait_for_timeout(500)
                except:
                    pass
            
            if quote:
                print(f"🔍 Searching for quote: '{quote[:60]}{'...' if len(quote) > 60 else ''}'")
                
                # Find the quote element
                element = find_quote_in_page(page, quote)
                
                if element:
                    result['quote_found'] = True
                    
                    # Step 1: Try multiple scroll methods (some sites block certain approaches)
                    print("📍 Scrolling quote to center of viewport...")
                    
                    # Method 1: scrollIntoView with block center (most reliable)
                    try:
                        page.evaluate('''(el) => {
                            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });
                        }''', element)
                        page.wait_for_timeout(500)
                        print("  ✅ Scroll method 1 (scrollIntoView) succeeded")
                    except Exception as scroll_err:
                        print(f"  ⚠️ Scroll method 1 failed: {scroll_err}")
                        
                        # Method 2: Manual scrollTo calculation as fallback
                        try:
                            page.evaluate('''(el) => {
                                const rect = el.getBoundingClientRect();
                                const scrollTop = window.pageYOffset + rect.top - (window.innerHeight / 2) + (rect.height / 2);
                                window.scrollTo({ top: Math.max(0, scrollTop), behavior: 'instant' });
                            }''', element)
                            page.wait_for_timeout(500)
                            print("  ✅ Scroll method 2 (scrollTo) succeeded")
                        except Exception as scroll_err2:
                            print(f"  ⚠️ Scroll method 2 also failed: {scroll_err2}")
                    
                    # Step 1.5: Verify element is now visible in viewport
                    is_visible = page.evaluate('''(el) => {
                        const rect = el.getBoundingClientRect();
                        return rect.top >= 0 && rect.bottom <= window.innerHeight;
                    }''', element)
                    
                    if not is_visible:
                        print("  ⚠️ Element not fully visible, trying Playwright scroll...")
                        try:
                            element.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                        except:
                            pass
                    
                    # Step 2: Highlight the element
                    if highlight:
                        print("🎨 Highlighting quote...")
                        page.evaluate('''(el) => {
                            // Save original styles
                            el.setAttribute('data-original-style', el.getAttribute('style') || '');
                            
                            // Apply highlight styles with !important to override site CSS
                            el.style.setProperty('background-color', '#ffff00', 'important');
                            el.style.setProperty('color', '#000000', 'important');
                            el.style.setProperty('padding', '10px', 'important');
                            el.style.setProperty('border-radius', '4px', 'important');
                            el.style.setProperty('border', '4px solid #ff6600', 'important');
                            el.style.setProperty('box-shadow', '0 0 30px rgba(255, 102, 0, 0.8)', 'important');
                            el.style.setProperty('position', 'relative', 'important');
                            el.style.setProperty('z-index', '99999', 'important');
                            el.style.setProperty('display', 'block', 'important');
                        }''', element)
                        print("  ✅ Quote highlighted with yellow background + orange border")
                    
                    # Step 3: Wait for CSS to apply and re-render
                    page.wait_for_timeout(800)
                    
                    # Step 4: Take the screenshot
                    print("📸 Taking screenshot...")
                    page.screenshot(path=output_path)
                    result['success'] = True
                    result['message'] = f"Quote found, centered, and captured: '{quote[:40]}...'"
                    
                else:
                    # Quote NOT found - try fuzzy fallback
                    print("⚠️ Exact quote not found. Trying fuzzy search...")
                    
                    # Try with just the first 3 words
                    words = quote.split()
                    if len(words) >= 3:
                        fuzzy_quote = ' '.join(words[:3])
                        fuzzy_element = find_quote_in_page(page, fuzzy_quote)
                        
                        if fuzzy_element:
                            print(f"  ✅ Found partial match with: '{fuzzy_quote}'")
                            
                            # Scroll and highlight
                            page.evaluate('''(el) => {
                                const rect = el.getBoundingClientRect();
                                const scrollTop = window.pageYOffset + rect.top - (window.innerHeight / 2);
                                window.scrollTo({ top: scrollTop, behavior: 'instant' });
                            }''', fuzzy_element)
                            
                            if highlight:
                                page.evaluate('''(el) => {
                                    el.style.backgroundColor = '#ffff00';
                                    el.style.border = '3px solid #ff6600';
                                    el.style.padding = '8px';
                                }''', fuzzy_element)
                            
                            page.wait_for_timeout(300)
                            page.screenshot(path=output_path)
                            result['success'] = True
                            result['quote_found'] = True
                            result['message'] = f"Partial match found: '{fuzzy_quote}'"
                        else:
                            # Complete failure
                            result['success'] = False
                            result['quote_found'] = False
                            result['message'] = f"ERROR: Quote not found on page: '{quote[:50]}...'"
                            print(f"  ❌ {result['message']}")
                            # Don't take useless screenshot
                    else:
                        result['success'] = False
                        result['message'] = f"ERROR: Quote too short and not found: '{quote}'"
            
            else:
                # No quote provided - just screenshot the article content
                print("📸 No quote specified. Taking article screenshot...")
                
                # Try to find and scroll to main article content
                for selector in ['article', '.article-content', '.story-content', 
                                '.post-content', 'main', '#content', '.entry-content']:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.scroll_into_view_if_needed()
                        break
                
                page.screenshot(path=output_path)
                result['success'] = True
                result['message'] = "Article screenshot captured (no specific quote)"
            
            # Validate file was created
            if result['success'] and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                if size > 0:
                    print(f"✅ Screenshot saved: {output_path} ({size:,} bytes)")
                else:
                    result['success'] = False
                    result['message'] = "Screenshot file is empty"
                    
        except Exception as e:
            result['message'] = f"Error: {str(e)}"
            print(f"❌ Error: {e}")
            
        finally:
            browser.close()
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Take screenshots of news articles with quote highlighting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find and highlight a specific quote (RECOMMENDED)
  python article_screenshotter.py --url "https://timesofindia.com/article" --quote "PM Modi said this is important" --output "quote.png"
  
  # Screenshot without highlighting
  python article_screenshotter.py --url "https://example.com" --quote "important text" --no-highlight --output "quote.png"
  
  # Just capture article (no specific quote)
  python article_screenshotter.py --url "https://example.com" --output "article.png"

NOTE: Always provide --quote for meaningful screenshots. Without it, you just get the page header.
        """
    )
    
    parser.add_argument("--url", "-u", required=True, help="URL of the article")
    parser.add_argument("--output", "-o", required=True, help="Output file path for screenshot")
    parser.add_argument("--quote", "-q", help="Specific quote/text to find, center, and highlight (REQUIRED for useful screenshots)")
    parser.add_argument("--no-highlight", action="store_true", help="Don't highlight the found text")
    parser.add_argument("--width", "-w", type=int, default=1280, help="Viewport width (default: 1280)")
    parser.add_argument("--height", "-H", type=int, default=900, help="Viewport height (default: 900)")
    
    args = parser.parse_args()
    
    # Warn if no quote provided
    if not args.quote:
        print("⚠️ WARNING: No --quote provided. Screenshot will just be the page header.")
        print("   For useful screenshots, always provide the specific text you want to capture.")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    result = take_quote_screenshot(
        url=args.url,
        output_path=args.output,
        quote=args.quote,
        highlight=not args.no_highlight,
        width=args.width,
        height=args.height
    )
    
    if result['success']:
        print(f"\n✅ SUCCESS: {result['message']}")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
