"""OpenDocument Text (.odt) export module — self-contained and portable.

Mirrors the exporter contract used by every generator in ``services.exporter``:

    generate_odt(content, chapters=None, title=..., author=..., output_format=..., cover_image=None) -> io.BytesIO

Layout mapping (mirrors ``generate_docx``):
  - optional full-page cover image (from a base64 data-URL)
  - a title page (title 28pt bold centered; "by <author>" 16pt centered)
  - a static "Contents" page listing the chapter headings
  - chapter headings as real outline-level-1 headings (``text:h``), centered,
    each starting a new page
  - body paragraphs justified with a 0.5" first-line indent, bold/italic
    inline formatting preserved as character-styled spans
  - inline plates (<img>/<figure> with data-URI src) embedded as pictures with
    their caption below; a malformed plate becomes a VISIBLE inline note —
    never silently dropped (governance rule #4)
  - ``output_format``: 'penguin' → Garamond, 1.5 line spacing;
    anything else ('chicago') → Times New Roman, double spacing
    (same distinction as ``generate_docx``)

Dependencies: odfpy + BeautifulSoup + stdlib only. Pillow is used
opportunistically (image validation + real dimensions) when installed; without
it, images still embed with sensible default aspect ratios.

Spell/grammar squiggle spans in the editor HTML collapse to plain text (their
wording is kept verbatim; the on-screen decoration is editor chrome, not
manuscript formatting).
"""

import io

from bs4 import BeautifulSoup, NavigableString, Tag

from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties, FontFace, TabStops, TabStop
from odf.text import H, P, Span, LineBreak
from odf.text import (TableOfContent, TableOfContentSource, TableOfContentEntryTemplate,
                      IndexEntryText, IndexEntryTabStop, IndexEntryPageNumber, IndexBody)
from odf.draw import Frame, Image


BETA_LABEL = "Tome-Master BETA - UNSUBMITTED DRAFT"

_BLOCK_TAGS = ['h1', 'h2', 'h3', 'p', 'div', 'figure', 'img']

# Printable area on US Letter with 1" margins, in inches (same as generate_docx).
_PAGE_W_IN = 6.5
_PAGE_H_IN = 9.0
_PLATE_MAX_H_IN = 8.0


# ─────────────────────────────────────────────────────────────────────────────
# Image decoding (data URIs). Pillow is optional: when present it validates the
# bytes and reports real pixel dimensions; when absent we fall back to header
# sniffing + a default aspect ratio so the export still succeeds.
# ─────────────────────────────────────────────────────────────────────────────

class PlateError(Exception):
    """A specific <img> could not be decoded. Carries the failure reason so the
    exporter surfaces it inline rather than silently dropping the plate."""


def _sniff_image_ext(raw: bytes) -> str:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"\xff\xd8"):
        return "jpeg"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if raw.startswith(b"BM"):
        return "bmp"
    return ""


def _pil_dimensions(raw: bytes):
    """(width, height, format_ext) via Pillow, or None when Pillow is absent.
    Raises PlateError when Pillow IS present but cannot read the bytes."""
    try:
        from PIL import Image as _PILImage
    except ImportError:
        return None
    try:
        with _PILImage.open(io.BytesIO(raw)) as im:
            w, h = im.size
            fmt = (im.format or "").lower()
    except Exception as e:
        raise PlateError(f"image bytes are not a readable image ({e})")
    return w, h, ("jpeg" if fmt == "jpg" else fmt)


def _decode_data_uri_image(src: str):
    """Decode an <img src> data-URI into (bytes, ext, width_px, height_px).

    Raises PlateError on anything that cannot be embedded (external http link,
    undecodable base64, or — with Pillow installed — unreadable image bytes) so
    the caller surfaces a real, specific error.
    """
    import base64
    if not src:
        raise PlateError("image has no src")
    s = src.strip()
    if not s.lower().startswith("data:"):
        raise PlateError(f"unsupported image src (not a data URI): {s[:60]}")
    header, _, encoded = s.partition(",")
    if not encoded:
        raise PlateError("data URI has no payload")
    ext = "png"
    if ":" in header and "/" in header:
        mediatype = header[header.index(":") + 1:].split(";")[0]
        if "/" in mediatype:
            ext = mediatype.split("/", 1)[1].strip().lower() or "png"
    try:
        if "base64" in header.lower():
            raw = base64.b64decode(encoded, validate=True)
        else:
            from urllib.parse import unquote_to_bytes
            raw = unquote_to_bytes(encoded)
    except Exception as e:
        raise PlateError(f"could not decode image data ({e})")
    if not raw:
        raise PlateError("image decoded to zero bytes")
    dims = _pil_dimensions(raw)  # raises PlateError on unreadable bytes
    if dims:
        w, h, fmt = dims
        if fmt:
            ext = fmt
    else:
        sniffed = _sniff_image_ext(raw)
        if sniffed:
            ext = sniffed
        w, h = 1000, 750  # landscape default when dimensions are unknowable
    if ext == "jpg":
        ext = "jpeg"
    return raw, ext, w, h


