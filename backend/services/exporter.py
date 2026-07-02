import io
import html
import os
import json
from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from services import license_service
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, NextPageTemplate, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color, gray

# --- BETA PHASE PROTECTION ---
# Watermarking is active by default for all unactivated drafts
def get_protection_status():
    return not license_service.is_activated()

BETA_LABEL = "Tome-Master BETA - UNSUBMITTED DRAFT"
# -----------------------------

def add_toc_field(paragraph):
    """Injects a dynamic Microsoft Word Table of Contents field code."""
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText'); instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar2 = OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'), 'separate')
    fldChar3 = OxmlElement('w:fldChar'); fldChar3.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar1); run._r.append(instrText); run._r.append(fldChar2); run._r.append(fldChar3)


def _add_simple_field(paragraph, instruction: str, cached_text: str = ""):
    """Append a Word field (e.g. PAGE, STYLEREF) to a paragraph as a real field
    so Word recalculates it live. ``cached_text`` is the value shown before the
    field is recalculated (Word updates it on open via updateFields)."""
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve')
    instr.text = instruction
    sep = OxmlElement('w:fldChar'); sep.set(qn('w:fldCharType'), 'separate')
    cached = OxmlElement('w:t'); cached.set(qn('xml:space'), 'preserve'); cached.text = cached_text
    end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'), 'end')
    run._r.append(begin); run._r.append(instr); run._r.append(sep); run._r.append(cached); run._r.append(end)
    return run


def _set_update_fields_on_open(doc):
    """Set <w:updateFields w:val="true"/> in settings.xml so Word repaginates and
    populates every field (TOC, PAGE, STYLEREF) automatically when the file opens."""
    settings = doc.settings.element
    # Remove any existing to stay idempotent.
    for existing in settings.findall(qn('w:updateFields')):
        settings.remove(existing)
    upd = OxmlElement('w:updateFields')
    upd.set(qn('w:val'), 'true')
    settings.insert(0, upd)


def _start_new_section(doc, restart_numbering: bool = False, start_at: int = 1):
    """Begin a new Word section on a new page. When ``restart_numbering`` is set,
    the new section restarts the PAGE counter at ``start_at`` (used so the body
    starts at page 1 while the front matter carries no numbering at all)."""
    from docx.enum.section import WD_SECTION
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    sectPr = section._sectPr
    # add_section CLONES the previous section's properties — always drop any
    # inherited pgNumType so numbering only restarts when explicitly requested.
    for existing in sectPr.findall(qn('w:pgNumType')):
        sectPr.remove(existing)
    if restart_numbering:
        pgNumType = OxmlElement('w:pgNumType')
        pgNumType.set(qn('w:start'), str(start_at))
        sectPr.append(pgNumType)
    return section


def _clear_header_footer(section):
    """Unlink a section's header/footer from the previous section so we can give
    the front matter blank running heads while the body gets live fields."""
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    for p in list(section.header.paragraphs):
        p.clear()
    for p in list(section.footer.paragraphs):
        p.clear()


def _add_running_header_and_footer(section):
    """Body section running heads (industry standard):
      - top:  the current chapter title via STYLEREF "Heading 1" (auto per page)
      - bottom: the page number via PAGE field, centered."""
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    hp = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # STYLEREF \\* MERGEFORMAT pulls the nearest Heading 1 text onto every page.
    run = _add_simple_field(hp, 'STYLEREF "Heading 1" \\* MERGEFORMAT', "")
    run.italic = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    fp = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = _add_simple_field(fp, 'PAGE \\* MERGEFORMAT', "1")
    frun.font.size = Pt(10)


def _suppress_header_on_first_page(section):
    """Chapter-opener convention: the opening page shows NO running head (the
    big chapter heading is already on the page body) but keeps the centered
    folio; pages 2+ of the chapter inherit the STYLEREF running header."""
    section.different_first_page_header_footer = True
    # Materialise an explicitly blank first-page header so nothing is inherited.
    section.first_page_header.is_linked_to_previous = False
    for p in list(section.first_page_header.paragraphs):
        p.clear()
    # Keep the centered PAGE folio on the opener.
    section.first_page_footer.is_linked_to_previous = False
    fp = (section.first_page_footer.paragraphs[0]
          if section.first_page_footer.paragraphs else section.first_page_footer.add_paragraph())
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = _add_simple_field(fp, 'PAGE \\* MERGEFORMAT', "1")
    frun.font.size = Pt(10)

RED_SPELL = RGBColor(0xEF, 0x44, 0x44); BLUE_GRAMMAR = RGBColor(0x3B, 0x82, 0xF6)

def _decode_cover(cover_image: str):
    """Decode a base64 data-URL cover into (bytes, width_px, height_px).

    Returns None when no cover supplied. Raises on a malformed/undecodable
    image so the caller surfaces a real error (governance rule #4) rather than
    silently exporting a book with no cover.
    """
    if not cover_image:
        return None
    import base64
    if "," in cover_image:
        _, encoded = cover_image.split(",", 1)
    else:
        encoded = cover_image
    raw = base64.b64decode(encoded)
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        # Pillow couldn't read it — still hand back the bytes with a sane
        # default aspect so the cover at least embeds.
        w, h = (1000, 1500)
    return raw, w, h

# ─────────────────────────────────────────────────────────────────────────────
# INLINE PLATES / FIGURES
#
# Manuscript content can carry embedded images (plates, figures, photos). They
# arrive in the HTML as <img> tags whose ``src`` is (almost always) a base64
# ``data:`` URI inserted by the editor/import pipeline. Optionally wrapped in a
# <figure> with a <figcaption>, and/or carrying an ``alt`` attribute.
#
# These helpers decode an <img> to raw bytes + dimensions (reusing Pillow as the
# cover path does) and pull a human caption. Each exporter renders the plate IN
# PLACE (preserving prose order) with the caption/alt preserved. A single bad
# plate is surfaced inline (governance rule #4 — never silently dropped) but
# never aborts the whole export.
# ─────────────────────────────────────────────────────────────────────────────

class PlateError(Exception):
    """A specific <img> could not be decoded. Carries the failure reason so the
    exporter can surface it inline rather than silently dropping the plate."""


def _decode_data_uri_image(src: str):
    """Decode an <img src> data-URI into (bytes, ext, width_px, height_px).

    ``ext`` is the lowercase image subtype suitable for python-docx / a filename
    ('jpeg', 'png', 'gif', …). Raises PlateError on anything we cannot embed
    (non-data URI such as an external http link, undecodable base64, or bytes
    Pillow cannot open) so the caller surfaces a real, specific error.
    """
    import base64
    if not src:
        raise PlateError("image has no src")
    s = src.strip()
    if not s.lower().startswith("data:"):
        # An external/relative reference can't be embedded into a self-contained
        # export — be explicit rather than emitting a broken link.
        raise PlateError(f"unsupported image src (not a data URI): {s[:60]}")
    # data:[<mediatype>][;base64],<data>
    header, _, encoded = s.partition(",")
    if not encoded:
        raise PlateError("data URI has no payload")
    ext = "png"
    if ":" in header and "/" in header:
        mediatype = header[header.index(":") + 1:].split(";")[0]
        if "/" in mediatype:
            ext = mediatype.split("/", 1)[1].strip().lower() or "png"
    is_b64 = "base64" in header.lower()
    try:
        if is_b64:
            raw = base64.b64decode(encoded)
        else:
            from urllib.parse import unquote_to_bytes
            raw = unquote_to_bytes(encoded)
    except Exception as e:
        raise PlateError(f"could not decode image data ({e})")
    if not raw:
        raise PlateError("image decoded to zero bytes")
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(io.BytesIO(raw)) as im:
            w, h = im.size
            fmt = (im.format or "").lower()
            if fmt:
                ext = "jpeg" if fmt == "jpg" else fmt
    except Exception as e:
        raise PlateError(f"image bytes are not a readable image ({e})")
    # Normalise the common alias.
    if ext == "jpg":
        ext = "jpeg"
    return raw, ext, w, h


