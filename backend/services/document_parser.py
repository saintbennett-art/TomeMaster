import mammoth
import re
import io
import os
import base64
import fitz
from PIL import Image
from openai import OpenAI
from docx import Document
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# MANUSCRIPT_REDLINE_PROMPT (Centralized for Upload + Transcription)
from .transcriber_service import MANUSCRIPT_REDLINE_PROMPT

def _is_heading_candidate(text: str) -> bool:
    """Intelligent check to see if a paragraph is structurally a heading."""
    prev = text.strip()
    if not prev: return False
    # If it's short (< 95 chars) and doesn't end in punctuation, it's a heading.
    if len(prev) < 95 and not re.search(r'[.?!:"\'\)\]]$', prev):
        return True
    # If it starts with common chapter markers
    if re.match(r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)', prev, re.I):
        return True
    # If it's ALL CAPS and short
    if prev.isupper() and len(prev) < 120 and len(prev) > 3:
        return True
    return False

def _should_join_paragraphs(prev_text: str, next_text: str) -> bool:
    """Intelligent safeguard to prevent Chapter Headings and short titles from being merged."""
    prev = prev_text.strip()
    if not prev: return False
    
    # 1. Punctuation is King: If it ends in ANY punctuation, never join!
    if re.search(r'[.?!:"\'\)\]]$', prev):
        return False
        
    # 2. PROSE LENGTH RULE: Any line shorter than a full printed prose line (e.g. < 120 chars) 
    # is likely a Heading, Title, or Name. Don't join! This protects Chapter 1, Prelude, etc.
    if len(prev) < 120:
        return False
        
    # 2b. If it ends in a number (Page Number / TOC), don't join!
    if re.search(r'\d+$', prev) and len(prev) < 100:
        return False
        
    # 3. If it starts with common Chapter/Section markers, don't join!
    if re.match(r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)', prev, re.I):
        return False
        
    # 4. If it's ALL CAPS, it's likely a heading. Don't join!
    if prev.isupper() and len(prev) > 3:
        return False
        
    # 5. If it looks like a TOC line (high dot density), don't join!
    if "...." in prev or " . . " in prev:
        return False
        
    return True

