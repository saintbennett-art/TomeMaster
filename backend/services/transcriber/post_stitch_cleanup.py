"""
Post-Stitch Cleanup Pipeline (Phase 2)
=======================================
Runs automatically after resort_from_cache() seals Unified_Manuscript.md.
Produces Clean_Manuscript.md — a deduplicated, artifact-free, chapter-structured
version ready for the editor, spell check, and AI analysis.

Pipeline:
  Phase 2A — Source Deduplication (remove full-dump + OCR duplicates)
  Phase 2B — Artifact Stripping (page markers, system metadata, AI reports, roman numerals)
  Phase 2C — Quote/Apostrophe Restoration (RTF smart-quote corruption fix)
  Phase 2D — Chapter Extraction (detect headings, format as ## H2, generate TOC)
  Phase 2E — Paragraph Normalization (collapse blanks, normalize line endings)
"""

import os
import re
import time
from typing import List, Tuple, Optional, Dict


# ─── ROMAN NUMERAL HANDLING ─────────────────────────────────────────────

ROMAN_PATTERN = re.compile(
    r'^(m{0,4})(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\s',
    re.IGNORECASE
)

def _is_roman_page_number(line: str) -> bool:
    """Check if line starts with a roman numeral page number (from OCR artifacts)."""
    stripped = line.strip()
    if not stripped:
        return False
    m = ROMAN_PATTERN.match(stripped)
    if m and m.group(0).strip():
        # Must be a valid roman numeral (at least one character matched)
        numeral = m.group(0).strip().lower()
        if len(numeral) >= 1 and numeral not in ('a', 'e', 'o', 'u'):
            return True
    return False


# ─── CONTRACTION PATTERNS ───────────────────────────────────────────────

# Maps "word ?X" patterns to "word'X" for common English contractions
CONTRACTION_FIXES = [
    # Negative contractions
    (r"\bcan\s*\?\s*t\b", "can't"),
    (r"\bdon\s*\?\s*t\b", "don't"),
    (r"\bwon\s*\?\s*t\b", "won't"),
    (r"\bdoesn\s*\?\s*t\b", "doesn't"),
    (r"\bdidn\s*\?\s*t\b", "didn't"),
    (r"\bisn\s*\?\s*t\b", "isn't"),
    (r"\bwasn\s*\?\s*t\b", "wasn't"),
    (r"\baren\s*\?\s*t\b", "aren't"),
    (r"\bweren\s*\?\s*t\b", "weren't"),
    (r"\bcouldn\s*\?\s*t\b", "couldn't"),
    (r"\bwouldn\s*\?\s*t\b", "wouldn't"),
    (r"\bshouldn\s*\?\s*t\b", "shouldn't"),
    (r"\bhaven\s*\?\s*t\b", "haven't"),
    (r"\bhasn\s*\?\s*t\b", "hasn't"),
    (r"\bhadn\s*\?\s*t\b", "hadn't"),
    (r"\bmustn\s*\?\s*t\b", "mustn't"),
    (r"\bneedn\s*\?\s*t\b", "needn't"),
    (r"\bain\s*\?\s*t\b", "ain't"),
    # Pronoun contractions
    (r"\bI\s*\?\s*m\b", "I'm"),
    (r"\bI\s*\?\s*d\b", "I'd"),
    (r"\bI\s*\?\s*ll\b", "I'll"),
    (r"\bI\s*\?\s*ve\b", "I've"),
    (r"\bhe\s*\?\s*s\b", "he's"),
    (r"\bshe\s*\?\s*s\b", "she's"),
    (r"\bit\s*\?\s*s\b", "it's"),
    (r"\bthat\s*\?\s*s\b", "that's"),
    (r"\bwhat\s*\?\s*s\b", "what's"),
    (r"\bthere\s*\?\s*s\b", "there's"),
    (r"\bhere\s*\?\s*s\b", "here's"),
    (r"\bwho\s*\?\s*s\b", "who's"),
    (r"\bwhere\s*\?\s*s\b", "where's"),
    (r"\bwhen\s*\?\s*s\b", "when's"),
    (r"\bhow\s*\?\s*s\b", "how's"),
    (r"\blet\s*\?\s*s\b", "let's"),
    (r"\byou\s*\?\s*re\b", "you're"),
    (r"\bwe\s*\?\s*re\b", "we're"),
    (r"\bthey\s*\?\s*re\b", "they're"),
    (r"\byou\s*\?\s*ll\b", "you'll"),
    (r"\bwe\s*\?\s*ll\b", "we'll"),
    (r"\bthey\s*\?\s*ll\b", "they'll"),
    (r"\byou\s*\?\s*ve\b", "you've"),
    (r"\bwe\s*\?\s*ve\b", "we've"),
    (r"\bthey\s*\?\s*ve\b", "they've"),
    (r"\byou\s*\?\s*d\b", "you'd"),
    (r"\bwe\s*\?\s*d\b", "we'd"),
    (r"\bthey\s*\?\s*d\b", "they'd"),
    # Verb contractions
    (r"\bwould\s*\?\s*ve\b", "would've"),
    (r"\bcould\s*\?\s*ve\b", "could've"),
    (r"\bshould\s*\?\s*ve\b", "should've"),
    (r"\bmight\s*\?\s*ve\b", "might've"),
    (r"\bmust\s*\?\s*ve\b", "must've"),
    # Common word contractions
    (r"\bo\s*\?\s*clock\b", "o'clock"),
    (r"\bma\s*\?\s*am\b", "ma'am"),
    (r"\by\s*\?\s*all\b", "y'all"),
    # Possessive 's — generic catch for "word?s" where word ends in a letter
    (r"(\w)\s*\?\s*s\b", r"\1's"),
]