def _decode_cover(cover_image: str):
    """Decode a base64 (data-URL or bare base64) cover into
    (bytes, ext, width_px, height_px). Returns None when no cover supplied.
    Raises on undecodable base64 so the caller surfaces a real error rather
    than silently exporting a book with no cover."""
    if not cover_image:
        return None
    import base64
    encoded = cover_image.split(",", 1)[1] if "," in cover_image else cover_image
    raw = base64.b64decode(encoded)
    try:
        dims = _pil_dimensions(raw)
    except PlateError:
        dims = None  # cover path keeps the docx behavior: embed with default aspect
    if dims:
        w, h, fmt = dims
        ext = fmt or _sniff_image_ext(raw) or "jpeg"
    else:
        w, h = 1000, 1500
        ext = _sniff_image_ext(raw) or "jpeg"
    return raw, ext, w, h


def _image_caption(img_tag) -> str:
    """Human caption for an <img>: the wrapping <figure>'s <figcaption> if any,
    else the img alt/title. Returns '' when none. Exact wording kept."""
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


# ─────────────────────────────────────────────────────────────────────────────
# HTML block helpers (same semantics as services.exporter — duplicated here on
# purpose so this module stays importable on its own).
# ─────────────────────────────────────────────────────────────────────────────

def _block_images(node):
    if getattr(node, "name", None) == "img":
        return [node]
    if hasattr(node, "find_all"):
        return node.find_all("img")
    return []


def _block_has_only_images(node) -> bool:
    name = getattr(node, "name", None)
    if name == "img":
        return True
    if not _block_images(node):
        return False
    if name == "figure":
        return True
    text = node.get_text().replace('​', '').replace('\xa0', ' ').strip()
    return not text


def _is_nested_block(node) -> bool:
    parent = node.parent
    while parent is not None and getattr(parent, "name", None):
        if parent.name in ('p', 'figure'):
            return True
        if node.name in ('img', 'figure') and parent.name in ('div', 'h1', 'h2', 'h3'):
            return True
        parent = parent.parent
    return False


def _strip_toc(soup):
    """Remove any manuscript-authored table of contents from the body (the ODT
    gets its own generated Contents page)."""
    toc_div = soup.find('div', class_='editor-toc')
    if toc_div:
        toc_div.decompose()
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'b', 'strong']):
        if not tag.parent:
            continue
        text = tag.get_text().replace('​', '').strip().lower()
        if text in ("table of contents", "contents"):
            curr = tag.next_sibling
            while curr:
                next_node = curr.next_sibling
                if getattr(curr, 'name', None) in ('h1', 'h2', 'h3') and curr.get_text().strip():
                    break
                curr_text = curr.get_text().replace('​', '').strip().lower() if hasattr(curr, 'get_text') else ""
                if curr_text and (curr_text.startswith('chapter ') or curr_text in ('prologue', 'epilogue')):
                    break
                if hasattr(curr, 'decompose'):
                    curr.decompose()
                curr = next_node
            tag.decompose()
            break


def _strip_frontmatter_blocks(soup, title, author):
    """Remove the manuscript's own leading title/author block so it is not
    duplicated under the generated title page (same rules as generate_docx)."""
    title_l = (title or "").strip().lower()
    author_l = (author or "").strip().lower()
    removed = 0
    for node in list(soup.find_all(['h1', 'h2', 'h3', 'p', 'div'])):
        if not getattr(node, 'name', None) or not node.parent:
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
        break


# ─────────────────────────────────────────────────────────────────────────────
# ODT document construction
# ─────────────────────────────────────────────────────────────────────────────

