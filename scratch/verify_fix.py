import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from backend.services.transcriber_service import ingest_project_baseline, TRANSCRIPTION_STATE

folder = os.path.join(os.getcwd(), "TestManuscript")
print(f"Testing ingestion for: {folder}")

# Trigger ingestion
success = ingest_project_baseline(folder)

print(f"Ingestion Success: {success}")
print(f"Final Status: {TRANSCRIPTION_STATE.get('status')}")
print(f"Error Message: {TRANSCRIPTION_STATE.get('error_message')}")
