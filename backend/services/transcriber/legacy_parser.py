"""
[LEGACY PARSER]: Manuscript Resurrection Engine for legacy document formats.

Supports: .doc (Word 97-2003), .wpd (WordPerfect), .wps (MS Works), .odt (OpenDocument)

Strategy (Windows Desktop):
1. Primary: pywin32 COM automation — opens any format Microsoft Word can handle
2. Fallback: olefile text extraction for .doc when Word is unavailable
3. Last resort: return None → caller falls back to OCR pipeline

TomeMaster is a "Manuscript Resurrection Tool" — people bring files from the 1990s.
This module ensures NOTHING gets left behind.
"""

import os
import platform
import tempfile
import time
from typing import Optional

# ─── Tier Detection ──────────────────────────────────────────────────────────

_WORD_COM_AVAILABLE: Optional[bool] = None

LEGACY_EXTENSIONS = {'.doc', '.wpd', '.wps', '.odt'}
# .docx is handled natively by python-docx — not a "legacy" format


def _check_word_com() -> bool:
    """Probes for pywin32 + Word COM server. Cached after first call."""
    global _WORD_COM_AVAILABLE
    if _WORD_COM_AVAILABLE is not None:
        return _WORD_COM_AVAILABLE

    if platform.system() != "Windows":
        _WORD_COM_AVAILABLE = False
        return False

    try:
        import win32com.client  # noqa: F401
        # Quick probe: can we instantiate Word?
        word = win32com.client.Dispatch("Word.Application")
        word.Quit()
        _WORD_COM_AVAILABLE = True
        print("[LEGACY PARSER]: Microsoft Word COM automation available ✓")
    except Exception as e:
        _WORD_COM_AVAILABLE = False
        print(f"[LEGACY PARSER]: Word COM not available ({e}). Will use fallback parsers.")

    return _WORD_COM_AVAILABLE


def is_legacy_document(f_path: str) -> bool:
    """Returns True if the file is a legacy format this module can handle."""
    ext = os.path.splitext(f_path.lower())[1]
    return ext in LEGACY_EXTENSIONS


# ─── Tier 1: COM Automation ──────────────────────────────────────────────────

def _parse_via_word_com(f_path: str) -> Optional[str]:
    """Opens the file in Word via COM, extracts text page-by-page.

    Word can open: .doc, .docx, .wpd, .wps, .odt, .rtf, .txt, .html, .xml
    This is the nuclear option — if Word can open it, we can read it.
    """
    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        word = None
        doc = None

        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # Suppress all dialogs

            abs_path = os.path.abspath(f_path)
            doc = word.Documents.Open(
                abs_path,
                ReadOnly=True,
                AddToRecentFiles=False,
                ConfirmConversions=False,  # Don't ask about format
            )

            pages = []
            total_pages = doc.ComputeStatistics(2)  # wdStatisticPages = 2

            if total_pages <= 1:
                # Single page or can't detect pages — grab everything
                text = doc.Content.Text.strip()
                if text:
                    pages.append(f"<page><number>1</number><text>{text}</text></page>")
            else:
                # Extract page-by-page using the Range.GoTo method
                for page_num in range(1, total_pages + 1):
                    try:
                        # Navigate to page start
                        page_range = doc.GoTo(What=1, Which=1, Count=page_num)  # wdGoToPage=1, wdGoToAbsolute=1

                        # Find page end (start of next page, or end of doc)
                        if page_num < total_pages:
                            next_page = doc.GoTo(What=1, Which=1, Count=page_num + 1)
                            page_range = doc.Range(page_range.Start, next_page.Start)
                        else:
                            page_range = doc.Range(page_range.Start, doc.Content.End)

                        text = page_range.Text.strip()
                        if text:
                            pages.append(f"<page><number>{page_num}</number><text>{text}</text></page>")
                    except Exception:
                        # If page nav fails, grab remaining content
                        remaining = doc.Range(page_range.Start if page_range else 0, doc.Content.End)
                        text = remaining.Text.strip()
                        if text:
                            pages.append(f"<page><number>{page_num}</number><text>{text}</text></page>")
                        break

            if pages:
                ext = os.path.splitext(f_path)[1].upper().lstrip('.')
                print(f"[LEGACY PARSE]: Extracted {len(pages)} pages from {ext} file via Word COM: {os.path.basename(f_path)}")
                return "\n".join(pages)

            return None

        finally:
            if doc:
                try:
                    doc.Close(SaveChanges=0)
                except:
                    pass
            if word:
                try:
                    word.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()

    except ImportError:
        print("[LEGACY PARSER]: pywin32 not installed — skipping COM extraction")
        return None
    except Exception as e:
        print(f"[LEGACY PARSE ERROR]: Word COM failed for {os.path.basename(f_path)}: {e}")
        return None


