import io
import base64
import os
import shutil
import fitz # PyMuPDF
from PIL import Image
from typing import List, Tuple, Optional

# ─── Text-Layer Detection Threshold ──────────────────────────────────────────
# If the first 3 pages of a PDF yield more than this many characters, we
# treat it as a digital PDF with native text — skip OCR, use text extraction.
_TEXT_LAYER_THRESHOLD = 150


def _pdf_has_text_layer(f_path: str) -> bool:
    """Returns True if the PDF has a native selectable-text layer.
    
    Scans the first 3 pages. If the combined text exceeds the threshold,
    the PDF is digital (exported from Word, InDesign, etc.) — NOT a scan.
    """
    try:
        doc = fitz.open(f_path)
        sample = ""
        for i in range(min(3, len(doc))):
            sample += doc.load_page(i).get_text("text").strip()
            if len(sample) > _TEXT_LAYER_THRESHOLD:
                doc.close()
                return True
        doc.close()
        return len(sample) > _TEXT_LAYER_THRESHOLD
    except Exception:
        return False


def parse_text_pdf(f_path: str) -> Optional[str]:
    """[TEXT EXTRACTION]: Extracts all text from a digital PDF using native scraping.
    
    Returns the full text content with page markers, or None on failure.
    This is orders of magnitude faster than OCR and produces zero errors on
    clean digital documents.
    """
    try:
        doc = fitz.open(f_path)
        pages_text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if text:
                pages_text.append(f"<page><number>{page_num + 1}</number><text>{text}</text></page>")
        doc.close()
        if pages_text:
            print(f"[TEXT PARSE]: Extracted {len(pages_text)} pages from digital PDF: {os.path.basename(f_path)}")
            return "\n".join(pages_text)
        return None
    except Exception as e:
        print(f"[TEXT PARSE ERROR]: Failed to extract text from {f_path}: {e}")
        return None


def parse_text_docx(f_path: str) -> Optional[str]:
    """[TEXT EXTRACTION]: Extracts all text from a Word .docx file.
    
    Returns page-tagged text content, or None on failure.
    Word files are NEVER scanned images — they always have native text.
    """
    try:
        from docx import Document
        doc = Document(f_path)
        
        # Word doesn't have explicit pages, but we can split by page breaks
        # or treat sections as pages. For manuscript fidelity, we group by
        # paragraph and use section breaks / page-break-before as markers.
        current_page = []
        pages = []
        page_num = 0
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            # Check for page break in paragraph's XML
            has_page_break = False
            if para._p is not None:
                from lxml import etree
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                # Check for w:br with type="page" 
                breaks = para._p.findall('.//w:br[@w:type="page"]', ns)
                if breaks:
                    has_page_break = True
                # Check for pageBreakBefore in paragraph properties
                pPr = para._p.find('.//w:pPr/w:pageBreakBefore', ns)
                if pPr is not None:
                    has_page_break = True
            
            if has_page_break and current_page:
                page_num += 1
                pages.append(f"<page><number>{page_num}</number><text>{chr(10).join(current_page)}</text></page>")
                current_page = []
            
            if text:
                current_page.append(text)
        
        # Flush remaining content
        if current_page:
            page_num += 1
            pages.append(f"<page><number>{page_num}</number><text>{chr(10).join(current_page)}</text></page>")
        
        if pages:
            print(f"[TEXT PARSE]: Extracted {len(pages)} pages from Word doc: {os.path.basename(f_path)}")
            return "\n".join(pages)
        return None
    except Exception as e:
        print(f"[TEXT PARSE ERROR]: Failed to parse DOCX {f_path}: {e}")
        return None


def is_parseable_document(f_path: str) -> bool:
    """Returns True if the file should be TEXT-PARSED instead of OCR'd.
    
    This covers:
    - .docx files (always parseable via python-docx)
    - .doc / .wpd / .wps / .odt files (legacy formats — parsed via COM or fallback)
    - .pdf files WITH a native text layer (exported from Word, InDesign, etc.)
    
    Returns False for:
    - .pdf files that are pure scans (no text layer → needs OCR)
    - Image files (.jpg, .png, etc.)
    """
    from services.transcriber.legacy_parser import LEGACY_EXTENSIONS
    lower = f_path.lower()
    ext = os.path.splitext(lower)[1]
    if lower.endswith('.docx'):
        return True
    if ext in LEGACY_EXTENSIONS:
        return True  # .doc, .wpd, .wps, .odt — always text, never scanned images
    if lower.endswith('.pdf'):
        return _pdf_has_text_layer(f_path)
    return False


def parse_document_text(f_path: str) -> Optional[str]:
    """[SMART ROUTER]: Extracts text from a parseable document.
    
    Routes: .docx → python-docx, .doc/.wpd/.wps/.odt → legacy_parser, .pdf → PyMuPDF
    Returns <page>-tagged text ready for the RTF pipeline, or None on failure.
    Call is_parseable_document() first to verify the file qualifies.
    """
    from services.transcriber.legacy_parser import LEGACY_EXTENSIONS, parse_legacy_document
    lower = f_path.lower()
    ext = os.path.splitext(lower)[1]
    
    if lower.endswith('.docx'):
        return parse_text_docx(f_path)
    if ext in LEGACY_EXTENSIONS:
        # .doc, .wpd, .wps, .odt → Manuscript Resurrection Engine
        result = parse_legacy_document(f_path)
        if result:
            print(f"[SMART ROUTE]: {os.path.basename(f_path)} → legacy parse (resurrected, no API credits)")
            return result
        # Legacy parser exhausted — caller will fall back to OCR
        print(f"[SMART ROUTE]: Legacy parse failed for {os.path.basename(f_path)}, falling back to OCR")
        return None
    if lower.endswith('.pdf'):
        return parse_text_pdf(f_path)
    return None


def process_asset(f_path: str, folder_path: str) -> List[Tuple[Image.Image, str]]:
    """
    [VISION PROCESSOR]: Converts a manuscript asset (PDF or Image) into 
    processable high-fidelity image buffers.
    """
    images_to_process = []
    
    if f_path.lower().endswith(".pdf"):
        try:
            pdf_doc = fitz.open(f_path)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images_to_process.append((img, f"{f_path}_p{page_num+1}"))
            pdf_doc.close()
        except Exception as e:
            print(f"VISION ERROR: Failed to unpack PDF {f_path}: {e}")
    else:
        try:
            with Image.open(f_path) as img_check:
                img_check.verify()
            with Image.open(f_path) as img:
                img.load() 
                images_to_process.append((img.copy(), f_path))
        except Exception as e:
            print(f"VISION ERROR: Asset Corruption Detected: {os.path.basename(f_path)}. Isolating...")
            failed_dir = os.path.join(folder_path, "Failed_Assets")
            os.makedirs(failed_dir, exist_ok=True)
            try:
                shutil.move(f_path, os.path.join(failed_dir, os.path.basename(f_path)))
            except: pass
            
    return images_to_process

def generate_telemetry(img: Image.Image) -> str:
    """Generates a base64 encoded thumbnail for frontend streaming."""
    buffered = io.BytesIO()
    with img.copy() as thumb:
        thumb.thumbnail((512, 512)) 
        thumb.save(buffered, format="JPEG", quality=60)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')