def _protection_active() -> bool:
    """Beta watermark gate. Uses the app's license service when this module
    runs inside Tome-Master; when the module is reused standalone (no
    ``services.license_service`` importable) no watermark is applied."""
    try:
        from services import license_service
    except ImportError:
        return False
    return not license_service.is_activated()


def _build_styles(doc, output_format: str):
    """Register the named styles this exporter uses and return them by key."""
    penguin = output_format == 'penguin'
    font_name = 'Garamond' if penguin else 'Times New Roman'
    line_height = '150%' if penguin else '200%'

    doc.fontfacedecls.addElement(FontFace(
        name=font_name, fontfamily=f"'{font_name}'",
        fontfamilygeneric="roman", fontpitch="variable"))

    styles = {}

    def para(key, name, para_props=None, text_props=None):
        s = Style(name=name, family="paragraph")
        if para_props:
            s.addElement(ParagraphProperties(**para_props))
        base_text = {"fontname": font_name}
        base_text.update(text_props or {})
        s.addElement(TextProperties(**base_text))
        doc.styles.addElement(s)
        styles[key] = s
        return s

    body_para = {"textalign": "justify", "textindent": "0.5in",
                 "lineheight": line_height, "margintop": "0in", "marginbottom": "0in"}
    para("body", "TMBody", body_para, {"fontsize": "12pt"})
    para("body_break", "TMBodyBreak", {**body_para, "breakbefore": "page"}, {"fontsize": "12pt"})
    para("heading1", "TMHeading1",
         {"textalign": "center", "breakbefore": "page",
          "margintop": "0.2in", "marginbottom": "0.2in"},
         {"fontsize": "16pt", "fontweight": "bold"})
    # 2" top margin drops the title ~1/3 down the page, matching generate_docx.
    para("title", "TMTitle", {"textalign": "center", "margintop": "2in"},
         {"fontsize": "28pt", "fontweight": "bold"})
    para("author", "TMAuthor", {"textalign": "center"}, {"fontsize": "16pt"})
    para("center", "TMCenter", {"textalign": "center"}, {"fontsize": "12pt"})
    para("center_break", "TMCenterBreak", {"textalign": "center", "breakbefore": "page"},
         {"fontsize": "12pt"})
    para("scene_break", "TMSceneBreak", {"textalign": "center", "lineheight": line_height},
         {"fontsize": "12pt"})
    para("caption", "TMCaption", {"textalign": "center"},
         {"fontsize": "10pt", "fontstyle": "italic"})
    para("plate_note", "TMPlateNote", {"textalign": "center"},
         {"fontsize": "10pt", "fontstyle": "italic", "color": "#999999"})
    para("toc_heading", "TMContentsHeading",
         {"textalign": "center", "breakbefore": "page", "marginbottom": "0.2in"},
         {"fontsize": "18pt", "fontweight": "bold"})
    # TOC entries carry a right-aligned dot-leader tab so refreshed page numbers
    # align at the margin (chapter title . . . . N).
    toc_entry = para("toc_entry", "TMTocEntry", {"lineheight": "150%"}, {"fontsize": "12pt"})
    toc_tabs = TabStops()
    toc_tabs.addElement(TabStop(position=f"{_PAGE_W_IN}in", type="right", leadertext="."))
    for el in toc_entry.childNodes:
        if el.qname[1] == "paragraph-properties":
            el.addElement(toc_tabs)
            break
    para("watermark", "TMWatermark", {"textalign": "center"},
         {"fontsize": "10pt", "color": "#808080"})

    def char(key, name, **text_props):
        s = Style(name=name, family="text")
        s.addElement(TextProperties(**text_props))
        doc.styles.addElement(s)
        styles[key] = s

    char("bold", "TMBold", fontweight="bold")
    char("italic", "TMItalic", fontstyle="italic")
    char("bold_italic", "TMBoldItalic", fontweight="bold", fontstyle="italic")
    return styles


def _iter_inline_runs(node, bold=False, italic=False):
    """Yield (text, bold, italic) runs for a block's inline content, exact
    wording preserved. <img> children are skipped here (plates are rendered
    separately, after the paragraph, to preserve document order)."""
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text:
                yield text, bold, italic
        elif isinstance(child, Tag):
            if child.name == 'img':
                continue
            if child.name == 'br':
                yield '\n', bold, italic
            elif child.name in ('strong', 'b'):
                yield from _iter_inline_runs(child, True, italic)
            elif child.name in ('em', 'i'):
                yield from _iter_inline_runs(child, bold, True)
            else:
                yield from _iter_inline_runs(child, bold, italic)