def _split_merged_headings(text: str) -> str:
    """Detects if a Chapter Header or title was accidentally merged into prose on the same line and splits them."""
    # Pattern: Start of line -> Common Header word -> optional number/title -> space -> Quote or Capital Letter 
    patterns = [
        r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)\s*(?:\d+|[A-Z][a-z]+)?\s*[:.-]?\s+([A-Z"“「])',
        # Specific patterns for common title-to-prose merges
        r'^([A-V][a-z]+ [A-V][a-z]+ [A-V][a-z]+)\s+([A-Z"“「])',
        r'^(A Snowy Christmas Eve)\s+([A-Z"“「])',
    ]
    cleaned = text
    if not cleaned: return ""
    
    for p in patterns:
        cleaned = re.sub(p, r'\1\n\n\2', cleaned, flags=re.MULTILINE)
    return cleaned

def _mop_up_noise(text: str) -> str:
    """Removes specific metadata noise phrases often found in OCR or legacy PDF exports."""
    noise_patterns = [
        r'grammar/spelling corrected',
        r'removed/eliminated added',
        r'corrected added',
        r'THIS CLOSE by Ron Lamb' # Specific to user's title page bleed-over
    ]
    cleaned = text
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def _normalize_typography(text: str) -> str:
    """Normalizes 'Smart' quotes and professional dashes to standard keyboard characters."""
    if not text: return ""
    # Curly single quotes / apostrophes
    text = re.sub(r'[\u2018\u2019\u201a\u201b\u02bc\u0060\u00b4]', "'", text)
    # Curly double quotes
    text = re.sub(r'[\u201c\u201d\u201e\u201f]', '"', text)
    # Em-dashes / En-dashes
    text = re.sub(r'[\u2013\u2014]', '--', text)
    return text

# DELETION MARKERS:
# - If you see a light blue highlighter squiggle or ink mark drawn over or across text, OMIT that text from the output. Do NOT add any comments or placeholders about the deletion.

def _is_light_blue(color):
    """Detects if a color (tuple of 3 floats) is in the Light Blue/Cyan spectrum."""
    if not color or len(color) < 3: return False
    r, g, b = color
    # SkyBlue is typically (0.5, 0.7, 1.0). We look for Blue being the dominant channel.
    return b > 0.6 and b > r and b > g

def _get_page_content_purged(page):
    """Extracts text from a page, skipping words that intersect with blue 'INK' or 'HIGHLIGHT' annotations.
    Preserves structural line and block breaks using dictionary mode."""
    
    # 1. Detection Phase: Identify Blue Deletion Zones
    annots = page.annots()
    blue_rects = []
    if annots:
        for annot in annots:
            if annot.type[0] in [8, 15]:
                if _is_light_blue(annot.colors.get("stroke")) or _is_light_blue(annot.colors.get("fill")):
                    if annot.rect.width > 10 and annot.rect.height > 10:
                        blue_rects.append(annot.rect)
    
    # 2. Extraction Phase: Iterate through blocks and lines to preserve prose flow
    text_dict = page.get_text("dict")
    
    # TOC Skipping Check: If page has > 5 lines with many dots (leaders), it's likely a TOC page
    dots_counts = 0
    
    final_blocks = []
    for b in text_dict["blocks"]:
        if b["type"] != 0: continue # Skip image blocks
        
        block_lines = []
        for l in b["lines"]:
            line_text = ""
            for s in l["spans"]:
                s_text = s["text"]
                s_rect = fitz.Rect(s["bbox"])
                
                # Enhanced TOC detection: Look for dots, leaders, or trailing page numbers
                if re.search(r'\.{3,}|(?:\s\.\s){2,}', s_text) or re.search(r'\d+$', s_text.strip()):
                    # Only count as TOC line if it's relatively short (typical for TOC)
                    if len(s_text.strip()) < 100:
                        dots_counts += 1
                
                if blue_rects:
                    is_purged = False
                    s_area = s_rect.get_area()
                    for br in blue_rects:
                        if s_rect.intersects(br):
                            intersect_area = (s_rect & br).get_area()
                            if s_area > 0 and (intersect_area / s_area) > 0.4:
                                is_purged = True
                                break
                    if not is_purged:
                        line_text += (" " if line_text and not line_text.endswith(" ") else "") + s_text
                else:
                    line_text += (" " if line_text and not line_text.endswith(" ") else "") + s_text
            
            if line_text.strip():
                block_lines.append(line_text.strip())
        
        if block_lines:
            # JOIN with DOUBLE newline to ensure every line is evaluated as a potential paragraph
            final_blocks.append("\n\n".join(block_lines))
            
    if dots_counts > 4:
        return ""
        
    return _mop_up_noise("\n\n".join(final_blocks))

def parse_txt(content: bytes) -> str:
    """Parses raw txt file bytes to string, handling common encodings and normalizing typography."""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = content.decode('windows-1252')
        except UnicodeDecodeError:
            text = content.decode('latin-1', errors='replace')
    return _normalize_typography(text)

def parse_toc_entry(clean: str, style: str) -> dict:
    """Helper to split dot-leaders and page numbers from titles."""
    # Match strings exactly like "Title ..... 14" or "Title . . . 14" or "Title      14"
    match = re.search(r'^(.*?)(?:(?:\s*\.\s*){2,}|\s{3,}|\t)[\s]*(\d+)$', clean)
    if match:
        return {"title": match.group(1).strip(), "style": style, "page_number": int(match.group(2))}
    return {"title": clean, "style": style, "page_number": 1}

def extract_toc_from_html(html: str) -> list:
    """Extracts structural chapters and TOC entries natively from the Mammoth HTML output."""
    toc = []
    
    # 1. Grab explicit TOC entries mapped via style_map
    toc_divs = re.findall(r'<div class="toc-entry">(.*?)</div>', html)
    for text in toc_divs:
        clean = re.sub(r'<.*?>', '', text).strip()
        if clean: toc.append(parse_toc_entry(clean, "toc-entry"))
        
    # 2. Grab standard HTML headers produced by Mammoth
    headers = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html)
    for text in headers:
        clean = re.sub(r'<.*?>', '', text).strip()
        if clean: toc.append(parse_toc_entry(clean, "heading"))
        
    # 3. Grab implied chapters masquerading as normal paragraphs
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html)
    for p_text in paragraphs:
        clean = re.sub(r'<.*?>', '', p_text).strip()
        # Ensure it's short, starts with chapter wording, or has TOC dot leaders
        if len(clean) < 150:
            if re.match(r"^(chapter\s+\w+|prelude|prologue|epilogue|title page)", clean, re.IGNORECASE):
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
        return idx if idx != -1 else float('inf')
        
    unique.sort(key=get_offset)
            
    return unique

