import sys
import os
import shutil
import re

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from services.transcriber_service import to_rtf, resort_from_cache

def test_gap_reporting():
    test_dir = "scratch/gap_test_project"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create mock RTF files with a GAP (missing page 1)
    pages = {
        0: "This is page 0.",
        2: "This is page 2."
    }
    
    for i, text in pages.items():
        rtf_path = os.path.join(test_dir, f"page_{i}.rtf")
        with open(rtf_path, "w", encoding="utf-8") as f:
            f.write(to_rtf(text))
            
    # Mocking Archive contents to help expected_range detection
    archive_dir = os.path.join(test_dir, "Archive")
    os.makedirs(archive_dir)
    # We create a dummy image to make the system expect 3 pages
    for i in range(3):
        with open(os.path.join(archive_dir, f"page_{i}.jpg"), "w") as f:
            f.write("dummy")

    # 2. Run stitching
    print("Running resort_from_cache with gaps...")
    resort_from_cache(test_dir)
    
    # 3. Verify output
    manuscript_path = os.path.join(test_dir, "Unified_Manuscript.md")
    if not os.path.exists(manuscript_path):
        print("FAIL: Manuscript not found.")
        return
        
    with open(manuscript_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print("\nManuscript Content:")
    print("-" * 20)
    print(content)
    print("-" * 20)
    
    # Verify Gap Summary Header
    assert "> [DIRECTORIAL ALERT]: The following pages are missing: 1." in content
    # Verify Placeholder Injection
    assert "[DIRECTORIAL ALERT: PAGE 1 MISSING]" in content
    # Verify Markers are RETAINED when gaps exist
    assert "--- [PAGE START: page_0.rtf] ---" in content
    assert "--- [PAGE START: page_2.rtf] ---" in content
    
    print("\nSUCCESS: Gap reporting verified.")

if __name__ == "__main__":
    test_gap_reporting()
