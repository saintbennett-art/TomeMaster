"""
Plain-text file parser.

Zero heavy dependencies — only uses text_utils for typography normalization.
"""

from .text_utils import _normalize_typography


def parse_txt(content: bytes) -> str:
    """Parses raw txt file bytes to string, handling common encodings and normalizing typography."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("windows-1252")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")
    return _normalize_typography(text)
