import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from services.transcriber_service import check_and_strip_manuscript_markers, to_rtf

def test_on_the_fly_cleansing():
    # Simulate a "corrupt" manuscript with raw RTF blocks
    raw_manuscript = f"""# Manuscript Title
Generated on: ...

--- [PAGE START: page_0.rtf] ---
{to_rtf("This is page 0.")}

--- [PAGE START: page_1.rtf] ---
{to_rtf("This is **page 1**.")}
"""
    
    print("Raw Manuscript (Simulated):")
    print(raw_manuscript)
    
    # Run cleansing
    interpreted = check_and_strip_manuscript_markers(raw_manuscript)
    
    print("\nInterpreted (For Editor):")
    print("-" * 20)
    print(interpreted)
    print("-" * 20)
    
    # Verify markers are GONE (sequential)
    assert "--- [PAGE START" not in interpreted
    # Verify RTF tags are GONE
    assert "{\\rtf1" not in interpreted
    # Verify prose is CLEAN
    assert "This is page 0." in interpreted
    assert "**page 1**" in interpreted
    
    print("\nSUCCESS: On-the-fly interpretation verified.")

if __name__ == "__main__":
    test_on_the_fly_cleansing()
