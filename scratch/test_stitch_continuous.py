import sys
import os
import shutil

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from services.transcriber_service import to_rtf, strip_rtf, resort_from_cache

def test_continuous_stitching():
    test_dir = "scratch/stitch_test_project"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create mock RTF files
    pages = [
        "This is page 0.",
        "This is **page 1** with bold.",
        "And this is *page 2* with italic."
    ]
    
    for i, text in enumerate(pages):
        rtf_path = os.path.join(test_dir, f"page_{i}.rtf")
        with open(rtf_path, "w", encoding="utf-8") as f:
            f.write(to_rtf(text))
            
    # 2. Run stitching
    print("Running resort_from_cache...")
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
    
    # Verify markers are GONE
    assert "--- [PAGE START" not in content
    # Verify content is PRESENT and formatted
    assert "This is page 0." in content
    assert "**page 1**" in content
    assert "*page 2*" in content
    
    print("\nSUCCESS: Continuous stitching verified.")

if __name__ == "__main__":
    test_continuous_stitching()