# Pre-compile for speed
_COMPILED_CONTRACTIONS = [(re.compile(p, re.IGNORECASE), r) for p, r in CONTRACTION_FIXES]


# ─── PHASE 2A: SOURCE DEDUPLICATION ─────────────────────────────────────

def _parse_pages(raw_text: str) -> List[Tuple[int, str]]:
    """Extract (page_number, content) tuples from raw stitched manuscript."""
    pattern = r'--- \[PAGE START: page_(\d+)\.rtf\] ---\n(.*?)(?=\n--- \[PAGE START:|\n--- \[MISSING PAGE:|$)'
    matches = re.finditer(pattern, raw_text, re.DOTALL)
    pages = []
    for m in matches:
        num = int(m.group(1))
        content = m.group(2).strip()
        pages.append((num, content))
    return pages


def _content_fingerprint(text: str) -> str:
    """Normalize text for comparison — lowercase, strip whitespace/punctuation."""
    cleaned = re.sub(r'[^a-z0-9]', '', text.lower())
    return cleaned[:500]  # First 500 chars is enough for dedup


def _is_ai_report(content: str) -> bool:
    """Detect if a page is an AI-generated report rather than manuscript prose."""
    indicators = [
        'AI Boardroom', 'Boardroom Report', 'SYSTEM STATUS',
        'DIRECTORIAL', 'Specialist Convention', 'Analysis Report',
        'Emotional Arc', 'Structural Analysis', 'Pacing Report'
    ]
    score = sum(1 for ind in indicators if ind.lower() in content.lower())
    return score >= 2


def _is_toc_stub(content: str) -> bool:
    """Detect if a page is just a TOC stub or empty placeholder."""
    stripped = content.strip()
    if len(stripped) < 100:
        return True
    # Mostly numbers and short lines
    lines = [l.strip() for l in stripped.split('\n') if l.strip()]
    if len(lines) > 0:
        short_lines = sum(1 for l in lines if len(l) < 30)
        if short_lines / len(lines) > 0.8:
            return True
    return False