def truncate_for_demo(data: dict) -> dict:
    """Slices manuscript content to the first 10 chapters for Demo Mode testing."""
    toc = data.get("toc", [])
    if len(toc) <= 10:
        return data
        
    # The 11th chapter starts where the demo should end
    cut_off_chap = toc[10]
    marker = cut_off_chap.get("title", "")
    if not marker:
        return data
        
    # Truncate raw text
    text = data.get("text", "")
    text_idx = text.find(marker)
    if text_idx != -1:
        data["text"] = text[:text_idx] + "\n\n[DEMO MODE: Remainder of manuscript truncated]"
        
    # Truncate HTML
    html = data.get("html", "")
    # Search for the marker in the HTML. Mammoth usually wraps markers in header tags.
    html_search = re.search(rf'<h[1-6][^>]*>{re.escape(marker)}', html)
    if html_search:
        data["html"] = html[:html_search.start()] + "<hr/><p><strong>[DEMO MODE: Remainder of manuscript truncated]</strong></p>"
    else:
        # Fallback to simple title text search in HTML
        html_idx = html.find(marker)
        if html_idx != -1:
            data["html"] = html[:html_idx] + "<hr/><p><strong>[DEMO MODE: Remainder of manuscript truncated]</strong></p>"
            
    # Truncate TOC
    data["toc"] = toc[:10]
    return data

def parse_docx(content: bytes) -> dict:
    """Extracts HTML formatted text, plain text, and a Table of Contents from a docx file byte stream."""
    
    # Custom mapping to unify Hard Page Breaks with the PDF page marker for automatic purging
    custom_style_map = (
        "p[style-name^='TOC'] => div.toc-entry:fresh\n"
        "br[type='page'] => hr.pdf-page-marker:fresh"
    )
    
    # Use mammoth to convert DOCX to cleaner HTML
    result = mammoth.convert_to_html(
        io.BytesIO(content),
        style_map=custom_style_map
    )
    html_content = result.value
    
    # Extract TOC deeply via HTML to bypass invisible word SDTs
    toc = extract_toc_from_html(html_content)
    
    # We also need pure text for word counts and preview
    raw_text = mammoth.extract_raw_text(io.BytesIO(content)).value
    
    return {
        "html": _normalize_typography(html_content),
        "text": _normalize_typography(raw_text),
        "toc": toc
    }

def parse_epub(content: bytes) -> dict:
    """Specialized private parser for EPUB recovery. Extracts HTML spine and maps to TOC."""
    book = epub.read_epub(io.BytesIO(content))
    
    html_fragments = []
    full_text = []
    toc = []
    
    # Process the document spine
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        
        # Extract title/chapter markers from the HTML
        chapter_title = ""
        h1 = soup.find('h1')
        if h1:
            chapter_title = h1.get_text().strip()
            if chapter_title:
                toc.append({"title": chapter_title, "style": "epub-chapter", "page_number": len(html_fragments) + 1})
        
        # Clean the HTML content: Remove style and script tags
        for s in soup(['style', 'script']):
            s.decompose()
            
        text = soup.get_text()
        full_text.append(text)
        
        # Normalize the HTML for the TomeMaster editor
        # We preserve basic paragraph structure
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3'])
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
        "toc": toc
    }

