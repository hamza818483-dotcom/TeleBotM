#!/usr/bin/env python3
"""
Helper script to generate Pyrogram session string for GitHub Actions/CI/CD.

This script will:
1. Prompt for your Telegram API credentials
2. Authenticate with your phone number (one-time)
3. Generate a session string that can be used in .env file

Usage:
    python generate_session_string.py

After running, add the output to your .env file as TELEGRAM_SESSION_STRING
"""

import os
import sys
from pyrogram import Client

def main():
    print("=" * 60)
    print("Pyrogram Session String Generator")
    print("=" * 60)
    print()
    print("This script will generate a session string for Pyrogram.")
    print("You'll need your API credentials from https://my.telegram.org/apps")
    print()
    
    # Get API credentials
    api_id = input("Enter your API ID (integer): ").strip()
    if not api_id.isdigit():
        print("Error: API ID must be a valid integer")
        sys.exit(1)
    api_id = int(api_id)
    
    api_hash = input("Enter your API Hash: ").strip()
    if not api_hash:
        print("Error: API Hash cannot be empty")
        sys.exit(1)
    
    print()
    print("Creating temporary client...")
    print("You will be prompted for your phone number and authentication code.")
    print()
    
    # Create temporary client
    app = Client(
        "temp_session_generator",
        api_id=api_id,
        api_hash=api_hash
    )
    
    try:
        # Start and authenticate
        app.start()
        
        # Export session string
        session_string = app.export_session_string()
        
        print()
        print("=" * 60)
        print("SUCCESS! Your session string has been generated.")
        print("=" * 60)
        print()
        print("Add this to your .env file:")
        print()
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print()
        print("=" * 60)
        print("IMPORTANT SECURITY NOTES:")
        print("=" * 60)
        print("1. This session string is equivalent to your account password")
        print("2. Keep it secure and never share it publicly")
        print("3. Never commit it to git repositories")
        print("4. For GitHub Actions, add it as a Secret, not in code")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        app.stop()
        # Clean up temporary session file
        try:
            if os.path.exists("temp_session_generator.session"):
                os.remove("temp_session_generator.session")
            if os.path.exists("temp_session_generator.session-journal"):
                os.remove("temp_session_generator.session-journal")
        except:
            pass

if __name__ == "__main__":
    main()

