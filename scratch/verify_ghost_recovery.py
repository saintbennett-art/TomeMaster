import os
import sys
import shutil
# Add current directory to path
sys.path.append(os.getcwd())

from backend.services.transcriber_service import ingest_project_baseline, TRANSCRIPTION_STATE

folder = os.path.join(os.getcwd(), "TestManuscript")
print(f"Testing GHOST RECOVERY for: {folder}")

# 1. SETUP: Clean root of images (put them in Archive), delete ledger
archive_dir = os.path.join(folder, "Archive")
if not os.path.exists(archive_dir): os.makedirs(archive_dir)

for f in os.listdir(folder):
    if f.lower().endswith(".jpg") and f.lower() != "cover.jpg":
        shutil.move(os.path.join(folder, f), os.path.join(archive_dir, f))

ledger_path = os.path.join(folder, "project_ledger.json")
if os.path.exists(ledger_path): os.remove(ledger_path)

# 2. RUN: Trigger ingestion
ingest_project_baseline(folder)

print(f"Final Status: {TRANSCRIPTION_STATE.get('status')}")
print(f"Total Images Inferred: {TRANSCRIPTION_STATE.get('total_images')}")
print(f"Error Message: {TRANSCRIPTION_STATE.get('error_message')}")

# Wait a second for the thread to start and check the ledger
import time
time.sleep(2)
if os.path.exists(ledger_path):
    with open(ledger_path, "r") as f:
        print(f"Ledger Recovered: {f.read()[:100]}...")