def _image_caption(img_tag) -> str:
    """Human caption for an <img>: the wrapping <figure>'s <figcaption> if any,
    else the img ``alt`` / ``title``. Returns '' when none. Exact wording kept."""
    fig = img_tag.find_parent("figure")
    if fig is not None:
        cap = fig.find("figcaption")
        if cap is not None:
            t = cap.get_text().replace('​', '').replace('\xa0', ' ').strip()
            if t:
                return t
    for attr in ("alt", "title"):
        v = (img_tag.get(attr) or "").replace('​', '').replace('\xa0', ' ').strip()
        if v:
            return v
    return ""


def _block_images(node):
    """Images carried by a block node, in document order. A <figure>/<p> may wrap
    one or more <img>; a bare <img> block returns itself."""
    if getattr(node, "name", None) == "img":
        return [node]
    if hasattr(node, "find_all"):
        return node.find_all("img")
    return []


def _block_has_only_images(node) -> bool:
    """True when a block should be rendered purely as plate(s): a bare <img>, a
    <figure> (its text is the caption, owned by the plate), or any block whose
    only non-whitespace content is image(s)."""
    name = getattr(node, "name", None)
    if name == "img":
        return True
    if not _block_images(node):
        return False
    if name == "figure":
        return True
    text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
    return not text


def _strip_frontmatter_blocks(soup, title, author):
    """Remove the manuscript's own leading title/author block from the body so
    it is not duplicated under the generated title page. Conservative: only
    drops leading blocks that look like a title page (matching the supplied
    title/author, a bare 'by' line, or 'title page' label) before the first
    real chapter heading or body paragraph run.
    """
    title_l = (title or "").strip().lower()
    author_l = (author or "").strip().lower()
    removed = 0
    for node in list(soup.find_all(['h1', 'h2', 'h3', 'p', 'div'])):
        if not getattr(node, 'name', None) or not node.parent:
            continue
        # Never touch the TOC placeholder marker injected by _strip_toc.
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            node.decompose()
            continue
        t_lower = text.lower()
        is_title = title_l and t_lower == title_l
        is_author = author_l and (t_lower == author_l or t_lower == f"by {author_l}".strip())
        is_by_line = t_lower in ('by', 'by:', 'by-') or t_lower.startswith('by ')
        is_label = t_lower in ('title page', 'titlepage')
        if removed < 4 and (is_title or is_author or is_by_line or is_label):
            node.decompose()
            removed += 1
            continue
        # First block that is not part of the title page → stop scanning.
        break

def _add_inline_runs(p_obj, node, is_bold=False, is_italic=False):
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if not text: continue
            run = p_obj.add_run(text); run.bold = is_bold; run.italic = is_italic
        elif isinstance(child, Tag):
            classes = child.get('class') or []
            if 'misspelled-word' in classes:
                run = p_obj.add_run(child.get_text()); run.bold = is_bold; run.italic = is_italic; run.underline = True; run.font.color.rgb = RED_SPELL
            elif 'grammar-squiggle' in classes:
                run = p_obj.add_run(child.get_text()); run.bold = is_bold; run.italic = is_italic; run.underline = True; run.font.color.rgb = BLUE_GRAMMAR
            elif child.name in ('strong', 'b'): _add_inline_runs(p_obj, child, is_bold=True, is_italic=is_italic)
            elif child.name in ('em', 'i'): _add_inline_runs(p_obj, child, is_bold=is_bold, is_italic=True)
            else: _add_inline_runs(p_obj, child, is_bold=is_bold, is_italic=is_italic)

_BLOCK_TAGS = ['h1', 'h2', 'h3', 'p', 'div', 'figure', 'img']


def _is_nested_block(node) -> bool:
    """True when ``node`` is a block-tag whose rendering is already owned by an
    ancestor block we also iterate (so we don't render it twice). e.g. an <img>
    inside a <figure> or <p>, or a <p> inside a <div> we already emit."""
    parent = node.parent
    while parent is not None and getattr(parent, "name", None):
        if parent.name in ('p', 'figure'):
            return True
        # An <img>/<figure> nested under any other block is owned by that block's
        # image rendering; skip the standalone visit.
        if node.name in ('img', 'figure') and parent.name in ('div', 'h1', 'h2', 'h3'):
            return True
        parent = parent.parent
    return False


def _strip_toc(soup):
    toc_div = soup.find('div', class_='editor-toc')
    if toc_div: toc_div.decompose()
    
    found_manual = False
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'b', 'strong']):
        if not tag.parent: continue
        text = tag.get_text().replace('\u200b', '').strip().lower()
        if text in ["table of contents", "contents"]:
            found_manual = True
            placeholder = soup.new_tag('div', id='toc-placeholder')
            tag.insert_before(placeholder)
            
            curr = tag.next_sibling
            while curr:
                next_node = curr.next_sibling
                if getattr(curr, 'name', None) in ['h1', 'h2', 'h3'] and curr.get_text().strip(): break
                curr_text = curr.get_text().replace('\u200b', '').strip().lower() if hasattr(curr, 'get_text') else ""
                if curr_text and (curr_text.startswith('chapter ') or curr_text in ['prologue', 'epilogue']): break
                if hasattr(curr, 'decompose'): curr.decompose()
                curr = next_node
            tag.decompose()
            break
            
    if not found_manual:
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            t = tag.get_text().replace('\u200b', '').lower()
            if any(x in t for x in ['chapter', 'prologue', 'part 1', 'epilogue']):
                placeholder = soup.new_tag('div', id='toc-placeholder')
                tag.insert_before(placeholder)
                found_manual = True
                break
        if not found_manual:
            placeholder = soup.new_tag('div', id='toc-placeholder')
            soup.insert(0, placeholder)

def _extract_frontmatter(soup, default_title, default_author):
    title = default_title
    author = default_author
    
    blocks = soup.find_all(['h1', 'h2', 'h3', 'p', 'div'])
    
    found_title = False
    for node in blocks[:20]:
        if not getattr(node, 'name', None): continue
            
        text = node.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
        if not text: continue
            
        if not found_title:
            title = text
            found_title = True
            node.decompose()
        else:
            t_lower = text.lower()
            if t_lower in ['by', 'by:', 'by-'] or t_lower.startswith('by ') or node.name in ['h2', 'h3'] or len(text.split()) <= 5:
                author = text
                curr = node.next_sibling # Get pointer BEFORE destroying the node
                node.decompose()
                
                if t_lower in ['by', 'by:', 'by-']:
                    while curr:
                        next_curr = curr.next_sibling
                        if getattr(curr, 'name', None) in ['p', 'h1', 'h2', 'h3', 'div']:
                            n_text = curr.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
                            if n_text:
                                author += " " + n_text
                                curr.decompose()
                                break
                            else:
                                curr.decompose()
                        curr = next_curr
            break
            
    return title, author

def _add_docx_beta_watermark(doc):
    """Adds a prominent Beta watermark disclaimer to the header of every section."""
    if not get_protection_status(): return

    def _stamp(hdr):
        # Append as a SEPARATE paragraph so we never overwrite a STYLEREF field
        # paragraph that may already occupy header.paragraphs[0].
        p = hdr.add_paragraph()
        run = p.add_run(f"--- {BETA_LABEL} ---")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(128, 128, 128)

    for section in doc.sections:
        # Sections whose header is linked-to-previous INHERIT an earlier
        # (already stamped) header — unlinking them here would strip the
        # inherited STYLEREF running head, so leave those alone.
        if not section.header.is_linked_to_previous:
            _stamp(section.header)
        # Chapter openers carry their own (blank) first-page header — stamp it
        # too so the watermark appears on every page.
        if (section.different_first_page_header_footer
                and not section.first_page_header.is_linked_to_previous):
            _stamp(section.first_page_header)

