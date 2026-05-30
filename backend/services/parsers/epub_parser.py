"""
EPUB parser.

Imports ebooklib and BeautifulSoup only when called.
"""

import io

from .text_utils import _normalize_typography


def parse_epub(content: bytes) -> dict:
    """Specialized parser for EPUB recovery. Extracts HTML spine and maps to TOC."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(io.BytesIO(content))

    html_fragments = []
    full_text = []
    toc = []

    # Process the document spine
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")

        # Extract title/chapter markers from the HTML
        chapter_title = ""
        h1 = soup.find("h1")
        if h1:
            chapter_title = h1.get_text().strip()
            if chapter_title:
                toc.append(
                    {
                        "title": chapter_title,
                        "style": "epub-chapter",
                        "page_number": len(html_fragments) + 1,
                    }
                )

        # Clean the HTML content: Remove style and script tags
        for s in soup(["style", "script"]):
            s.decompose()

        text = soup.get_text()
        full_text.append(text)

        # Normalize the HTML for the TomeMaster editor
        paragraphs = soup.find_all(["p", "h1", "h2", "h3"])
        for p in paragraphs:
            tag = p.name
            p_text = p.get_text().strip()
            if p_text:
                html_fragments.append(f"<{tag}>{p_text}</{tag}>")

    combined_html = "".join(html_fragments)
    combined_text = "\n\n".join(full_text)

    return {
        "text": _normalize_typography(combined_text.strip()),
        "html": _normalize_typography(combined_html),
        "toc": toc,
    }
