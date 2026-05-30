"""
services/parsers — Per-format document parsers with lazy imports.

Loading TXT doesn't pull in PyMuPDF + PIL + ebooklib.
Each sub-module is imported on first use.

Public API (backward-compatible with document_parser.py):
    parse_txt(content)        → str
    parse_docx(content)       → dict
    parse_pdf_smart(content)  → dict
    stream_pdf_smart(content) → generator
    parse_epub(content)       → dict
    truncate_for_demo(data)   → dict
"""


def parse_txt(content: bytes) -> str:
    from .txt_parser import parse_txt
    return parse_txt(content)


def parse_docx(content: bytes) -> dict:
    from .docx_parser import parse_docx
    return parse_docx(content)


def parse_pdf_smart(content: bytes, api_key: str = "") -> dict:
    from .pdf_parser import parse_pdf_smart
    return parse_pdf_smart(content, api_key)


def stream_pdf_smart(content: bytes, api_key: str = "", is_demo: bool = False, folder_path: str = None):
    from .pdf_parser import stream_pdf_smart
    return stream_pdf_smart(content, api_key, is_demo, folder_path)


def parse_epub(content: bytes) -> dict:
    from .epub_parser import parse_epub
    return parse_epub(content)


def truncate_for_demo(data: dict) -> dict:
    from .docx_parser import truncate_for_demo
    return truncate_for_demo(data)
