"""
Shared text utilities for all document parsers.

Heading detection, paragraph joining, typography normalization,
noise removal, and merged-heading splitting.
"""

import re


def _is_heading_candidate(text: str) -> bool:
    """Intelligent check to see if a paragraph is structurally a heading."""
    prev = text.strip()
    if not prev:
        return False
    # If it's short (< 95 chars) and doesn't end in punctuation, it's a heading.
    if len(prev) < 95 and not re.search(r'[.?!:"\'\)\]]$', prev):
        return True
    # If it starts with common chapter markers
    if re.match(
        r"^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)",
        prev,
        re.I,
    ):
        return True
    # If it's ALL CAPS and short
    if prev.isupper() and len(prev) < 120 and len(prev) > 3:
        return True
    return False


def _should_join_paragraphs(prev_text: str, next_text: str) -> bool:
    """Intelligent safeguard to prevent Chapter Headings and short titles from being merged."""
    prev = prev_text.strip()
    if not prev:
        return False

    # 1. Punctuation is King: If it ends in ANY punctuation, never join!
    if re.search(r'[.?!:"\'\)\]]$', prev):
        return False

    # 2. PROSE LENGTH RULE: Any line shorter than a full printed prose line (e.g. < 120 chars)
    # is likely a Heading, Title, or Name. Don't join!
    if len(prev) < 120:
        return False

    # 2b. If it ends in a number (Page Number / TOC), don't join!
    if re.search(r"\d+$", prev) and len(prev) < 100:
        return False

    # 3. If it starts with common Chapter/Section markers, don't join!
    if re.match(
        r"^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)",
        prev,
        re.I,
    ):
        return False

    # 4. If it's ALL CAPS, it's likely a heading. Don't join!
    if prev.isupper() and len(prev) > 3:
        return False

    # 5. If it looks like a TOC line (high dot density), don't join!
    if "...." in prev or " . . " in prev:
        return False

    return True


def _split_merged_headings(text: str) -> str:
    """Detects if a Chapter Header or title was accidentally merged into prose and splits them."""
    patterns = [
        r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)\s*(?:\d+|[A-Z][a-z]+)?\s*[:.-]?\s+([A-Z""\u300c])',
        r"^([A-V][a-z]+ [A-V][a-z]+ [A-V][a-z]+)\s+([A-Z\"\u201c\u300c])",
        r"^(A Snowy Christmas Eve)\s+([A-Z\"\u201c\u300c])",
    ]
    cleaned = text
    if not cleaned:
        return ""

    for p in patterns:
        cleaned = re.sub(p, r"\1\n\n\2", cleaned, flags=re.MULTILINE)
    return cleaned


def _mop_up_noise(text: str) -> str:
    """Removes specific metadata noise phrases often found in OCR or legacy PDF exports."""
    noise_patterns = [
        r"grammar/spelling corrected",
        r"removed/eliminated added",
        r"corrected added",
        r"THIS CLOSE by Ron Lamb",
    ]
    cleaned = text
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _normalize_typography(text: str) -> str:
    """Normalizes 'Smart' quotes and professional dashes to standard keyboard characters."""
    if not text:
        return ""
    # Curly single quotes / apostrophes
    text = re.sub(r"[\u2018\u2019\u201a\u201b\u02bc\u0060\u00b4]", "'", text)
    # Curly double quotes
    text = re.sub(r"[\u201c\u201d\u201e\u201f]", '"', text)
    # Em-dashes / En-dashes
    text = re.sub(r"[\u2013\u2014]", "--", text)
    return text