def _add_docx_plate(doc, img_tag):
    """Embed one inline plate <img> into the DOCX in place: picture centered and
    fit to the printable width (6.5" within 1" margins), with a caption line under
    it. A malformed plate becomes a visible inline note (never silently dropped)."""
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        raw, _ext, w, h = _decode_data_uri_image(src)
    except PlateError as e:
        note = doc.add_paragraph()
        note.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = note.add_run(f"[Plate could not be embedded: {e}]")
        r.italic = True
        r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        return
    avail_w = Inches(6.5)
    aspect = (h / w) if w else 1.0
    width = avail_w
    height = Inches(6.5 * aspect)
    max_h = Inches(8.0)
    if height > max_h:
        height = max_h
        width = Inches(8.0 / aspect) if aspect else avail_w
    pic_p = doc.add_paragraph()
    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_p.add_run().add_picture(io.BytesIO(raw), width=width, height=height)
    if caption:
        cap_p = doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cr = cap_p.add_run(caption)
        cr.italic = True
        cr.font.size = Pt(10)


# ─────────────────────────────────────────────────────────────────────────────
# SUBMISSION PRESET — William Shunn Standard Manuscript Format
# (https://www.shunn.net/format/story/)
#
# A dedicated DOCX layout for agent/editor submissions: Times New Roman 12pt,
# double-spaced, 1" margins, 0.5" first-line indent, ragged right (left-
# aligned), NO inter-paragraph spacing, no cover, no title-page section, no
# Contents page. Page 1 carries the contact block (author name, top-left) and
# the approximate word count (top-right); the title + byline sit roughly a
# third of the way down. Pages 2+ carry a top-right running header
# "Lastname / TITLE / page#". Chapters open on a fresh page about a third of
# the way down; scene breaks render as a centered "#". Modern Shunn: italics
# stay italics (no underlining).
# ─────────────────────────────────────────────────────────────────────────────

def _approximate_word_count(content: str) -> int:
    """Approximate manuscript word count from the plain text of the HTML
    content, rounded to the nearest 500 (Shunn: "about 85,000 words"). When
    rounding to 500 would collapse a short piece to zero, the exact count is
    returned instead (an honest number beats a fabricated zero)."""
    text = BeautifulSoup(content, 'html.parser').get_text()
    n = len(text.split())
    rounded = int(round(n / 500.0)) * 500
    return rounded if rounded > 0 else n


def _generate_docx_submission(content: str, chapters: list, title: str, author: str) -> io.BytesIO:
    """Render the manuscript in Shunn Standard Manuscript Format (see the
    preset banner above). ``cover_image`` is deliberately not accepted —
    submission manuscripts are plain typescript pages."""
    from docx.enum.text import WD_TAB_ALIGNMENT

    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Inches(1)

    # Normal style: TNR 12, double-spaced, ragged right, zero paragraph spacing.
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    pf = style_normal.paragraph_format
    pf.line_spacing = 2.0
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    # ── Page 1: contact block (author name, top-left) + word count (top-right)
    #    on the same line via a right tab stop at the right margin. ──
    head_p = doc.add_paragraph()
    head_p.paragraph_format.line_spacing = 1.0
    head_p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    head_p.add_run(author_text)
    head_p.add_run(f"\tabout {_approximate_word_count(content):,} words")

    # ── Title + byline, centered roughly a third of the way down page 1
    #    (5 empty double-spaced lines ≈ 3" of the 9" text block). ──
    for _ in range(5):
        doc.add_paragraph()
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.add_run(title_text)
    if author_text:
        bp = doc.add_paragraph()
        bp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        bp.add_run(f"by {author_text}")

    # ── Running header, pages 2+ only (different-first-page suppresses it on
    #    page 1): "Lastname / TITLE / page#", top-right, live PAGE field. ──
    section.different_first_page_header_footer = True
    # Materialise an explicitly blank first-page header so page 1 stays clean.
    section.first_page_header.is_linked_to_previous = False
    hp = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    lastname = author_text.split()[-1] if author_text.split() else ""
    slug = " / ".join(part for part in (lastname, title_text.upper()) if part)
    hp.add_run(f"{slug} / ")
    _add_simple_field(hp, 'PAGE \\* MERGEFORMAT', "2")

    # ── Body ──
    soup = BeautifulSoup(content, 'html.parser')
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)

    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            # A submission manuscript carries no Contents page.
            continue
        if _is_nested_block(node):
            continue

        # Standalone plate block: still embedded (never silently dropped).
        if _block_has_only_images(node):
            for img in _block_images(node):
                _add_docx_plate(doc, img)
            continue

        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            continue

        if node.name in ['h1', 'h2', 'h3']:
            # Every chapter opens on a fresh page (page 1 always holds the
            # title block), heading centered about a third of the way down.
            doc.add_page_break()
            for _ in range(4):
                doc.add_paragraph()
            hpara = doc.add_paragraph()
            hpara.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hpara.add_run(text)
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                doc.add_paragraph('#').alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue
            p_obj = doc.add_paragraph()
            p_obj.paragraph_format.first_line_indent = Inches(0.5)
            _add_inline_runs(p_obj, node)
            for img in _block_images(node):
                _add_docx_plate(doc, img)

    _add_docx_beta_watermark(doc)
    _set_update_fields_on_open(doc)

    file_stream = io.BytesIO(); doc.save(file_stream); file_stream.seek(0); return file_stream


