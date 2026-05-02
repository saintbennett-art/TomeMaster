import json

# [DUPLICATED LOGIC FROM AI_SERVICE.PY FOR CLEAN-ROOM PROOFING]
def _strip_front_matter(text: str, chapters: list[dict] = None) -> tuple[str, list[dict]]:
    """Directorial Override: Forensicly anchors to the first high-volume narrative segment."""
    if not chapters or not text:
        return text, chapters
    
    # [ABSOLUTE STRUCTURAL PURGE]: Identifying the narrative anchor
    start_idx = 0
    for i, chapter in enumerate(chapters):
        content = (chapter.get("content", "") or "").strip()
        title = (chapter.get("title", "") or "").lower()
        
        # Meta-Signatures (purging intro blocks)
        is_meta = any(sig in title for sig in ["title page", "table of contents", "toc", "prelude", "forward", "dedication", "copyright"])
        if is_meta: continue
        
        # Narrative Anchor: Substantial text or Speech signatures
        if len(content) > 300 or content.startswith('"') or content.startswith("'"):
            start_idx = i
            break
            
    cleaned_chapters = chapters[start_idx:]
    cleaned_text = "\n\n".join([c.get("content", "").strip() for c in cleaned_chapters if c.get("content", "").strip()])
    
    return cleaned_text, cleaned_chapters

def prove_payload_purity():
    # SIMULATING YOUR EXACT PAYLOAD STRUCTURE
    chapters = [
        {
            "title": "THIS CLOSE",
            "content": "THIS CLOSE\nby R. E. Lamb"
        },
        {
            "title": "Prelude / Forward",
            "content": "\"For He shall give His Angels charge over thee, to keep thee in all thy ways. They shall bear thee up in their hands, lest thy dash thy foot against a stone...\" Psalms Chapter 91, verses 11, 12 KJV"
        },
        {
            "title": "Table of Contents",
            "content": "Table of Contents\n\nTHIS CLOSE 1\nby R. E. Lamb 2\nPrelude / Forward 3\nTable of Contents 4\nThe Shattered Christmas Dream 5\n..."
        },
        {
            "title": "The Shattered Christmas Dream",
            "content": "\"It's snowing, it's snowing!\" I shouted to my big sister Shelley, as we scrambled to peek out the living room window..."
        }
    ]
    
    raw_text = "\n\n".join([c["content"] for c in chapters])
    
    print("--- [INITIATING CLEAN-ROOM PAYLOAD PROOF] ---")
    print(f"ORIGINAL TOTAL CHAPTERS: {len(chapters)}")
    
    cleaned_text, cleaned_chapters = _strip_front_matter(raw_text, chapters)
    
    print(f"PURGED CHAPTERS: {len(chapters) - len(cleaned_chapters)}")
    print(f"REMAINING CORE CHAPTERS: {len(cleaned_chapters)}")
    print("-" * 30)
    print("REMAINING TEXT PREVIEW:")
    print(cleaned_text[:200])
    print("-" * 30)
    
    # Forensic Success Condition: First chapter should be the narrative story
    # MUST START WITH: "It's snowing, it's snowing!"
    if cleaned_text.strip().startswith('"It\'s snowing'):
        print("[SUCCESS]: Front matter forensicly purged. Narrative anchor established.")
    else:
        print("[FAILURE]: Contamination persists or payload evacuated.")

if __name__ == "__main__":
    prove_payload_purity()
