import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from services.transcriber_service import check_and_strip_manuscript_markers

def test_cleansing_logic():
    # Case 1: Perfect Sequence (Should Strip)
    text_1 = """--- [PAGE START: page_0.rtf] ---
This is page 0.
--- [PAGE START: page_1.rtf] ---
This is page 1.
--- [PAGE START: page_2.rtf] ---
This is page 2."""
    
    cleaned_1 = check_and_strip_manuscript_markers(text_1)
    print("Case 1 (Sequential):")
    print(cleaned_1)
    assert "--- [PAGE START" not in cleaned_1
    assert "This is page 0." in cleaned_1
    
    # Case 2: Gap in Sequence (Should Retain)
    text_2 = """--- [PAGE START: page_0.rtf] ---
This is page 0.
--- [PAGE START: page_2.rtf] ---
This is page 2."""
    
    cleaned_2 = check_and_strip_manuscript_markers(text_2)
    print("\nCase 2 (Gap):")
    print(cleaned_2)
    assert "--- [PAGE START: page_0.rtf] ---" in cleaned_2
    assert "--- [PAGE START: page_2.rtf] ---" in cleaned_2
    
    # Case 3: Out of Order (Should Retain)
    text_3 = """--- [PAGE START: page_1.rtf] ---
This is page 1.
--- [PAGE START: page_0.rtf] ---
This is page 0."""
    
    cleaned_3 = check_and_strip_manuscript_markers(text_3)
    print("\nCase 3 (Out of Order):")
    print(cleaned_3)
    assert "--- [PAGE START: page_1.rtf] ---" in cleaned_3
    
    print("\nSUCCESS: Cleanup logic verified.")

if __name__ == "__main__":
    test_cleansing_logic()