def parse_pdf_smart(content: bytes, api_key: str = "") -> dict:
    """Intelligently parses PDF using blazing-fast native text scraping if available, falling back to Vision OCR for pure image scans."""
    pdf_doc = fitz.open(stream=content, filetype="pdf")
    
    # Heuristic Check: Does the PDF have a native digital text layer?
    # We check the first 3 pages. If total scraped characters > 150, we assume it's a native digital PDF.
    sample_text = ""
    for i in range(min(3, len(pdf_doc))):
        sample_text += pdf_doc.load_page(i).get_text("text").strip()
        
    full_text = ""
    toc = []
    html_fragments = []
    
    if len(sample_text) > 150:
        # PATH A: BLAZING FAST NATIVE SCRAPE
        print("Native text layer detected! Bypassing OCR...")
        collected_text = ""
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            page_content = _get_page_content_purged(page).strip()
            if not page_content:
                page_content = f"PAGE {page_num + 1} EMPTY"
            
            # Use Double Newline between pages to prevent page-break mashing
            collected_text += page_content + "\n\n"
            
            first_line = page_content.split('\n')[0].strip()
            if len(first_line) < 100 and len(first_line) > 0:
                toc.append({"title": first_line, "style": "pdf-page-marker", "page_number": page_num + 1})
        
        # Now parse the entire document as one coherent stream
        full_text = collected_text.strip()
        
        # Cleanly enforce that any single \n is merged into a space!
        # Only \n\n (or more) will be treated as distinct paragraphs.
        clean_content = re.sub(r'(?<!\n)\n(?!\n)', ' ', full_text)
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', clean_content) if p.strip()]
        
        # We NO LONGER insert the <hr> markers here by default because the user wants them GONE.
        # This prevents mid-sentence breaks before they reach the editor.
        html_fragments = [f"<p>{p}</p>" for p in paragraphs]
                
    else:
        # PATH B: OCR VISION FALLBACK FOR SCANNED IMAGES
        print("No native text layer detected. Booting Vision OCR...")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY", "")
            
        if not api_key:
            raise ValueError("Missing OpenAI API Key for Handwriting Vision Analysis.")
            
        client = OpenAI(api_key=api_key)
        collected_text = ""
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=90)
            img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": MANUSCRIPT_REDLINE_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                max_tokens=2500
            )
            
            raw_text = response.choices[0].message.content
            text_match = re.search(r'<text>(.*?)</text>', raw_text, re.DOTALL)
            if text_match:
                page_content = text_match.group(1).strip()
                if "output this placeholder text" in page_content: page_content = ""
                if "[BLANK_PAGE]" in page_content: page_content = ""
                
                # Fail-Safe: Split any headings the AI merged onto the same line
                page_content = _split_merged_headings(page_content)
                
                # Use Double Newline between pages to prevent page-break mashing
                if collected_text and not collected_text.endswith('\n\n'):
                    collected_text += "\n\n"
                collected_text += page_content + "\n\n"
                
                first_line = page_content.split('\n')[0].strip()
                if len(first_line) < 100 and len(first_line) > 0:
                    toc.append({"title": first_line, "style": "pdf-page-marker", "page_number": page_num + 1})

        full_text = collected_text.strip()
        
        # Split by ANY newline to evaluate every line as a potential paragraph
        paragraphs = [p.strip() for p in re.split(r'\n+', full_text) if p.strip()]
        
        # Build HTML with smart joining and H1 wrapping
        html_fragments = []
        if paragraphs:
            current_p = paragraphs[0]
            for i in range(1, len(paragraphs)):
                next_p = paragraphs[i]
                if _should_join_paragraphs(current_p, next_p):
                    current_p += " " + next_p
                else:
                    tag = "h1" if _is_heading_candidate(current_p) else "p"
                    html_fragments.append(f"<{tag}>{current_p}</{tag}>")
                    current_p = next_p
            tag = "h1" if _is_heading_candidate(current_p) else "p"
            html_fragments.append(f"<{tag}>{current_p}</{tag}>")

    pdf_doc.close()
    
    html = f"<div class='pdf-manuscript'>{''.join(html_fragments)}</div>"
    
    return {
        "text": _normalize_typography(full_text.strip()),
        "html": _normalize_typography(html),
        "toc": toc
    }

