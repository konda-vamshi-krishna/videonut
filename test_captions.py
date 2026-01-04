#!/usr/bin/env python3
"""
Test script for YouTube caption reader
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.downloaders.caption_reader import get_youtube_captions, extract_video_id

def test_caption_reader():
    # Test with a known YouTube video that has captions
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # First YouTube video
    
    print(f"Testing caption reader with URL: {test_url}")
    
    try:
        captions = get_youtube_captions(test_url)
        print("Successfully retrieved captions:")
        print("-" * 50)
        print(captions[:500] + "..." if len(captions) > 500 else captions)  # Print first 500 chars
        print("-" * 50)
        print(f"Total characters: {len(captions)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_caption_reader()