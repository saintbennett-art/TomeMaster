import sys
import os
sys.path.append(os.getcwd())
from services.transcriber_service import TRANSCRIPTION_STATE

print(f"Engine Status: {TRANSCRIPTION_STATE.get('status')}")
print(f"Error Message: {TRANSCRIPTION_STATE.get('error_message')}")
print(f"Active Folder: {TRANSCRIPTION_STATE.get('folder')}")
print(f"Processed: {TRANSCRIPTION_STATE.get('processed_images')} / {TRANSCRIPTION_STATE.get('total_images')}")