def _append_text_with_breaks(target, text: str):
    """Add text to a P/Span, converting embedded newlines to <text:line-break/>."""
    pieces = text.split('\n')
    for i, piece in enumerate(pieces):
        if i:
            target.addElement(LineBreak())
        if piece:
            target.addText(piece)


def _add_inline_runs(p, node, styles):
    """Render a block's inline content into an odf P, mapping bold/italic to
    character-styled spans (nesting flattened, like the DOCX run mapping)."""
    for text, bold, italic in _iter_inline_runs(node):
        clean = text.replace('​', '').replace('\xa0', ' ')
        if not clean:
            continue
        if bold and italic:
            span = Span(stylename=styles["bold_italic"])
        elif bold:
            span = Span(stylename=styles["bold"])
        elif italic:
            span = Span(stylename=styles["italic"])
        else:
            _append_text_with_breaks(p, clean)
            continue
        _append_text_with_breaks(span, clean)
        p.addElement(span)


def _fit_image_inches(w_px, h_px, max_w_in, max_h_in):
    """Fit an image into (max_w, max_h) inches preserving aspect ratio."""
    aspect = (h_px / w_px) if w_px else 1.5
    width = max_w_in
    height = max_w_in * aspect
    if height > max_h_in:
        height = max_h_in
        width = (max_h_in / aspect) if aspect else max_w_in
    return width, height


def _add_picture_paragraph(doc, styles, raw, ext, w_px, h_px,
                           max_w_in, max_h_in, index, para_style):
    """Embed image bytes as a Pictures/ package part inside a centered paragraph."""
    href = doc.addPicture(f"Pictures/tm_image_{index}.{ext}",
                          mediatype=f"image/{ext}", content=raw)
    width_in, height_in = _fit_image_inches(w_px, h_px, max_w_in, max_h_in)
    p = P(stylename=para_style)
    frame = Frame(width=f"{width_in:.3f}in", height=f"{height_in:.3f}in",
                  anchortype="as-char")
    frame.addElement(Image(href=href, type="simple", show="embed", actuate="onLoad"))
    p.addElement(frame)
    doc.text.addElement(p)


def _add_odt_plate(doc, styles, img_tag, index, para_style):
    """Embed one inline plate <img> in place: centered picture fit to the
    printable width with its caption below. A malformed plate becomes a
    visible inline note (never silently dropped)."""
    src = img_tag.get("src") or ""
    caption = _image_caption(img_tag)
    try:
        raw, ext, w, h = _decode_data_uri_image(src)
    except PlateError as e:
        note = P(stylename=styles["plate_note"])
        note.addText(f"[Plate could not be embedded: {e}]")
        doc.text.addElement(note)
        return
    _add_picture_paragraph(doc, styles, raw, ext, w, h,
                           _PAGE_W_IN, _PLATE_MAX_H_IN, index, para_style)
    if caption:
        cap = P(stylename=styles["caption"])
        cap.addText(caption)
        doc.text.addElement(cap)


def _clean_text(node) -> str:
    return node.get_text().replace('​', '').replace('\xa0', ' ').strip()


