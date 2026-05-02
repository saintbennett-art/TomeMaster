import sys
import os

# Align with backend logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services import ai_service

def test_payload_strip():
    # Representative sample of the "Trash" identified by Mr. Bennett
    test_chapters = [
        {"title": "Title Page (Manuscript)", "content": "Book Title\nAuthor Name"},
        {"title": " Prelude & Intro ", "content": "Once upon a time... (the junk)"},
        {"title": "Table of Contents", "content": "1. Chapter One..."},
        {"title": "Chapter One", "content": "Actual story content starts here."}
    ]
    test_text = "\n\n".join([c["content"] for c in test_chapters])

    print("--- [BEFORE STRIP] ---")
    print(f"Chapter Count: {len(test_chapters)}")
    for c in test_chapters:
        print(f"Title: '{c['title']}'")

    cleaned_text, cleaned_chapters = ai_service._strip_front_matter(test_text, test_chapters)

    print("\n--- [AFTER STRIP] ---")
    print(f"Chapter Count: {len(cleaned_chapters)}")
    for c in cleaned_chapters:
        print(f"Title: '{c['title']}'")
        
    if len(cleaned_chapters) == 1 and cleaned_chapters[0]["title"] == "Chapter One":
        print("\n[SUCCESS]: Fuzzy match identified and neutralized all variations of front-matter.")
    else:
        print("\n[FAILURE]: Non-narrative content still detected in the payload.")

if __name__ == "__main__":
    test_payload_strip()