def generate_docx(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    if output_format == 'submission':
        # Shunn Standard Manuscript Format is a wholly different page layout
        # (no cover, no title-page section, no TOC) — dispatch to its own
        # renderer so the chicago/penguin paths below stay untouched.
        return _generate_docx_submission(content, chapters, title, author)
    doc = Document()

    for section in doc.sections:
        section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Inches(1)

    # ===== FRONT MATTER (section 0): cover + title page. No page numbers, no running header. =====
    # --- Cover image: sized to fill the page within margins (US Letter, 1" margins → 6.5" x 9") ---
    cover = _decode_cover(cover_image)
    if cover:
        img_data, cw, ch = cover
        page_w = Inches(6.5)
        page_h = Inches(9.0)
        # Fit the image inside the printable area, preserving aspect ratio.
        aspect = (ch / cw) if cw else 1.5
        width = page_w
        height = Inches(6.5 * aspect)
        if height > page_h:
            height = page_h
            width = Inches(9.0 / aspect) if aspect else page_h
        cover_p = doc.add_paragraph()
        cover_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cover_p.add_run().add_picture(io.BytesIO(img_data), width=width, height=height)
        doc.add_page_break()

    # --- Title page: ALWAYS rendered (never suppressed) ---
    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = tp.add_run(title_text)
    tr.bold = True
    tr.font.size = Pt(28)
    if author_text:
        doc.add_paragraph()
        ap = doc.add_paragraph()
        ap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        arun = ap.add_run(f"by {author_text}")
        arun.font.size = Pt(16)

    style_normal = doc.styles['Normal']; font = style_normal.font
    font.name = 'Garamond' if output_format == 'penguin' else 'Times New Roman'
    font.size = Pt(12)
    style_normal.paragraph_format.line_spacing = 1.5 if output_format == 'penguin' else 2.0
    style_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for i in range(1, 4):
        style_name = f'TOC {i}'
        if style_name in doc.styles:
            s = doc.styles[style_name]; s.font.name = font.name; s.font.size = Pt(12); s.paragraph_format.line_spacing = style_normal.paragraph_format.line_spacing

    soup = BeautifulSoup(content, 'html.parser')
    _strip_toc(soup)
    # Drop the manuscript's own leading title/author block so it isn't duplicated
    # below the generated title page.
    _strip_frontmatter_blocks(soup, title, author)

    # --- Native, live Table of Contents as the last front-matter page (unnumbered) ---
    doc.add_page_break()
    toc_heading = doc.add_paragraph()
    toc_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    th = toc_heading.add_run("Contents"); th.bold = True; th.font.size = Pt(18)
    doc.add_paragraph(
        "This table updates automatically. If it appears empty, click it and press F9 "
        "(or right-click \u2192 Update Field)."
    ).runs[0].italic = True
    add_toc_field(doc.add_paragraph())

    # The front-matter section (section 0) carries blank header/footer = unnumbered.
    _clear_header_footer(doc.sections[0])

    # ===== BODY (new section): page numbering restarts at 1; running header + footer =====
    body_section = _start_new_section(doc, restart_numbering=True, start_at=1)
    body_section.top_margin = body_section.bottom_margin = Inches(1)
    body_section.left_margin = body_section.right_margin = Inches(1)
    _add_running_header_and_footer(body_section)
    # The body's first page is the first chapter's opener — no running head there.
    _suppress_header_on_first_page(body_section)

    has_content = False
    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            # TOC already rendered in the front matter; skip the inline placeholder.
            continue
        if _is_nested_block(node):
            continue

        # Standalone image block (bare <img> or a <figure>/<div> whose only
        # content is plates): render the plate(s) in place.
        if _block_has_only_images(node):
            for img in _block_images(node):
                _add_docx_plate(doc, img)
                has_content = True
            continue

        text = node.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
        if not text: continue

        if node.name in ['h1', 'h2', 'h3']:
            if has_content:
                # Each chapter opens its own section (new page) so its FIRST
                # page suppresses the running head; the default header/footer
                # stay linked-to-previous and inherit STYLEREF + PAGE.
                ch_section = _start_new_section(doc)
                ch_section.top_margin = ch_section.bottom_margin = Inches(1)
                ch_section.left_margin = ch_section.right_margin = Inches(1)
                _suppress_header_on_first_page(ch_section)
            doc.add_heading(text, level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
            has_content = True
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                doc.add_paragraph('#').alignment = WD_ALIGN_PARAGRAPH.CENTER
                has_content = True
                continue
            p_obj = doc.add_paragraph(); p_obj.paragraph_format.first_line_indent = Inches(0.5); _add_inline_runs(p_obj, node)
            has_content = True
            # A <p> can carry both prose and an inline plate; render any images
            # immediately after the paragraph so order is preserved.
            for img in _block_images(node):
                _add_docx_plate(doc, img)

    # Beta watermark: appended as an EXTRA header paragraph per section so it never
    # clobbers the STYLEREF running header or PAGE footer fields.
    _add_docx_beta_watermark(doc)

    # Tell Word to recompute TOC / PAGE / STYLEREF fields the moment the file opens.
    _set_update_fields_on_open(doc)

    file_stream = io.BytesIO(); doc.save(file_stream); file_stream.seek(0); return file_stream

def generate_analysis_docx(markdown_text: str) -> io.BytesIO:
    doc = Document()
    _add_docx_beta_watermark(doc)
    for s in doc.sections: s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
    doc.add_heading("tome_master AI Boardroom Report", 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        if line.startswith('# '): doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith('## '): doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith('### '): doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith(('- ', '* ')):
            p = doc.add_paragraph(style='List Bullet'); p.add_run(line[2:].strip().replace('**', ''))
        elif line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) > 2:
                # Filter out empty strings from split and ignore decorative separator lines
                headers = [val.strip() for val in table_lines[0].split('|') if val.strip()]
                if not headers: continue
                
                table = doc.add_table(rows=1, cols=len(headers), style='Table Grid')
                hdr_cells = table.rows[0].cells
                for idx, hdr in enumerate(headers):
                    hdr_cells[idx].text = hdr
                
                # Make headers repeat on each page for context
                tr = table.rows[0]._tr
                trPr = tr.get_or_add_trPr()
                tblHeader = OxmlElement('w:tblHeader')
                trPr.append(tblHeader)
                
                for r_idx, row_line in enumerate(table_lines):
                    # Skip header line (0) and alignment separator lines (1)
                    if r_idx <= 1:
                        continue
                    
                    row_data = [val.strip() for val in row_line.split('|') if val.strip()]
                    if len(row_data) > 0:
                        row_cells = table.add_row().cells
                        # Ensure we don't exceed header count but fill what we have
                        for idx, val in enumerate(row_data[:len(headers)]):
                            row_cells[idx].text = val
            continue
        else:
            p = doc.add_paragraph(); p.add_run(line.replace('**', '')); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        i += 1
        
    file_stream = io.BytesIO(); doc.save(file_stream); file_stream.seek(0); return file_stream

TRADE_PAPERBACK = (6 * inch, 9 * inch)

def to_roman(num):
    lookup = [(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')]
    r = ''; 
    for v, n in lookup:
        while num >= v: r += n; num -= v
    return r or 'i'

class ResetPageFlowable(Flowable):
    def wrap(self, w, h): return (0, 0)
    def draw(self): self.canv._pageNumber = 0

class BookmarkFlowable(Flowable):
    """Zero-height flowable that registers a named PDF destination + outline
    entry at its position, so the chapter heading is reachable from the reader's
    bookmark panel and from clickable TOC links (href="#key"). It also notifies
    the doc template so the two-pass TOC records this chapter's real page number,
    and updates the running header to show this chapter's title."""
    def __init__(self, key, title, level=0):
        Flowable.__init__(self)
        self.key = key; self.title = title; self.level = level
    def wrap(self, w, h): return (0, 0)
    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=False)
        dt = self.canv._doctemplate
        # Body-relative page number so the TOC matches the printed footer numbers
        # (the body starts at 1; cover/title/Contents are unnumbered).
        abs_page = self.canv.getPageNumber()
        body_start = getattr(dt, 'body_start_page', None)
        display_page = abs_page - body_start + 1 if body_start else abs_page
        # Feed ReportLab's TableOfContents (two-pass): (level, text, pageNum, key).
        dt.notify('TOCEntry', (self.level, self.title, display_page, self.key))
        # Record the chapter title so the running header reflects it, and the
        # page it opened on so the opener page draws NO running head (the big
        # chapter heading is already on that page).
        dt.current_chapter = self.title
        dt.chapter_open_page = abs_page

def draw_watermark(canvas, doc):
    if not get_protection_status(): return
    canvas.saveState()
    canvas.setFont('Times-Bold', 60)
    canvas.setFillAlpha(0.15)
    canvas.setStrokeColor(gray)
    canvas.translate(TRADE_PAPERBACK[0]/2, TRADE_PAPERBACK[1]/2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, BETA_LABEL)
    canvas.restoreState()


class BodyStartFlowable(Flowable):
    """Zero-height marker recording the absolute page on which the body begins,
    so footer page numbers can be displayed as 1..N (body) while the cover,
    title page and Contents stay UNNUMBERED."""
    def wrap(self, w, h): return (0, 0)
    def draw(self):
        dt = self.canv._doctemplate
        if getattr(dt, 'body_start_page', None) is None:
            dt.body_start_page = self.canv.getPageNumber()


class ManuscriptDocTemplate(BaseDocTemplate):
    """Two-pass template: ``multiBuild`` reruns until the TOC page numbers are
    stable. Tracks the running-chapter title and the body's first page so the
    onPage callback can draw the chapter running header + centered footer page
    number on body pages only (front matter unnumbered)."""
    def __init__(self, *args, **kwargs):
        BaseDocTemplate.__init__(self, *args, **kwargs)
        self.current_chapter = ""
        self.body_start_page = None
        self.chapter_open_page = None


def _append_pdf_plate(story, img_tag, avail_w, avail_h, cap_style):
    """Append one inline plate to the PDF story: a ReportLab Image scaled to the
    frame (aspect-preserved; a large/full-page plate is fine) with a caption
    under it. A malformed plate becomes a visible inline note (never dropped)."""
    from reportlab.platypus import Image, Spacer
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        raw, _ext, w, h = _decode_data_uri_image(src)
    except PlateError as e:
        story.append(Paragraph(html.escape(f"[Plate could not be embedded: {e}]"), cap_style))
        return
    aspect = (h / w) if w else 1.0
    iw = avail_w
    ih = avail_w * aspect
    if ih > avail_h:
        ih = avail_h
        iw = avail_h / aspect if aspect else avail_w
    story.append(Spacer(1, 0.15 * inch))
    story.append(Image(io.BytesIO(raw), width=iw, height=ih))
    if caption:
        story.append(Paragraph(html.escape(caption), cap_style))
    story.append(Spacer(1, 0.15 * inch))


def generate_pdf(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    from reportlab.platypus import Image
    from reportlab.platypus.tableofcontents import TableOfContents

    file_stream = io.BytesIO(); margin = 0.75 * inch; gutter = 0.25 * inch
    frame = Frame(margin + gutter, margin, TRADE_PAPERBACK[0] - 2*margin - gutter, TRADE_PAPERBACK[1] - 2*margin, id='normal')

    def draw_frontmatter(canvas, doc):
        """Cover / title / Contents pages: watermark only, NO page number, NO header."""
        draw_watermark(canvas, doc)

    def draw_body(canvas, doc):
        draw_watermark(canvas, doc)
        canvas.saveState()
        # Running header: current chapter title, centered at the top — but NOT
        # on the chapter's opening page, where the heading is already in the body.
        if doc.current_chapter and canvas.getPageNumber() != doc.chapter_open_page:
            canvas.setFont('Times-Italic', 9)
            canvas.setFillColor(gray)
            canvas.drawCentredString(TRADE_PAPERBACK[0] / 2.0, TRADE_PAPERBACK[1] - margin / 1.5, doc.current_chapter)
        # Centered footer page number, body-relative (1..N). Front matter excluded.
        canvas.setFillColor(Color(0, 0, 0))
        canvas.setFont('Times-Roman', 10)
        if doc.body_start_page is not None:
            display = canvas.getPageNumber() - doc.body_start_page + 1
            if display >= 1:
                canvas.drawCentredString(TRADE_PAPERBACK[0] / 2.0, margin / 2.0, str(display))
        canvas.restoreState()

    doc = ManuscriptDocTemplate(file_stream, pagesize=TRADE_PAPERBACK)
    # Draw header/footer at page END so doc.current_chapter reflects the chapter
    # whose heading actually drew on this page (onPageBegin would lag by one page).
    doc.addPageTemplates([
        PageTemplate(id='FrontMatter', frames=frame, onPageEnd=draw_frontmatter),
        PageTemplate(id='Narrative', frames=frame, onPageEnd=draw_body),
    ])
    styles = getSampleStyleSheet()

    leading_val = 15 if output_format == "penguin" else 22
    style_n = ParagraphStyle('CM_N', parent=styles['Normal'], fontName='Times-Roman', fontSize=11, leading=leading_val, firstLineIndent=0.3*inch, alignment=TA_JUSTIFY)
    style_f = ParagraphStyle('CM_F', parent=style_n, firstLineIndent=0)
    style_t = ParagraphStyle('CM_T', parent=styles['Heading1'], fontName='Times-Bold', fontSize=28, leading=34, alignment=TA_CENTER, spaceBefore=2.5*inch, spaceAfter=0.4*inch)
    style_by = ParagraphStyle('CM_BY', parent=styles['Normal'], fontName='Times-Roman', fontSize=15, leading=20, alignment=TA_CENTER)
    style_c = ParagraphStyle('CM_C', parent=styles['Heading2'], fontName='Times-Bold', fontSize=16, leading=20, alignment=TA_CENTER, spaceBefore=1.5*inch, spaceAfter=0.5*inch)
    style_cap = ParagraphStyle('CM_CAP', parent=styles['Normal'], fontName='Times-Italic', fontSize=9, leading=12, alignment=TA_CENTER, spaceBefore=4)

    # Printable plate area = frame interior (keeps a full-page plate inside margins).
    plate_w = TRADE_PAPERBACK[0] - 2 * margin - gutter
    plate_h = TRADE_PAPERBACK[1] - 2 * margin

    story = []

    # --- Cover: full printable area, aspect-preserved ---
    cover = _decode_cover(cover_image)
    if cover:
        img_data, cw, ch = cover
        avail_w = TRADE_PAPERBACK[0] - 2 * margin
        avail_h = TRADE_PAPERBACK[1] - 2 * margin
        aspect = (ch / cw) if cw else 1.5
        iw = avail_w
        ih = avail_w * aspect
        if ih > avail_h:
            ih = avail_h
            iw = avail_h / aspect if aspect else avail_w
        img = Image(io.BytesIO(img_data), width=iw, height=ih)
        story.append(img)
        story.append(PageBreak())

    # --- Title page: ALWAYS rendered (never suppressed) ---
    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()
    story.append(Paragraph(html.escape(title_text), style_t))
    if author_text:
        story.append(Paragraph(f"by {html.escape(author_text)}", style_by))
    story.append(PageBreak())

    soup = BeautifulSoup(content, 'html.parser')
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)

    # Collect chapter headings (in body order) so each TOC entry links to the very
    # anchor we register at its heading.
    heading_nodes = []
    for node in soup.find_all(['h1', 'h2', 'h3']):
        t = node.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
        if t:
            heading_nodes.append(node)
    heading_keys = {id(n): f"chap_{i}" for i, n in enumerate(heading_nodes)}

    # ReportLab's two-pass Table of Contents: collects (level, title, page, key)
    # notifications during the build and renders real page numbers + dot leaders +
    # clickable links. multiBuild reruns until the numbers are stable.
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle('TOCEntry', fontName='Times-Roman', fontSize=12, leading=20,
                       firstLineIndent=0, leftIndent=0, rightIndent=0.2 * inch),
    ]

    found_n = False
    has_content = False
    for i, node in enumerate(soup.find_all(_BLOCK_TAGS)):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            if heading_nodes:
                if has_content: story.append(PageBreak())
                story.append(Paragraph("Contents", style_c))
                story.append(toc)
                has_content = True
            continue
        if _is_nested_block(node):
            continue

        # Standalone plate block (bare <img>/<figure>): render the plate(s) here.
        if _block_has_only_images(node):
            for img in _block_images(node):
                _append_pdf_plate(story, img, plate_w, plate_h, style_cap)
                has_content = True
            continue

        text = node.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
        if not text: continue

        if node.name in ['h1', 'h2', 'h3']:
            if has_content:
                # First chapter: switch to the numbered body template and mark the
                # body's first page (so footer numbering starts at 1 here).
                if not found_n and any(x in text.lower() for x in ['chapter', 'prologue', 'part 1']):
                    story.append(NextPageTemplate('Narrative')); story.append(PageBreak()); story.append(BodyStartFlowable()); found_n = True
                else: story.append(PageBreak())
            elif not found_n:
                # No front matter preceded the first heading: start the body here.
                story.append(NextPageTemplate('Narrative')); story.append(BodyStartFlowable()); found_n = True
            key = heading_keys.get(id(node))
            if key:
                story.append(BookmarkFlowable(key, text, level=0))
            story.append(Paragraph(f'{html.escape(text)}', style_c))
            has_content = True
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                story.append(Spacer(1, 0.3*inch)); story.append(Paragraph('#', ParagraphStyle('SB', parent=style_n, alignment=TA_CENTER))); story.append(Spacer(1, 0.3*inch))
                has_content = True
                continue
            story.append(Paragraph(_node_to_reportlab_markup(node), style_n))
            has_content = True
            # Inline plate(s) within a prose paragraph: render right after it.
            for img in _block_images(node):
                _append_pdf_plate(story, img, plate_w, plate_h, style_cap)

    doc.multiBuild(story); file_stream.seek(0); return file_stream

def _node_to_reportlab_markup(node) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString): parts.append(html.escape(str(child)))
        elif isinstance(child, Tag):
            classes = child.get('class') or []; inner = _node_to_reportlab_markup(child)
            if 'misspelled-word' in classes: parts.append(f'<u><font color="#ef4444">{inner}</font></u>')
            elif 'grammar-squiggle' in classes: parts.append(f'<u><font color="#3b82f6">{inner}</font></u>')
            elif child.name in ('strong', 'b'): parts.append(f'<b>{inner}</b>')
            elif child.name in ('em', 'i'): parts.append(f'<i>{inner}</i>')
            else: parts.append(inner)
    return ''.join(parts)

import tempfile
import uuid
from ebooklib import epub

def generate_epub(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    book = epub.EpubBook()
    
    cover = _decode_cover(cover_image)
    if cover:
        img_data, _cw, _ch = cover
        # set_cover marks the image as the EPUB cover (dc cover meta + manifest
        # properties="cover-image") so e-readers display it as the book cover.
        book.set_cover("cover.jpg", img_data, create_page=True)

    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)
    
    style = 'body { font-family: "Times New Roman", Times, serif; line-height: 2.0; } h1, h2, h3 { text-align: center; } p { text-align: justify; text-indent: 1.5em; margin-top: 0; margin-bottom: 0; }'
    if output_format == "penguin":
        style = 'body { font-family: "Garamond", "Palatino Linotype", serif; line-height: 1.5; } h1, h2, h3 { text-align: center; } p { text-align: justify; text-indent: 1.5em; margin-top: 0; margin-bottom: 0; }'
    default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style)
    book.add_item(default_css)
    
    soup = BeautifulSoup(content, 'html.parser')
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)

    # --- Title page (after cover) ---
    title_text = (title or "").strip()
    author_text = (author or "").strip()
    title_page = None
    if title_text and title_text.lower() not in ("manuscript", "manuscript title"):
        by_line = ""
        if author_text and author_text.lower() not in ("author", "author name"):
            by_line = f'<p style="text-align: center; text-indent: 0; font-size: 1.2em;">by {html.escape(author_text)}</p>'
        title_page = epub.EpubHtml(title=title_text, file_name='title_page.xhtml', lang='en')
        title_page.content = (
            '<html><head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>'
            '<body><div style="margin-top: 30%; text-align: center;">'
            f'<h1 style="text-align: center; font-size: 2em;">{html.escape(title_text)}</h1>'
            f'{by_line}</div></body></html>'
        )
        title_page.add_item(default_css)
        book.add_item(title_page)

    # Inline plates: each <img> becomes an EpubImage resource referenced from the
    # chapter XHTML so e-readers actually render it. ``_plate_counter`` keeps the
    # filenames unique; ``_emit_epub_plate`` returns the XHTML to insert in place.
    _plate_counter = {"n": 0}

    def _emit_epub_plate(img_tag) -> str:
        src = img_tag.get("src") or ""
        caption = _image_caption(img_tag)
        try:
            raw, ext, _w, _h = _decode_data_uri_image(src)
        except PlateError as e:
            return f'<p style="text-align:center; color:#999;"><em>[Plate could not be embedded: {html.escape(str(e))}]</em></p>'
        _plate_counter["n"] += 1
        fname = f"images/plate_{_plate_counter['n']}.{ext}"
        item = epub.EpubImage(
            uid=f"plate_{_plate_counter['n']}",
            file_name=fname,
            media_type=f"image/{ext}",
            content=raw,
        )
        book.add_item(item)
        cap_html = (f'<figcaption style="text-align:center; font-style:italic; font-size:0.9em;">'
                    f'{html.escape(caption)}</figcaption>') if caption else ""
        alt = html.escape(caption) if caption else "Plate"
        return (f'<figure style="text-align:center; margin:1.5em 0;">'
                f'<img src="{fname}" alt="{alt}" style="max-width:100%; height:auto;"/>'
                f'{cap_html}</figure>')

    sections = []
    current_chapter_title = "Front Matter"
    current_html_blocks = []

    if get_protection_status():
        current_html_blocks.append(f'<div style="border: 2px solid #666; padding: 2em; margin: 2em; text-align: center; border-radius: 10px;">')
        current_html_blocks.append(f'<h1 style="color: #666;">BETA ACCESS NOTICE</h1>')
        current_html_blocks.append(f'<p style="text-align: center; text-indent: 0;">This digital proof was generated during the <strong>tome_master Beta Phase</strong>.</p>')
        current_html_blocks.append(f'<p style="text-align: center; text-indent: 0; color: #ef4444; font-weight: bold;">{BETA_LABEL}</p>')
        current_html_blocks.append(f'<p style="text-align: center; text-indent: 0; font-size: 0.8em; margin-top: 1em;">Distribution or public sharing of this specific proof is discouraged to protect the development of the author\'s IP.</p>')
        current_html_blocks.append(f'</div>')
        current_html_blocks.append('<div style="page-break-after: always;"></div>')
    
    for tag in soup.find_all(_BLOCK_TAGS):
        if tag.name == 'div' and tag.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(tag):
            continue

        # Standalone plate block: emit the plate(s) as referenced resources.
        if _block_has_only_images(tag):
            for img in _block_images(tag):
                current_html_blocks.append(_emit_epub_plate(img))
            continue

        text = tag.get_text().replace('\u200b', '').replace('\xa0', ' ').strip()
        if not text: continue

        if tag.name in ['h1', 'h2', 'h3']:
            if current_html_blocks:
                sections.append((current_chapter_title, current_html_blocks))
            current_chapter_title = text
            current_html_blocks = [f"<h1>{html.escape(text)}</h1>"]
        elif tag.name == 'p':
            if text in ['***', '* * *', '#']:
                current_html_blocks.append('<p style="text-align: center;">***</p>')
            else:
                # Render any inline <img> as proper resources, then drop the raw
                # <img> tags from the paragraph's inner HTML so no data-URI leaks.
                plate_imgs = _block_images(tag)
                html_inner = "".join([str(c) for c in tag.contents if getattr(c, "name", None) != "img"])
                current_html_blocks.append(f"<p>{html_inner}</p>")
                for img in plate_imgs:
                    current_html_blocks.append(_emit_epub_plate(img))
                
    if current_html_blocks:
        sections.append((current_chapter_title, current_html_blocks))
        
    epub_chapters = []
    for i, (chap_title, blocks) in enumerate(sections):
        c = epub.EpubHtml(title=chap_title, file_name=f'chap_{i}.xhtml', lang='en')
        c.content = f'<html><head><link rel="stylesheet" href="style/default.css" type="text/css"/></head><body>{"".join(blocks)}</body></html>'
        c.add_item(default_css)
        book.add_item(c)
        epub_chapters.append(c)
        
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    # Spine order: cover (auto, when set_cover(create_page=True)) → title page → chapters.
    # The 'nav' item stays in the manifest (EPUB3 requirement) but out of the spine, so
    # readers use their native TOC menu rather than a visible contents page.
    spine = ['cover'] if cover else []
    if title_page is not None:
        spine.append(title_page)
    spine.extend(epub_chapters)
    book.spine = spine
    
    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp:
        tmp_name = tmp.name

    try:
        epub.write_epub(tmp_name, book, {})
        out_stream = io.BytesIO()
        with open(tmp_name, 'rb') as f:
            out_stream.write(f.read())
        out_stream.seek(0)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

    return out_stream


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTWEIGHT TEXT FORMATS: Markdown, HTML, RTF, Plain text
#
# Each reuses the SAME front-matter strip (_strip_toc + _strip_frontmatter_blocks)
# the heavy formats use, so the manuscript's own embedded title/author block isn't
# duplicated under the generated title block. All preserve the EXACT wording and
# emit straight quotes (per project rule — we never introduce smart quotes).
# ─────────────────────────────────────────────────────────────────────────────

