
import sys
import os

# Add backend to path
sys.path.append(r'c:\Users\saint\.gemini\antigravity\playground\dark-schrodinger')
from backend.services.transcriber_service import TRANSCRIPTION_STATE

print("--- Current Transcription State ---")
for key, value in TRANSCRIPTION_STATE.items():
    if key == "text" and value:
        print(f"{key}: [TEXT PRESENT, LENGTH {len(value)}]")
        print(f"Preview: {value[:200]}...")
    else:
        print(f"{key}: {value}")