def stream_pdf_smart(content: bytes, api_key: str = "", is_demo: bool = False, folder_path: str = None):
    """Streams a PDF, automatically choosing between the fast native layer or the slow GPT-4o Vision OCR on a per-page basis."""
    import json
    
    pdf_doc = fitz.open(stream=content, filetype="pdf")
    total_pages = len(pdf_doc)
    
    # In Demo Mode, we process the first 20 pages (to bypass long front matter)
    limit = 20 if is_demo else total_pages
    actual_total = total_pages
    total_pages = limit
    
    yield json.dumps({"type": "status", "message": "Inhaling PDF document..."}) + "\n"
    
    sample_text = ""
    for i in range(min(10, total_pages)):
        sample_text += _get_page_content_purged(pdf_doc.load_page(i)).strip()
        
    if len(sample_text) > 150:
        yield json.dumps({"type": "status", "message": "Native text layer detected! Transcribing lightning fast!"}) + "\n"
        tail_buffer = ""
        for page_num in range(total_pages):
            page_content = _get_page_content_purged(pdf_doc.load_page(page_num)).strip()
            
            if not page_content:
                page_content = ""
            
            # Smart Join: If the previous page didn't end with punctuation, join!
            if tail_buffer:
                if _should_join_paragraphs(tail_buffer, page_content):
                    page_content = tail_buffer + " " + page_content
                else:
                    yield json.dumps({"type": "page", "page": page_num, "html": f"<p>{tail_buffer}</p>", "text": tail_buffer}) + "\n"
            
            # Split by ANY newline to evaluate every line as a potential paragraph
            paragraphs = [p.strip() for p in re.split(r'\n+', page_content) if p.strip()]
            
            if not paragraphs:
                tail_buffer = ""
                continue
                
            # Keep the last paragraph as a buffer for the next page
            tail_buffer = paragraphs.pop()
            
            if paragraphs:
                page_html = "".join([f"<h1>{p}</h1>" if _is_heading_candidate(p) else f"<p>{p}</p>" for p in paragraphs])
                yield json.dumps({
                    "type": "page",
                    "page": page_num + 1,
                    "total_pages": total_pages,
                    "html": page_html,
                    "text": "\n\n".join(paragraphs)
                }) + "\n"
        
        if tail_buffer:
            yield json.dumps({"type": "page", "page": total_pages, "html": f"<p>{tail_buffer}</p>", "text": tail_buffer}) + "\n"
            
    else:
        yield json.dumps({"type": "status", "message": "No text layer found. Booting Vision OCR stream..."}) + "\n"
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY", "")
            
        if not api_key:
            yield json.dumps({"type": "error", "message": "Missing OpenAI API Key for Vision Analysis."}) + "\n"
            return
            
        client = OpenAI(api_key=api_key)
        tail_buffer = ""
        for page_num in range(total_pages):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=90)
            img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": MANUSCRIPT_REDLINE_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                max_tokens=2500
            )
            
            # [SOVEREIGN ACCOUNTING]: Log OCR Vision usage
            from .ai_service import _log_api_usage
            metrics = {"total_tokens": response.usage.total_tokens}
            _log_api_usage(f"OCR Page {page_num+1}", "openai", "gpt-4o", metrics, folder_path)
            
            raw_text = response.choices[0].message.content
            text_match = re.search(r'<text>(.*?)</text>', raw_text, re.DOTALL)
            if text_match:
                page_content = text_match.group(1).strip()
                if "[BLANK_PAGE]" in page_content: page_content = ""
                
                # Fail-Safe: Split any headings the AI merged onto the same line
                page_content = _split_merged_headings(page_content)
                
                if tail_buffer:
                    if _should_join_paragraphs(tail_buffer, page_content):
                        page_content = tail_buffer + " " + page_content
                    else:
                        yield json.dumps({"type": "page", "page": page_num, "html": f"<p>{tail_buffer}</p>", "text": tail_buffer}) + "\n"

                # Split by ANY newline to evaluate every line as a potential paragraph
                paragraphs = [p.strip() for p in re.split(r'\n+', page_content) if p.strip()]
                
                if not paragraphs:
                    tail_buffer = ""
                    continue
                
                tail_buffer = paragraphs.pop()
                if paragraphs:
                    page_html = "".join([f"<h1>{p}</h1>" if _is_heading_candidate(p) else f"<p>{p}</p>" for p in paragraphs])
                    yield json.dumps({
                        "type": "page",
                        "page": page_num + 1,
                        "total_pages": total_pages,
                        "html": page_html,
                        "text": "\n\n".join(paragraphs)
                    }) + "\n"
        
        if tail_buffer:
            yield json.dumps({"type": "page", "page": total_pages, "html": f"<p>{tail_buffer}</p>", "text": tail_buffer}) + "\n"

    pdf_doc.close()
    yield json.dumps({"type": "done", "message": "Compilation complete!"}) + "\n"
