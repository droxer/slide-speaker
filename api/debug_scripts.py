#!/usr/bin/env python3
"""
Debug script to check what scripts are stored in the state
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from slidespeaker.core.state_manager import state_manager

async def debug_script_data(file_id: str):
    """Debug script data in state for a given file ID"""
    
    state = await state_manager.get_state(file_id)
    if not state:
        print(f"No state found for file ID: {file_id}")
        return
    
    print(f"State for file ID: {file_id}")
    print(f"Audio language: {state.get('audio_language', 'unknown')}")
    print(f"Subtitle language: {state.get('subtitle_language', 'unknown')}")
    
    # Check review_scripts data
    if "steps" in state and "review_scripts" in state["steps"]:
        review_scripts = state["steps"]["review_scripts"]
        print(f"\nReview scripts status: {review_scripts['status']}")
        if review_scripts["data"]:
            print("Review scripts data:")
            for i, script_data in enumerate(review_scripts["data"][:3]):  # First 3 scripts
                print(f"  Slide {i + 1}: {script_data.get('script', '')[:100]}...")
        else:
            print("No review scripts data")
    
    # Check review_subtitle_scripts data
    if "steps" in state and "review_subtitle_scripts" in state["steps"]:
        review_subtitle_scripts = state["steps"]["review_subtitle_scripts"]
        print(f"\nReview subtitle scripts status: {review_subtitle_scripts['status']}")
        if review_subtitle_scripts["data"]:
            print("Review subtitle scripts data:")
            for i, script_data in enumerate(review_subtitle_scripts["data"][:3]):  # First 3 scripts
                print(f"  Slide {i + 1}: {script_data.get('script', '')[:100]}...")
        else:
            print("No review subtitle scripts data")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_scripts.py <file_id>")
        sys.exit(1)
    
    file_id = sys.argv[1]
    asyncio.run(debug_script_data(file_id))