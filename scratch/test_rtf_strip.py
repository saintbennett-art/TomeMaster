import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from services.transcriber_service import to_rtf, strip_rtf

def test_rtf_roundtrip():
    original_text = "This is a **bold** and *italic* test with Unicode: \u00a9 2026."
    print(f"Original: {original_text}")
    
    # 1. Convert to RTF
    rtf_content = to_rtf(original_text)
    print("\nGenerated RTF:")
    print(rtf_content)
    
    # 2. Strip back to text
    stripped_text = strip_rtf(rtf_content)
    print(f"\nStripped: {stripped_text}")
    
    assert stripped_text == original_text
    print("\nSUCCESS: Roundtrip verified.")

if __name__ == "__main__":
    test_rtf_roundtrip()