def _prepare_body_soup(content: str, title: str, author: str):
    """Parse content, strip the editor TOC + duplicated front matter, and return
    (soup, heading_nodes) where heading_nodes are the chapter headings in order."""
    soup = BeautifulSoup(content, 'html.parser')
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)
    heading_nodes = []
    for node in soup.find_all(['h1', 'h2', 'h3']):
        t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if t:
            heading_nodes.append(node)
    return soup, heading_nodes


def _slugify_anchor(text: str) -> str:
    """GitHub/CommonMark-style anchor slug: lowercased, spaces→hyphens, punctuation
    dropped. Used for both HTML id anchors and Markdown TOC links so they match."""
    import re
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-") or "section"


def _inline_to_markdown(node) -> str:
    """Render a node's inline children to Markdown (bold/italic), preserving exact
    text. Spell/grammar squiggle spans collapse to their plain text."""
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            inner = _inline_to_markdown(child)
            if child.name in ('strong', 'b'):
                parts.append(f"**{inner}**")
            elif child.name in ('em', 'i'):
                parts.append(f"*{inner}*")
            else:
                parts.append(inner)
    return ''.join(parts)


def _inline_to_plaintext(node) -> str:
    """Plain text of a node's children, exact wording, no markup."""
    return node.get_text().replace('​', '').replace('\xa0', ' ')


