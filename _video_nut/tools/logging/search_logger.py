#!/usr/bin/env python3
"""
Search Logger for VideoNut

Logs all search queries made by agents, with special focus on regional language searches.
This helps track:
1. What searches are being performed
2. Whether regional languages (Hindi, Telugu, Tamil, Marathi) are being used
3. Success/failure rates of searches
4. Search patterns over time

Usage:
    # Log a search
    python search_logger.py --log --query "electoral bonds scam" --language "en" --agent "investigator"
    
    # Log with regional language
    python search_logger.py --log --query "इलेक्टोरल बॉन्ड घोटाला" --language "hi" --agent "investigator"
    
    # View search history
    python search_logger.py --view --project "electoral_bonds"
    
    # Get regional language statistics
    python search_logger.py --stats
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path


# Regional language codes and names
REGIONAL_LANGUAGES = {
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'mr': 'Marathi',
    'bn': 'Bengali',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'or': 'Odia'
}

# Default log file location
DEFAULT_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "search_history.jsonl"


def ensure_log_dir():
    """Create log directory if it doesn't exist."""
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_search(query, language='en', agent='unknown', project=None, 
               success=True, results_count=0, notes=None):
    """
    Log a search query to the search history.
    
    Args:
        query: The search query string
        language: Language code (en, hi, te, etc.)
        agent: Which agent performed the search
        project: Project name/folder
        success: Whether the search returned results
        results_count: Number of results found
        notes: Optional notes
    
    Returns:
        Dict with the logged entry
    """
    ensure_log_dir()
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'query': query,
        'language': language,
        'language_name': REGIONAL_LANGUAGES.get(language, 'English' if language == 'en' else language),
        'is_regional': language in REGIONAL_LANGUAGES,
        'agent': agent,
        'project': project,
        'success': success,
        'results_count': results_count,
        'notes': notes
    }
    
    # Append to log file (JSONL format - one JSON per line)
    with open(DEFAULT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    # Also log to console
    lang_indicator = f"🇮🇳 {entry['language_name']}" if entry['is_regional'] else f"🌐 {entry['language_name']}"
    status = "✅" if success else "❌"
    
    print(f"{status} [{agent}] {lang_indicator}: \"{query}\" ({results_count} results)")
    
    return entry


def load_search_history(project=None, agent=None, language=None, limit=100):
    """
    Load search history with optional filters.
    
    Args:
        project: Filter by project name
        agent: Filter by agent name
        language: Filter by language code
        limit: Maximum entries to return
    
    Returns:
        List of search entries
    """
    if not DEFAULT_LOG_FILE.exists():
        return []
    
    entries = []
    with open(DEFAULT_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Apply filters
                if project and entry.get('project') != project:
                    continue
                if agent and entry.get('agent') != agent:
                    continue
                if language and entry.get('language') != language:
                    continue
                
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    
    # Return most recent entries
    return entries[-limit:]


def get_statistics():
    """
    Calculate search statistics.
    
    Returns:
        Dict with statistics
    """
    entries = load_search_history(limit=10000)
    
    if not entries:
        return {'total': 0, 'message': 'No search history found'}
    
    stats = {
        'total_searches': len(entries),
        'by_language': {},
        'by_agent': {},
        'regional_percentage': 0,
        'success_rate': 0,
        'average_results': 0
    }
    
    regional_count = 0
    success_count = 0
    total_results = 0
    
    for entry in entries:
        # By language
        lang = entry.get('language', 'unknown')
        stats['by_language'][lang] = stats['by_language'].get(lang, 0) + 1
        
        # By agent
        agent = entry.get('agent', 'unknown')
        stats['by_agent'][agent] = stats['by_agent'].get(agent, 0) + 1
        
        # Regional count
        if entry.get('is_regional'):
            regional_count += 1
        
        # Success rate
        if entry.get('success'):
            success_count += 1
        
        # Results count
        total_results += entry.get('results_count', 0)
    
    # Calculate percentages
    stats['regional_percentage'] = round((regional_count / len(entries)) * 100, 1)
    stats['regional_count'] = regional_count
    stats['success_rate'] = round((success_count / len(entries)) * 100, 1)
    stats['average_results'] = round(total_results / len(entries), 1)
    
    return stats


def display_history(entries):
    """Display search history in a readable format."""
    if not entries:
        print("No search history found.")
        return
    
    print(f"\n📋 Search History ({len(entries)} entries)\n")
    print("=" * 80)
    
    for entry in entries:
        timestamp = entry.get('timestamp', 'Unknown')[:19]  # Trim to date+time
        agent = entry.get('agent', 'unknown')
        lang = entry.get('language_name', entry.get('language', '?'))
        query = entry.get('query', '')[:50]  # Truncate long queries
        results = entry.get('results_count', 0)
        status = "✅" if entry.get('success') else "❌"
        regional = "🇮🇳" if entry.get('is_regional') else "  "
        
        print(f"{status} {regional} [{timestamp}] {agent:12} | {lang:10} | {query}")
    
    print("=" * 80)


def display_statistics(stats):
    """Display statistics in a readable format."""
    print("\n📊 Search Statistics\n")
    print("=" * 60)
    
    print(f"Total Searches: {stats.get('total_searches', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0)}%")
    print(f"Average Results: {stats.get('average_results', 0)}")
    print(f"\n🇮🇳 Regional Language Usage: {stats.get('regional_percentage', 0)}%")
    print(f"   ({stats.get('regional_count', 0)} out of {stats.get('total_searches', 0)} searches)")
    
    print("\n📈 By Language:")
    for lang, count in sorted(stats.get('by_language', {}).items(), key=lambda x: -x[1]):
        lang_name = REGIONAL_LANGUAGES.get(lang, 'English' if lang == 'en' else lang)
        bar = "█" * min(count, 30)
        regional_marker = "🇮🇳" if lang in REGIONAL_LANGUAGES else "  "
        print(f"   {regional_marker} {lang_name:15} {bar} ({count})")
    
    print("\n🤖 By Agent:")
    for agent, count in sorted(stats.get('by_agent', {}).items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 30)
        print(f"   {agent:15} {bar} ({count})")
    
    print("=" * 60)
    
    # Recommendations
    regional_pct = stats.get('regional_percentage', 0)
    if regional_pct < 20:
        print("\n💡 Recommendation: Try more regional language searches!")
        print("   Hindi: Add 'हिंदी में' or translate key terms")
        print("   Telugu: Add 'తెలుగులో' for Telugu sources")


def main():
    parser = argparse.ArgumentParser(
        description="Log and analyze search queries for VideoNut agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Log a search
  python search_logger.py --log --query "electoral bonds" --language "en" --agent "investigator"
  
  # Log a Hindi search
  python search_logger.py --log --query "इलेक्टोरल बॉन्ड" --language "hi" --agent "investigator"
  
  # View search history
  python search_logger.py --view
  
  # View history for specific project
  python search_logger.py --view --project "electoral_bonds"
  
  # Get statistics
  python search_logger.py --stats

Regional Language Codes:
  hi = Hindi       te = Telugu      ta = Tamil
  mr = Marathi     bn = Bengali     gu = Gujarati
  kn = Kannada     ml = Malayalam   pa = Punjabi
        """
    )
    
    # Actions
    parser.add_argument("--log", "-l", action="store_true", help="Log a new search")
    parser.add_argument("--view", "-v", action="store_true", help="View search history")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")
    
    # Log parameters
    parser.add_argument("--query", "-q", help="Search query to log")
    parser.add_argument("--language", default="en", help="Language code (en, hi, te, etc.)")
    parser.add_argument("--agent", default="unknown", help="Agent name")
    parser.add_argument("--project", "-p", help="Project name")
    parser.add_argument("--success", type=bool, default=True, help="Whether search succeeded")
    parser.add_argument("--results", type=int, default=0, help="Number of results")
    parser.add_argument("--notes", help="Optional notes")
    
    # View parameters
    parser.add_argument("--limit", type=int, default=50, help="Max entries to show")
    
    args = parser.parse_args()
    
    if not (args.log or args.view or args.stats):
        parser.print_help()
        print("\nError: Use --log, --view, or --stats")
        sys.exit(1)
    
    if args.log:
        if not args.query:
            print("Error: --query is required for logging")
            sys.exit(1)
        
        log_search(
            query=args.query,
            language=args.language,
            agent=args.agent,
            project=args.project,
            success=args.success,
            results_count=args.results,
            notes=args.notes
        )
        print("\n✅ Search logged successfully")
    
    elif args.view:
        entries = load_search_history(
            project=args.project,
            agent=args.agent,
            language=args.language,
            limit=args.limit
        )
        display_history(entries)
    
    elif args.stats:
        stats = get_statistics()
        display_statistics(stats)


if __name__ == "__main__":
    main()
