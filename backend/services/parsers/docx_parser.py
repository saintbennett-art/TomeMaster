"""
DOCX and TOC parser.

Imports mammoth and python-docx only when called.
"""

import re
import io

from .text_utils import _normalize_typography


def parse_toc_entry(clean: str, style: str) -> dict:
    """Helper to split dot-leaders and page numbers from titles."""
    match = re.search(
        r"^(.*?)(?:(?:\s*\.\s*){2,}|\s{3,}|\t)[\s]*(\d+)$", clean
    )
    if match:
        return {
            "title": match.group(1).strip(),
            "style": style,
            "page_number": int(match.group(2)),
        }
    return {"title": clean, "style": style, "page_number": 1}


def extract_toc_from_html(html: str) -> list:
    """Extracts structural chapters and TOC entries natively from the Mammoth HTML output."""
    toc = []

    # 1. Grab explicit TOC entries mapped via style_map
    toc_divs = re.findall(r'<div class="toc-entry">(.*?)</div>', html)
    for text in toc_divs:
        clean = re.sub(r"<.*?>", "", text).strip()
        if clean:
            toc.append(parse_toc_entry(clean, "toc-entry"))

    # 2. Grab standard HTML headers produced by Mammoth
    headers = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html)
    for text in headers:
        clean = re.sub(r"<.*?>", "", text).strip()
        if clean:
            toc.append(parse_toc_entry(clean, "heading"))

    # 3. Grab implied chapters masquerading as normal paragraphs
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html)
    for p_text in paragraphs:
        clean = re.sub(r"<.*?>", "", p_text).strip()
        if len(clean) < 150:
            if re.match(
                r"^(chapter\s+\w+|prelude|prologue|epilogue|title page)",
                clean,
                re.IGNORECASE,
            ):
                toc.append(parse_toc_entry(clean, "implied"))
            elif re.search(r"\.{3,}\s*\d+$", clean):
                toc.append(parse_toc_entry(clean, "implied-toc"))

    # Deduplicate in order
    seen = set()
    unique = []
    for item in toc:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)

    # Guarantee physical reading order by sorting against the global HTML stream
    def get_offset(item):
        idx = html.find(item["title"][:20])
        return idx if idx != -1 else float("inf")

    unique.sort(key=get_offset)

    return unique


def truncate_for_demo(data: dict) -> dict:
    """Slices manuscript content to the first 10 chapters for Demo Mode testing."""
    toc = data.get("toc", [])
    if len(toc) <= 10:
        return data

    cut_off_chap = toc[10]
    marker = cut_off_chap.get("title", "")
    if not marker:
        return data

    # Truncate raw text
    text = data.get("text", "")
    text_idx = text.find(marker)
    if text_idx != -1:
        data["text"] = (
            text[:text_idx]
            + "\n\n[DEMO MODE: Remainder of manuscript truncated]"
        )

    # Truncate HTML
    html = data.get("html", "")
    html_search = re.search(
        rf"<h[1-6][^>]*>{re.escape(marker)}", html
    )
    if html_search:
        data["html"] = (
            html[: html_search.start()]
            + "<hr/><p><strong>[DEMO MODE: Remainder of manuscript truncated]</strong></p>"
        )
    else:
        html_idx = html.find(marker)
        if html_idx != -1:
            data["html"] = (
                html[:html_idx]
                + "<hr/><p><strong>[DEMO MODE: Remainder of manuscript truncated]</strong></p>"
            )

    data["toc"] = toc[:10]
    return data


def parse_docx(content: bytes) -> dict:
    """Extracts HTML formatted text, plain text, and a Table of Contents from a docx file byte stream."""
    import mammoth

    custom_style_map = (
        "p[style-name^='TOC'] => div.toc-entry:fresh\n"
        "br[type='page'] => hr.pdf-page-marker:fresh"
    )

    result = mammoth.convert_to_html(
        io.BytesIO(content), style_map=custom_style_map
    )
    html_content = result.value

    toc = extract_toc_from_html(html_content)

    raw_text = mammoth.extract_raw_text(io.BytesIO(content)).value

    return {
        "html": _normalize_typography(html_content),
        "text": _normalize_typography(raw_text),
        "toc": toc,
    }