def _emit_markdown_plate(img_tag) -> str:
    """One inline plate as a CommonMark image: ![caption](data-uri). A malformed
    plate becomes a visible italic note (never silently dropped)."""
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        _decode_data_uri_image(src)
    except PlateError as e:
        return f"*[Plate could not be embedded: {e}]*"
    # Alt text doubles as the caption; Markdown has no native figcaption.
    return f"![{caption or 'Plate'}]({src})"


def generate_markdown(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    """CommonMark .md: cover image reference, title/author, anchor-linked TOC, then
    chapters with #/## headings. Wording preserved verbatim; straight quotes only."""
    soup, heading_nodes = _prepare_body_soup(content, title, author)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    lines = []
    if cover_image:
        # Embed the cover as a data-URI image reference so the .md is self-contained.
        cover = _decode_cover(cover_image)
        if cover:
            import base64
            img_data, _cw, _ch = cover
            b64 = base64.b64encode(img_data).decode("ascii")
            lines.append(f"![Cover](data:image/jpeg;base64,{b64})")
            lines.append("")

    lines.append(f"# {title_text}")
    if author_text:
        lines.append("")
        lines.append(f"by {author_text}")
    lines.append("")

    # Build anchor slugs (deduplicated) per heading so the TOC links resolve.
    seen = {}
    anchors = {}
    for node in heading_nodes:
        t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        slug = _slugify_anchor(t)
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0
        anchors[id(node)] = slug

    if heading_nodes:
        lines.append("## Table of Contents")
        lines.append("")
        for node in heading_nodes:
            t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
            lines.append(f"- [{t}](#{anchors[id(node)]})")
        lines.append("")

    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                lines.append(_emit_markdown_plate(img))
                lines.append("")
            continue
        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            continue
        if node.name in ['h1', 'h2', 'h3']:
            slug = anchors.get(id(node))
            # An explicit HTML anchor guarantees the TOC link target even when the
            # reader's slug algorithm differs from ours.
            if slug:
                lines.append(f'<a id="{slug}"></a>')
            lines.append("")
            lines.append(f"# {text}")
            lines.append("")
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                lines.append("")
                lines.append("---")
                lines.append("")
                continue
            lines.append(_inline_to_markdown(node).strip())
            lines.append("")
            for img in _block_images(node):
                lines.append(_emit_markdown_plate(img))
                lines.append("")

    md = "\n".join(lines).rstrip() + "\n"
    return io.BytesIO(md.encode("utf-8"))


def _inline_to_html(node) -> str:
    """Render inline children to safe HTML, preserving exact text (escaped) and
    bold/italic. Squiggle spans collapse to plain escaped text."""
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(html.escape(str(child)))
        elif isinstance(child, Tag):
            inner = _inline_to_html(child)
            if child.name in ('strong', 'b'):
                parts.append(f"<strong>{inner}</strong>")
            elif child.name in ('em', 'i'):
                parts.append(f"<em>{inner}</em>")
            else:
                parts.append(inner)
    return ''.join(parts)


def _emit_html_plate(img_tag) -> str:
    """Normalize one inline plate <img> for self-contained HTML: keep the embedded
    data-URI src and emit a <figure> + <figcaption>. A malformed plate becomes a
    visible note (never silently dropped)."""
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        # Validate the data so we surface a real error instead of a broken image.
        _decode_data_uri_image(src)
    except PlateError as e:
        return f'<p class="plate-error"><em>[Plate could not be embedded: {html.escape(str(e))}]</em></p>'
    alt = html.escape(caption) if caption else "Plate"
    cap_html = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
    return (f'<figure class="plate"><img src="{html.escape(src, quote=True)}" alt="{alt}"/>'
            f'{cap_html}</figure>')


def generate_html(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    """Self-contained .html: embedded cover (data URI), title block, anchor-linked
    TOC, then chapters with heading tags. Opens standalone in any browser."""
    soup, heading_nodes = _prepare_body_soup(content, title, author)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    font_family = ('"Garamond", "Palatino Linotype", serif'
                   if output_format == "penguin"
                   else '"Times New Roman", Times, serif')

    seen = {}
    anchors = {}
    for node in heading_nodes:
        t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        slug = _slugify_anchor(t)
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0
        anchors[id(node)] = slug

    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8"/>')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1"/>')
    parts.append(f"<title>{html.escape(title_text)}</title>")
    parts.append(
        "<style>"
        f"body{{font-family:{font_family};line-height:1.6;max-width:42rem;"
        "margin:2rem auto;padding:0 1rem;color:#111;}}"
        "img.cover{display:block;margin:0 auto 2rem;max-width:100%;height:auto;}"
        ".title-block{text-align:center;margin:2rem 0 3rem;}"
        ".title-block h1{font-size:2.2em;margin:0 0 .4em;}"
        ".title-block .author{font-size:1.2em;color:#444;}"
        "nav.toc{margin:2rem 0;}nav.toc ul{list-style:none;padding-left:0;}"
        "nav.toc li{margin:.3em 0;}"
        "h1.chapter{text-align:center;margin-top:3rem;}"
        "p{text-align:justify;text-indent:1.5em;margin:0 0 .2em;}"
        "hr.scene{border:none;text-align:center;margin:1.5rem 0;}"
        "hr.scene:after{content:'* * *';}"
        "figure.plate{margin:1.5rem 0;text-align:center;}"
        "figure.plate img{max-width:100%;height:auto;}"
        "figure.plate figcaption{font-style:italic;font-size:.9em;color:#444;margin-top:.4em;}"
        ".plate-error{text-align:center;color:#999;font-style:italic;}"
        "</style></head><body>"
    )

    cover = _decode_cover(cover_image)
    if cover:
        import base64
        img_data, _cw, _ch = cover
        b64 = base64.b64encode(img_data).decode("ascii")
        parts.append(f'<img class="cover" src="data:image/jpeg;base64,{b64}" alt="Cover"/>')

    parts.append('<div class="title-block">')
    parts.append(f"<h1>{html.escape(title_text)}</h1>")
    if author_text:
        parts.append(f'<div class="author">by {html.escape(author_text)}</div>')
    parts.append("</div>")

    if heading_nodes:
        parts.append('<nav class="toc"><h2>Table of Contents</h2><ul>')
        for node in heading_nodes:
            t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
            parts.append(f'<li><a href="#{anchors[id(node)]}">{html.escape(t)}</a></li>')
        parts.append("</ul></nav>")

    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                parts.append(_emit_html_plate(img))
            continue
        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            continue
        if node.name in ['h1', 'h2', 'h3']:
            slug = anchors.get(id(node), "")
            parts.append(f'<h1 class="chapter" id="{slug}">{html.escape(text)}</h1>')
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                parts.append('<hr class="scene"/>')
                continue
            parts.append(f"<p>{_inline_to_html(node)}</p>")
            for img in _block_images(node):
                parts.append(_emit_html_plate(img))

    parts.append("</body></html>")
    out = "\n".join(parts)
    return io.BytesIO(out.encode("utf-8"))


def _rtf_escape(text: str) -> str:
    """Escape text for RTF: backslash/braces, and non-ASCII via \\uN unicode runs
    (preserves exact characters in WordPad/Word). Straight quotes are passed
    through unchanged."""
    out = []
    for ch in text:
        o = ord(ch)
        if ch in ('\\', '{', '}'):
            out.append('\\' + ch)
        elif o < 128:
            out.append(ch)
        else:
            # RTF \uN uses signed 16-bit; emit a fallback '?' for non-unicode readers.
            code = o if o <= 32767 else o - 65536
            out.append(f"\\u{code}?")
    return ''.join(out)


def _inline_to_rtf(node) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(_rtf_escape(str(child)))
        elif isinstance(child, Tag):
            inner = _inline_to_rtf(child)
            if child.name in ('strong', 'b'):
                parts.append("{\\b " + inner + "}")
            elif child.name in ('em', 'i'):
                parts.append("{\\i " + inner + "}")
            else:
                parts.append(inner)
    return ''.join(parts)


def _rtf_pict_from_bytes(raw: bytes, ext: str, w: int, h: int, max_w_twips: int = 9000, max_h_twips: int = 12000) -> str:
    """Build an RTF ``\\pict`` group (hex-encoded JPEG/PNG) so Word/WordPad render
    the image. Dimensions are set via \\picwgoal/\\pichgoal (twips = 1/1440 inch),
    scaled to fit ``max_w_twips`` x ``max_h_twips`` while preserving aspect.

    RTF natively understands \\jpegblip and \\pngblip; for any other format we
    transcode to PNG via Pillow so the picture still embeds portably."""
    blip = None
    if ext in ("jpeg", "jpg"):
        blip = "jpegblip"
    elif ext == "png":
        blip = "pngblip"
    else:
        # Transcode (gif/bmp/webp/…) to PNG so RTF readers can display it.
        from PIL import Image as _PILImage
        buf = io.BytesIO()
        with _PILImage.open(io.BytesIO(raw)) as im:
            im.convert("RGB").save(buf, format="PNG")
        raw = buf.getvalue()
        blip = "pngblip"
    # Scale (twips) to fit, preserving aspect.
    aspect = (h / w) if w else 1.0
    goal_w = max_w_twips
    goal_h = int(max_w_twips * aspect)
    if goal_h > max_h_twips:
        goal_h = max_h_twips
        goal_w = int(max_h_twips / aspect) if aspect else max_w_twips
    hexdata = raw.hex()
    # picw/pich carry the source pixel size; picwgoal/pichgoal the display size.
    return (f"{{\\pict\\{blip}\\picw{w}\\pich{h}\\picwgoal{goal_w}\\pichgoal{goal_h} "
            f"{hexdata}}}")


def _emit_rtf_plate(out, img_tag):
    """Append one inline plate (centered \\pict + caption) to the RTF segment list.
    A malformed plate becomes a visible italic note (never silently dropped)."""
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        raw, ext, w, h = _decode_data_uri_image(src)
    except PlateError as e:
        out.append("\\pard\\qc\\i [Plate could not be embedded: " + _rtf_escape(str(e)) + "]\\i0\\par")
        out.append("\\pard\\qj\\fi360\\sl360\\slmult1")
        return
    out.append("\\pard\\qc\\sb200 " + _rtf_pict_from_bytes(raw, ext, w, h) + "\\par")
    if caption:
        out.append("\\pard\\qc\\i\\fs20 " + _rtf_escape(caption) + "\\i0\\fs24\\par")
    # Restore body paragraph defaults for following prose.
    out.append("\\pard\\qj\\fi360\\sl360\\slmult1")


def generate_rtf(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    """Rich Text .rtf: a cover page (\\pict), a title page (title + author), a text
    TOC (chapter list), then body with bold chapter headings and inline plates
    embedded via \\pict. Opens in WordPad/Word/any RTF reader."""
    soup, heading_nodes = _prepare_body_soup(content, title, author)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    out = []
    # Header: RTF version, ANSI charset, a single serif font, default 12pt (24 half-pt).
    out.append("{\\rtf1\\ansi\\ansicpg1252\\deff0")
    out.append("{\\fonttbl{\\f0\\froman Times New Roman;}}")
    out.append("\\f0\\fs24")

    # --- Cover page (\pict): the full cover image, centered, then a page break. ---
    if cover_image:
        try:
            raw, ext, cw, ch = _decode_data_uri_image(cover_image)
            out.append("\\pard\\qc\\sb1000 " + _rtf_pict_from_bytes(raw, ext, cw, ch) + "\\par")
            out.append("\\page")
        except PlateError as e:
            out.append("\\pard\\qc\\i [Cover could not be embedded: " + _rtf_escape(str(e)) + "]\\i0\\par\\page")

    # --- Title page ---
    out.append("\\pard\\qc\\sb2000\\fs56\\b " + _rtf_escape(title_text) + "\\b0\\par")
    if author_text:
        out.append("\\qc\\sb400\\fs28 by " + _rtf_escape(author_text) + "\\par")
    out.append("\\fs24\\page")

    # --- Table of Contents (text list; no page numbers) ---
    if heading_nodes:
        out.append("\\pard\\qc\\b\\fs36 Table of Contents\\b0\\fs24\\par\\sb200")
        out.append("\\pard\\ql\\fi0")
        for node in heading_nodes:
            t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
            out.append(_rtf_escape(t) + "\\par")
        out.append("\\page")

    # --- Body ---
    out.append("\\pard\\sl360\\slmult1")
    first = True
    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                _emit_rtf_plate(out, img)
                first = False
            continue
        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            continue
        if node.name in ['h1', 'h2', 'h3']:
            if not first:
                out.append("\\page")
            out.append("\\pard\\qc\\b\\fs32\\sb400\\sa200 " + _rtf_escape(text) + "\\b0\\fs24\\par")
            out.append("\\pard\\qj\\fi360\\sl360\\slmult1")
            first = False
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                out.append("\\pard\\qc\\sb200\\sa200 * * *\\par")
                out.append("\\pard\\qj\\fi360\\sl360\\slmult1")
                continue
            out.append(_inline_to_rtf(node) + "\\par")
            first = False
            for img in _block_images(node):
                _emit_rtf_plate(out, img)

    out.append("}")
    # Join with newlines: a newline is whitespace, so it terminates any trailing
    # parameterless control word (e.g. \par, \page) on each segment — preventing
    # "\parChapter" from being mis-read as one unknown control word (which would
    # drop the text). RTF readers ignore newlines as content.
    rtf = "\n".join(out)
    return io.BytesIO(rtf.encode("ascii", "replace"))


def generate_txt(content: str, chapters: list = None, title: str = "Manuscript Title", author: str = "Author Name", output_format: str = "chicago", cover_image: str = None) -> io.BytesIO:
    """Plain UTF-8 .txt: a title block, a numbered text TOC, then body. Plain text
    cannot show images, so the cover and each inline plate become a visible
    placeholder line so nothing silently vanishes."""
    soup, heading_nodes = _prepare_body_soup(content, title, author)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    lines = []
    lines.append(title_text)
    if author_text:
        lines.append(f"by {author_text}")
    if cover_image:
        lines.append(f"[Cover: {title_text}]")
    lines.append("")
    lines.append("")

    if heading_nodes:
        lines.append("TABLE OF CONTENTS")
        lines.append("")
        for i, node in enumerate(heading_nodes, start=1):
            t = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
            lines.append(f"{i}. {t}")
        lines.append("")
        lines.append("")

    def _plate_placeholder(img):
        cap = _image_caption(img)
        return f"[Plate: {cap or 'image'}]"

    first = True
    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                lines.append(_plate_placeholder(img))
                lines.append("")
            first = False
            continue
        text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
        if not text:
            continue
        if node.name in ['h1', 'h2', 'h3']:
            if not first:
                lines.append("")
                lines.append("")
            lines.append(text)
            lines.append("=" * len(text))
            lines.append("")
            first = False
        elif node.name == 'p':
            if text in ['***', '* * *', '#']:
                lines.append("")
                lines.append("                    * * *")
                lines.append("")
                continue
            lines.append(_inline_to_plaintext(node).strip())
            lines.append("")
            first = False
            for img in _block_images(node):
                lines.append(_plate_placeholder(img))
                lines.append("")

    txt = "\n".join(lines).rstrip() + "\n"
    return io.BytesIO(txt.encode("utf-8"))