def _detect_full_dump_page(pages: List[Tuple[int, str]]) -> Optional[int]:
    """Find the 'full book dump' page — one page that contains most of the book's content."""
    if len(pages) < 5:
        return None
    sizes = [(num, len(content)) for num, content in pages]
    sizes.sort(key=lambda x: x[1], reverse=True)
    # If the largest page is > 10x the median, it's a full dump
    if len(sizes) > 10:
        median_size = sizes[len(sizes) // 2][1]
        if median_size > 0 and sizes[0][1] > median_size * 10:
            return sizes[0][0]
    return None


def _detect_ocr_pages(pages: List[Tuple[int, str]]) -> List[int]:
    """Detect OCR-scanned pages by checking for roman numeral page numbers at line start."""
    ocr_pages = []
    for num, content in pages:
        lines = content.strip().split('\n')
        if lines and _is_roman_page_number(lines[0]):
            ocr_pages.append(num)
    return ocr_pages


def _content_overlap(text_a: str, text_b: str, sample_size: int = 5) -> float:
    """Check what fraction of sentences from text_a appear in text_b."""
    # Extract sentences from A
    sentences_a = re.split(r'[.!?]+', text_a)
    sentences_a = [s.strip() for s in sentences_a if len(s.strip()) > 40]
    if not sentences_a:
        return 0.0
    
    # Sample for speed
    step = max(1, len(sentences_a) // sample_size)
    samples = sentences_a[::step][:sample_size]
    
    b_normalized = re.sub(r'\s+', ' ', text_b.lower())
    hits = 0
    for sent in samples:
        normalized = re.sub(r'\s+', ' ', sent.lower().strip())
        if len(normalized) > 20 and normalized[:50] in b_normalized:
            hits += 1
    
    return hits / len(samples) if samples else 0.0


def phase_2a_dedup(pages: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Remove duplicate content sources: AI reports, full dumps, TOC stubs, OCR duplicates."""
    if not pages:
        return pages
    
    removed_count = 0
    kept = []
    
    # Step 1: Remove AI reports and TOC stubs
    clean_pages = []
    for num, content in pages:
        if _is_ai_report(content):
            print(f"[CLEANUP 2A]: Removed page {num} — AI Boardroom report (not manuscript)")
            removed_count += 1
            continue
        if _is_toc_stub(content):
            print(f"[CLEANUP 2A]: Removed page {num} — TOC stub/placeholder")
            removed_count += 1
            continue
        clean_pages.append((num, content))
    
    # Step 2: Detect and remove the full-book dump page
    dump_page = _detect_full_dump_page(clean_pages)
    if dump_page is not None:
        # Verify it actually contains content from other pages
        dump_content = next((c for n, c in clean_pages if n == dump_page), "")
        other_pages = [(n, c) for n, c in clean_pages if n != dump_page and len(c) > 200]
        if other_pages:
            overlap = _content_overlap(other_pages[0][1], dump_content)
            if overlap > 0.4:
                clean_pages = [(n, c) for n, c in clean_pages if n != dump_page]
                print(f"[CLEANUP 2A]: Removed page {dump_page} — full-book dump (content duplicated in chapter pages)")
                removed_count += 1
    
    # Step 3: Detect and remove OCR duplicate pages
    ocr_pages = _detect_ocr_pages(clean_pages)
    if ocr_pages and len(clean_pages) > len(ocr_pages):
        # Only remove OCR pages if we have non-OCR pages with the same content
        non_ocr = [(n, c) for n, c in clean_pages if n not in ocr_pages]
        if non_ocr:
            # Check overlap between first OCR page and non-OCR content
            non_ocr_text = ' '.join(c for _, c in non_ocr)
            sample_ocr = next((c for n, c in clean_pages if n in ocr_pages[:5] and len(c) > 100), "")
            if sample_ocr:
                overlap = _content_overlap(sample_ocr, non_ocr_text)
                if overlap > 0.3:
                    clean_pages = [(n, c) for n, c in clean_pages if n not in ocr_pages]
                    print(f"[CLEANUP 2A]: Removed {len(ocr_pages)} OCR-scanned pages — content duplicated in parsed pages")
                    removed_count += len(ocr_pages)
    
    print(f"[CLEANUP 2A]: Source deduplication complete — removed {removed_count} pages, keeping {len(clean_pages)}")
    return clean_pages


# ─── PHASE 2B: ARTIFACT STRIPPING ───────────────────────────────────────

def phase_2b_strip_artifacts(text: str) -> str:
    """Remove page markers, system metadata, roman numeral page numbers, and pipeline artifacts."""
    
    # Strip page markers: --- [PAGE START: page_X.rtf] ---
    text = re.sub(r'---\s*\[PAGE START:.*?\]\s*---\n?', '', text)
    
    # Strip system headers and metadata
    text = re.sub(r'# TomeMaster Unified Manuscript\n', '', text)
    text = re.sub(r'Generated on:.*?\n', '', text)
    text = re.sub(r'>\s*\[SYSTEM STATUS\].*?\n', '', text)
    text = re.sub(r'>\s*\[DIRECTORIAL ALERT\].*?\n', '', text)
    text = re.sub(r'---\s*\[START OF DOCUMENT\]\s*---\n?', '', text)
    text = re.sub(r'---\s*\[END OF DOCUMENT\]\s*---\n?', '', text)
    text = re.sub(r'\[DIRECTORIAL ALERT:.*?\]', '', text)
    text = re.sub(r'\[SYSTEM STATUS:.*?\]', '', text)
    
    # Strip roman numeral page numbers at start of lines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if _is_roman_page_number(stripped):
            # Remove just the roman numeral prefix, keep the rest
            cleaned = ROMAN_PATTERN.sub('', stripped, count=1)
            if cleaned.strip():
                cleaned_lines.append(cleaned)
            # If nothing left after removing numeral, skip the line
        else:
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Strip standalone page numbers (lines that are just a number)
    text = re.sub(r'^\d{1,4}\s*$', '', text, flags=re.MULTILINE)
    
    # Strip <page><number>X</number><text>...</text></page> XML wrappers
    text = re.sub(r'<page>\s*<number>\d+</number>\s*<text>', '', text)
    text = re.sub(r'</text>\s*</page>', '', text)
    
    return text


# ─── PHASE 2C: QUOTE/APOSTROPHE RESTORATION ─────────────────────────────

def phase_2c_restore_quotes(text: str) -> Tuple[str, int]:
    """Fix RTF smart-quote corruption: ? → ' for contractions, ? → " for dialogue."""
    fixes_count = 0
    
    # Step 1: Fix known contractions (high confidence)
    for pattern, replacement in _COMPILED_CONTRACTIONS:
        text, n = pattern.subn(replacement, text)
        fixes_count += n
    
    # Step 2: Fix dialogue quotes — ? at start of quoted speech
    # Pattern: space/newline + ? + Capital letter = opening quote
    def fix_opening_quote(m):
        return m.group(1) + '"' + m.group(2)
    text, n = re.subn(r'([\s\n])\s*\?([A-Z])', fix_opening_quote, text)
    fixes_count += n
    
    # Pattern: punctuation + ? + space/newline = closing quote
    def fix_closing_quote(m):
        return m.group(1) + '"' + m.group(2)
    text, n = re.subn(r'([.!,;:])\s*\?(\s)', fix_closing_quote, text)
    fixes_count += n
    
    # Pattern: word + ? + comma/period (end of quote)
    def fix_closing_quote2(m):
        return m.group(1) + '"' + m.group(2)
    text, n = re.subn(r'(\w)\s*\?\s*([,.])', fix_closing_quote2, text)
    fixes_count += n
    
    # Step 3: Fix standalone ?" at end of quote blocks
    text, n = re.subn(r'\?\s*"', '"', text)
    fixes_count += n
    
    print(f"[CLEANUP 2C]: Restored {fixes_count} corrupted quotes/apostrophes")
    return text, fixes_count


# ─── PHASE 2D: CHAPTER EXTRACTION ───────────────────────────────────────

# Common chapter heading patterns
CHAPTER_HEADING_PATTERNS = [
    re.compile(r'^Chapter\s+\d+', re.IGNORECASE),
    re.compile(r'^Part\s+\d+', re.IGNORECASE),
    re.compile(r'^Prologue\s*$', re.IGNORECASE),
    re.compile(r'^Epilogue\s*$', re.IGNORECASE),
    re.compile(r'^Foreword\s*$', re.IGNORECASE),
    re.compile(r'^Preface\s*$', re.IGNORECASE),
    re.compile(r'^Introduction\s*$', re.IGNORECASE),
    re.compile(r'^Afterword\s*$', re.IGNORECASE),
]


def _is_likely_heading(line: str, next_line: str = "") -> bool:
    """Heuristic: Is this line likely a chapter heading?"""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    
    # Explicit chapter markers
    for pat in CHAPTER_HEADING_PATTERNS:
        if pat.match(stripped):
            return True
    
    # Title-case short line followed by blank or long paragraph
    if len(stripped) < 60 and not stripped.endswith(('.', ',', ';', ':', '!')):
        words = stripped.split()
        if len(words) >= 2 and len(words) <= 12:
            # Most words capitalized
            cap_words = sum(1 for w in words if w[0].isupper() or w in ('and', 'the', 'of', 'in', 'a', 'an', 'to', 'for', '&', 'or'))
            if cap_words / len(words) >= 0.6:
                # Must be followed by blank line or long content
                if not next_line.strip() or len(next_line.strip()) > 80:
                    return True
    
    return False


def phase_2d_extract_chapters(text: str) -> Tuple[str, List[Dict]]:
    """Detect chapter headings, format as ## H2, generate TOC."""
    lines = text.split('\n')
    chapters = []
    result_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        
        stripped = line.strip()
        
        # Check if this line is a chapter heading
        if stripped and _is_likely_heading(stripped, next_line):
            # Don't double-## lines that are already headings
            if not stripped.startswith('#'):
                heading_text = stripped
                # Clean up common artifacts
                heading_text = re.sub(r'^\d+\.\s*', '', heading_text)  # Remove "1. " prefix
                heading_text = heading_text.strip()
                
                if heading_text:
                    chapters.append({
                        'title': heading_text,
                        'line_index': len(result_lines)
                    })
                    result_lines.append(f"\n## {heading_text}\n")
                    i += 1
                    continue
        
        result_lines.append(line)
        i += 1
    
    # Build TOC if we found chapters
    body = '\n'.join(result_lines)
    
    if chapters:
        toc_lines = ["## Table of Contents\n"]
        for idx, ch in enumerate(chapters, 1):
            slug = re.sub(r'[^a-z0-9\s-]', '', ch['title'].lower())
            slug = re.sub(r'\s+', '-', slug.strip())
            toc_lines.append(f"{idx}. [{ch['title']}](#{slug})")
        toc_lines.append("\n---\n")
        toc = '\n'.join(toc_lines)
        
        # Prepend TOC to the body
        body = toc + '\n' + body
    
    print(f"[CLEANUP 2D]: Extracted {len(chapters)} chapter headings")
    return body, chapters


# ─── PHASE 2E: PARAGRAPH NORMALIZATION ──────────────────────────────────

def phase_2e_normalize(text: str) -> str:
    """Collapse excessive blank lines, normalize line endings, clean whitespace."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # Strip trailing whitespace from each line
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)
    
    # Strip leading/trailing whitespace from entire document
    text = text.strip()
    
    return text


# ─── MASTER PIPELINE ────────────────────────────────────────────────────

def run_post_stitch_cleanup(folder_path: str) -> bool:
    """
    Master Phase 2 cleanup pipeline.
    
    Reads Unified_Manuscript.md → produces Clean_Manuscript.md
    Called automatically after resort_from_cache() completes.
    
    Returns True on success, False on failure.
    """
    unified_path = os.path.join(folder_path, "Unified_Manuscript.md")
    clean_path = os.path.join(folder_path, "Clean_Manuscript.md")
    
    if not os.path.exists(unified_path):
        print("[CLEANUP]: No Unified_Manuscript.md found — skipping Phase 2")
        return False
    
    try:
        print("[CLEANUP]: ═══════════════════════════════════════════════════")
        print("[CLEANUP]: POST-STITCH CLEANUP PIPELINE — Phase 2 Starting")
        print("[CLEANUP]: ═══════════════════════════════════════════════════")
        start_time = time.time()
        
        with open(unified_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()
        
        original_size = len(raw_text)
        print(f"[CLEANUP]: Input: {original_size:,} chars from Unified_Manuscript.md")
        
        # Phase 2A: Source Deduplication
        pages = _parse_pages(raw_text)
        if pages:
            print(f"[CLEANUP 2A]: Found {len(pages)} pages — analyzing for duplicates...")
            deduped_pages = phase_2a_dedup(pages)
            # Reconstruct text from deduplicated pages
            text = '\n\n'.join(content for _, content in deduped_pages)
        else:
            # No page markers found — use raw text as-is
            print("[CLEANUP 2A]: No page markers found — using raw text")
            text = raw_text
        
        # Phase 2B: Artifact Stripping
        text = phase_2b_strip_artifacts(text)
        print(f"[CLEANUP 2B]: Artifacts stripped — {len(text):,} chars remaining")
        
        # Phase 2C: Quote/Apostrophe Restoration
        text, fixes = phase_2c_restore_quotes(text)
        
        # Phase 2D: Chapter Extraction
        text, chapters = phase_2d_extract_chapters(text)
        
        # Phase 2E: Paragraph Normalization
        text = phase_2e_normalize(text)
        
        # Count remaining ambiguous ? marks
        remaining_questions = len(re.findall(r' \? ', text))
        
        # Write Clean_Manuscript.md
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        elapsed = round(time.time() - start_time, 2)
        final_size = len(text)
        reduction = round((1 - final_size / original_size) * 100, 1) if original_size > 0 else 0
        
        print(f"[CLEANUP]: ═══════════════════════════════════════════════════")
        print(f"[CLEANUP]: PIPELINE COMPLETE in {elapsed}s")
        print(f"[CLEANUP]:   Input:  {original_size:,} chars (Unified_Manuscript.md)")
        print(f"[CLEANUP]:   Output: {final_size:,} chars (Clean_Manuscript.md)")
        print(f"[CLEANUP]:   Reduction: {reduction}%")
        print(f"[CLEANUP]:   Chapters: {len(chapters)}")
        print(f"[CLEANUP]:   Quotes fixed: {fixes}")
        print(f"[CLEANUP]:   Remaining ? marks: {remaining_questions}")
        print(f"[CLEANUP]: ═══════════════════════════════════════════════════")
        
        return True
        
    except Exception as e:
        print(f"[CLEANUP ERROR]: Phase 2 pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False