def generate_odt(content: str, chapters: list = None, title: str = "Manuscript Title",
                 author: str = "Author Name", output_format: str = "chicago",
                 cover_image: str = None) -> io.BytesIO:
    """Render manuscript HTML to a .odt (OpenDocument Text) stream, seeked to 0.

    ``chapters`` is accepted for exporter-signature parity; like generate_docx,
    the chapter structure is derived from the manuscript's own <h1>-<h3>
    headings (``chapters`` supplies Contents-page titles only when the HTML
    carries no headings at all).
    """
    doc = OpenDocumentText()
    styles = _build_styles(doc, output_format)

    image_index = 0

    # --- Beta watermark line (matches the DOCX/PDF protection behavior) ---
    if _protection_active():
        wm = P(stylename=styles["watermark"])
        wm.addText(f"--- {BETA_LABEL} ---")
        doc.text.addElement(wm)

    # --- Cover image: fills the printable page, on its own first page ---
    cover = _decode_cover(cover_image)
    if cover:
        raw, ext, cw, ch = cover
        image_index += 1
        _add_picture_paragraph(doc, styles, raw, ext, cw, ch,
                               _PAGE_W_IN, _PAGE_H_IN, image_index, styles["center"])

    # --- Title page: ALWAYS rendered (never suppressed) ---
    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()
    first_title_para = P(stylename=styles["center_break"] if cover else styles["center"])
    doc.text.addElement(first_title_para)
    for _ in range(2):
        doc.text.addElement(P(stylename=styles["center"]))
    tp = P(stylename=styles["title"])
    tp.addText(title_text)
    doc.text.addElement(tp)
    if author_text:
        doc.text.addElement(P(stylename=styles["center"]))
        ap = P(stylename=styles["author"])
        ap.addText(f"by {author_text}")
        doc.text.addElement(ap)

    # --- Parse the body; strip any authored TOC and duplicate title block ---
    soup = BeautifulSoup(content or "", 'html.parser')
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)

    heading_nodes = [n for n in soup.find_all(['h1', 'h2', 'h3'])
                     if not _is_nested_block(n) and _clean_text(n)]

    # --- Contents page: a real text:table-of-content over outline level 1 ---
    # (chapter headings are emitted as text:h outline-level 1 below, so Word /
    # LibreOffice fill in page numbers on index refresh; the index-body is
    # pre-populated with the chapter titles so the page reads before a refresh).
    toc_titles = [_clean_text(n) for n in heading_nodes]
    if not toc_titles and chapters:
        toc_titles = [str(c.get("suggested_title") or c.get("title") or "").strip()
                      for c in chapters if isinstance(c, dict)]
        toc_titles = [t for t in toc_titles if t]
    # The "Contents" heading lives OUTSIDE the table-of-content element: word
    # processors regenerate the index-body wholesale on field update, and a
    # heading inside it (index-title) gets discarded — taking its page break
    # with it. Outside, both the heading and the break survive refreshes.
    toc_h = P(stylename=styles["toc_heading"])
    toc_h.addText("Contents")
    doc.text.addElement(toc_h)
    toc = TableOfContent(name="Contents")
    toc_src = TableOfContentSource(outlinelevel=1, useoutlinelevel="true")
    entry_tpl = TableOfContentEntryTemplate(outlinelevel=1, stylename=styles["toc_entry"])
    entry_tpl.addElement(IndexEntryText())
    entry_tpl.addElement(IndexEntryTabStop(type="right", leaderchar="."))
    entry_tpl.addElement(IndexEntryPageNumber())
    toc_src.addElement(entry_tpl)
    toc.addElement(toc_src)
    toc_body = IndexBody()
    for t in toc_titles:
        entry = P(stylename=styles["toc_entry"])
        entry.addText(t)
        toc_body.addElement(entry)
    toc.addElement(toc_body)
    doc.text.addElement(toc)

    # --- Body ---
    body_started = False  # first non-heading block after the Contents page
    for node in soup.find_all(_BLOCK_TAGS):
        if node.name == 'div' and node.get('id') == 'toc-placeholder':
            continue
        if _is_nested_block(node):
            continue

        if _block_has_only_images(node):
            for img in _block_images(node):
                image_index += 1
                plate_style = styles["center"] if body_started else styles["center_break"]
                _add_odt_plate(doc, styles, img, image_index, plate_style)
                body_started = True
            continue

        text = _clean_text(node)
        if not text:
            continue

        if node.name in ('h1', 'h2', 'h3'):
            h = H(outlinelevel=1, stylename=styles["heading1"])
            h.addText(text)
            doc.text.addElement(h)
            body_started = True
        elif node.name == 'p':
            if text in ('***', '* * *', '#'):
                sb = P(stylename=styles["scene_break"])
                sb.addText('#')
                doc.text.addElement(sb)
                body_started = True
                continue
            p_style = styles["body"] if body_started else styles["body_break"]
            p = P(stylename=p_style)
            _add_inline_runs(p, node, styles)
            doc.text.addElement(p)
            body_started = True
            # A <p> can carry prose AND an inline plate; render any images
            # immediately after the paragraph so order is preserved.
            for img in _block_images(node):
                image_index += 1
                _add_odt_plate(doc, styles, img, image_index, styles["center"])

    file_stream = io.BytesIO()
    doc.write(file_stream)
    file_stream.seek(0)
    return file_stream
