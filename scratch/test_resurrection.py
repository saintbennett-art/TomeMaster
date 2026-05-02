
import sys
import os
import re

# Add backend to path to import the service
sys.path.append(r'c:\Users\saint\.gemini\antigravity\playground\dark-schrodinger')
from backend.services.transcriber_service import check_and_strip_manuscript_markers, strip_rtf

manuscript_path = r'C:\Users\saint\OneDrive\Documents\This Close\Demo\This Close\Unified_Manuscript.md'

if os.path.exists(manuscript_path):
    with open(manuscript_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"Original length: {len(content)}")
    
    # Test strip_rtf on a small chunk
    test_chunk = """{\\rtf1\\ansi\\ansicpg1252\\deff0{\\fonttbl{\\f0 Times New Roman;}}\\f0\\fs24 This\\par
CLOSE\\par
\\par
by B Lamb}"""
    print("--- Test Chunk Stripping ---")
    print(f"Input: {test_chunk[:50]}...")
    print(f"Output: {strip_rtf(test_chunk)}")
    
    print("\n--- Full Manuscript Process ---")
    cleaned = check_and_strip_manuscript_markers(content)
    print(f"Cleaned length: {len(cleaned)}")
    print(f"Preview (first 500 chars):\n{cleaned[:500]}")
    
    if "{\\rtf" in cleaned:
        print("\n[FAILURE]: RTF tags still present in cleaned text!")
    else:
        print("\n[SUCCESS]: No RTF tags found in cleaned text.")
else:
    print(f"Manuscript not found at {manuscript_path}")