# ─── Tier 2: olefile fallback for .doc ───────────────────────────────────────

def _parse_doc_via_olefile(f_path: str) -> Optional[str]:
    """Extracts raw text from Word 97-2003 .doc files using OLE2 structure.

    This is a best-effort fallback when Word COM is unavailable.
    It reads the raw text stream from the compound document — formatting is lost
    but manuscript text is preserved. Good enough for resurrection.
    """
    try:
        import olefile

        if not olefile.isOleFile(f_path):
            print(f"[LEGACY PARSER]: {os.path.basename(f_path)} is not a valid OLE2 file")
            return None

        ole = olefile.OleFileIO(f_path)

        text = ""
        # Word stores text in the 'WordDocument' stream, but extracting it
        # requires parsing the FIB (File Information Block). As a simpler approach,
        # try the '1Table' or '0Table' streams which contain the piece table.
        # Actually, the simplest approach: read all streams and look for text.

        # The most reliable simple extraction: read the WordDocument stream
        # and pull out printable text runs
        if ole.exists('WordDocument'):
            raw = ole.openstream('WordDocument').read()
            # Extract printable ASCII/Unicode text runs (min 4 chars)
            import re
            # Try UTF-16LE first (Word 97+ uses Unicode internally)
            try:
                decoded = raw.decode('utf-16-le', errors='ignore')
                # Filter to printable text
                chunks = re.findall(r'[\x20-\x7E\n\r\t]{4,}', decoded)
                text = "\n".join(chunks)
            except:
                pass

            if not text or len(text) < 50:
                # Fallback to ASCII extraction
                chunks = re.findall(rb'[\x20-\x7E\n\r\t]{4,}', raw)
                text = "\n".join(c.decode('ascii', errors='ignore') for c in chunks)

        ole.close()

        if text and len(text.strip()) > 20:
            # Clean up: remove control artifacts, collapse whitespace
            import re as re2
            text = re2.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
            text = re2.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()

            print(f"[LEGACY PARSE]: Extracted ~{len(text)} chars from .doc via OLE fallback: {os.path.basename(f_path)}")
            return f"<page><number>1</number><text>{text}</text></page>"

        return None

    except ImportError:
        print("[LEGACY PARSER]: olefile not installed — cannot parse .doc without Word COM")
        return None
    except Exception as e:
        print(f"[LEGACY PARSE ERROR]: OLE fallback failed for {os.path.basename(f_path)}: {e}")
        return None


# ─── Public API ──────────────────────────────────────────────────────────────

def parse_legacy_document(f_path: str) -> Optional[str]:
    """[MANUSCRIPT RESURRECTION]: Extracts text from legacy document formats.

    Tries COM automation first (most reliable), then format-specific fallbacks.
    Returns <page>-tagged text ready for the RTF pipeline, or None on failure.
    """
    ext = os.path.splitext(f_path.lower())[1]
    basename = os.path.basename(f_path)

    print(f"[LEGACY PARSER]: Processing {ext.upper()} file: {basename}")

    # Tier 1: Word COM automation (handles ALL legacy formats)
    if _check_word_com():
        result = _parse_via_word_com(f_path)
        if result:
            return result
        print(f"[LEGACY PARSER]: Word COM returned no text for {basename}, trying fallbacks...")

    # Tier 2: Format-specific pure-Python fallbacks
    if ext == '.doc':
        result = _parse_doc_via_olefile(f_path)
        if result:
            return result

    # No parser succeeded
    print(f"[LEGACY PARSER]: All parsers exhausted for {basename}. File will need manual conversion or OCR.")
    return None
