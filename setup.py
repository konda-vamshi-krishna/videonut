#!/usr/bin/env python3
"""
VideoNut Setup Script
Installs dependencies and sets up the environment for VideoNut agents
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def install_python_packages():
    """Install required Python packages"""
    print("📦 Installing Python packages...")
    
    requirements = [
        "yt-dlp",
        "playwright", 
        "requests",
        "beautifulsoup4",
        "pypdf",
        "youtube-transcript-api"
    ]
    
    for package in requirements:
        try:
            print(f"  Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✅ {package} installed successfully")
            else:
                print(f"    ❌ Failed to install {package}")
                print(f"    Error: {result.stderr}")
        except Exception as e:
            print(f"    ❌ Error installing {package}: {str(e)}")

def setup_playwright():
    """Setup Playwright browsers"""
    print("🌐 Setting up Playwright browsers...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "--with-deps"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Playwright browsers installed successfully")
        else:
            print(f"  ❌ Playwright setup failed: {result.stderr}")
    except Exception as e:
        print(f"  ❌ Error setting up Playwright: {str(e)}")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating project directories...")
    
    dirs_to_create = [
        "Projects",
        "tools/bin",  # For ffmpeg and other binaries
        "output"
    ]
    
    for dir_path in dirs_to_create:
        full_path = os.path.join(os.getcwd(), dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"  ✅ Created directory: {dir_path}")

def check_ffmpeg():
    """Check if ffmpeg is available"""
    print("🎬 Checking for FFmpeg...")
    
    result = subprocess.run(["ffmpeg", "-version"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("  ✅ FFmpeg is available")
        return True
    else:
        print("  ⚠️ FFmpeg not found in system PATH")
        print("    You may need to install FFmpeg manually or place it in tools/bin/")
        return False

def main():
    print("🚀 VideoNut Setup Script")
    print("=" * 50)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    # Create directories first
    create_directories()
    
    # Install Python packages
    install_python_packages()
    
    # Setup Playwright
    setup_playwright()
    
    # Check FFmpeg
    check_ffmpeg()
    
    print()
    print("📋 Setup Summary:")
    print("  1. Python packages installed")
    print("  2. Playwright browsers configured") 
    print("  3. Project directories created")
    print("  4. FFmpeg checked")
    print()
    print("✅ Setup completed! Run 'python tools/check_env.py' to verify installation.")
    print("💡 To start a new project, use the investigator agent: /investigator")

if __name__ == "__main__":
    main()