"""Final Draft (.fdx) export — self-contained, portable module.

Converts a prose manuscript (HTML string) into Final Draft's XML format:

    <FinalDraft DocumentType="Script" Template="No" Version="1">
      <Content>
        <Paragraph Type="..."><Text [Style="..."]>...</Text></Paragraph>
        ...
      </Content>
      <TitlePage><Content>...</Content></TitlePage>
    </FinalDraft>

Design rules (deliberate, per project governance):

* Dependencies: **stdlib + bs4 only**. No imports from ``exporter.py`` — this
  module must remain portable/reusable, so the small amount of body-preparation
  logic it needs (editor-TOC strip, duplicated front-matter strip, block
  iteration) is reimplemented here to match the behavior of the other
  exporters without coupling to them.
* XML is built with ``xml.etree.ElementTree`` so escaping of &, <, >, quotes
  (including “smart quotes”) is always correct — never string-concatenated.
* Wording is preserved verbatim (100% literal accuracy). We never alter the
  author's text, only map structure.

Mapping choices:

* **Chapter titles → Paragraph Type="Scene Heading".** Final Draft's Scene
  Navigator, index cards and structure views are all keyed off Scene Heading
  paragraphs, so mapping chapters to Scene Headings keeps the manuscript
  navigable inside Final Draft (jump-to-chapter works). Mapping them to
  "General" (even bold) would flatten the document into one unstructured
  scroll — semantically a chapter IS the manuscript's scene-level landmark.
* **Prose paragraphs → Paragraph Type="Action".**
* **Bold/italic inline HTML → <Text Style="Bold"/"Italic"/"Bold+Italic">.**
* **Inline images/plates → a bracketed note paragraph** ("[Plate: caption]")
  — never a base64 dump; FDX has no native image embed we can rely on.
* Scene-break markers (***, * * *, #) → an Action paragraph "* * *".
* ``output_format`` and ``cover_image`` are accepted for signature parity
  with the other ``generate_*`` exporters but are not used (FDX has no cover
  or house-style concept).
"""

import io
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup, NavigableString, Tag

# Paragraph types Final Draft recognizes (kept for reference / validation by
# callers and tests; this module only ever emits Scene Heading and Action).
VALID_PARAGRAPH_TYPES = frozenset([
    "Scene Heading", "Action", "Character", "Dialogue",
    "Parenthetical", "Transition", "Shot", "General",
])

_BLOCK_TAGS = ["h1", "h2", "h3", "p", "div", "figure", "img"]
_SCENE_BREAK_MARKS = ("***", "* * *", "#")


def _clean(text: str) -> str:
    """Normalize invisible characters the editor injects; keep wording intact."""
    return text.replace("​", "").replace("\xa0", " ")


# ─── Body preparation (mirrors exporter.py behavior, reimplemented) ──────────

def _strip_toc(soup) -> None:
    """Remove the editor's TOC block and any manual 'Table of Contents' section
    so TOC entries don't come out as bogus script paragraphs."""
    toc_div = soup.find("div", class_="editor-toc")
    if toc_div:
        toc_div.decompose()

    for tag in soup.find_all(["h1", "h2", "h3", "p", "b", "strong"]):
        if not tag.parent:
            continue
        text = _clean(tag.get_text()).strip().lower()
        if text in ("table of contents", "contents"):
            curr = tag.next_sibling
            while curr:
                nxt = curr.next_sibling
                if getattr(curr, "name", None) in ("h1", "h2", "h3") and curr.get_text().strip():
                    break
                curr_text = _clean(curr.get_text()).strip().lower() if hasattr(curr, "get_text") else ""
                if curr_text and (curr_text.startswith("chapter ") or curr_text in ("prologue", "epilogue")):
                    break
                if hasattr(curr, "decompose"):
                    curr.decompose()
                curr = nxt
            tag.decompose()
            break


def _strip_frontmatter_blocks(soup, title: str, author: str) -> None:
    """Drop the manuscript's own leading title/author block so it is not
    duplicated under the generated <TitlePage>. Conservative: only removes
    leading blocks that look like a title page (matching the supplied
    title/author, a bare 'by' line, or a 'title page' label), stopping at the
    first real chapter heading or body paragraph."""
    title_l = (title or "").strip().lower()
    author_l = (author or "").strip().lower()
    removed = 0
    for node in list(soup.find_all(["h1", "h2", "h3", "p", "div"])):
        if not getattr(node, "name", None) or not node.parent:
            continue
        text = _clean(node.get_text()).strip()
        if not text:
            node.decompose()
            continue
        t_lower = text.lower()
        is_title = bool(title_l) and t_lower == title_l
        is_author = bool(author_l) and t_lower in (author_l, f"by {author_l}")
        is_by_line = t_lower in ("by", "by:", "by-") or t_lower.startswith("by ")
        is_label = t_lower in ("title page", "titlepage")
        if removed < 4 and (is_title or is_author or is_by_line or is_label):
            node.decompose()
            removed += 1
            continue
        break  # first non-front-matter block → stop scanning


def _is_nested_block(node) -> bool:
    """True when this block's rendering is owned by an ancestor block we also
    iterate (e.g. an <img> inside a <figure> or <p>)."""
    parent = node.parent
    while parent is not None and getattr(parent, "name", None):
        if parent.name in ("p", "figure"):
            return True
        if node.name in ("img", "figure") and parent.name in ("div", "h1", "h2", "h3"):
            return True
        parent = parent.parent
    return False


def _block_images(node):
    """Images carried by a block node, in document order."""
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
    return not _clean(node.get_text()).strip()


def _image_caption(img_tag) -> str:
    """Caption for an <img>: wrapping <figure>'s <figcaption>, else alt/title."""
    fig = img_tag.find_parent("figure")
    if fig is not None:
        cap = fig.find("figcaption")
        if cap is not None:
            t = _clean(cap.get_text()).strip()
            if t:
                return t
    for attr in ("alt", "title"):
        v = _clean(img_tag.get(attr) or "").strip()
        if v:
            return v
    return ""


# ─── Inline styling → FDX <Text Style=…> runs ────────────────────────────────

def _inline_runs(node, bold: bool = False, italic: bool = False):
    """Flatten a block's inline children into (text, bold, italic) runs,
    preserving exact text. Images are skipped here — the block emitter turns
    them into bracketed note paragraphs. Unknown spans (spell/grammar
    squiggles etc.) collapse to their plain text."""
    runs = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = _clean(str(child))
            if text:
                runs.append((text, bold, italic))
        elif isinstance(child, Tag):
            if child.name == "img":
                continue
            b = bold or child.name in ("strong", "b")
            i = italic or child.name in ("em", "i")
            runs.extend(_inline_runs(child, b, i))
    return runs


def _merge_runs(runs):
    """Merge adjacent runs with identical styling and trim the paragraph's
    outer whitespace (leading on first run, trailing on last)."""
    merged = []
    for text, b, i in runs:
        if merged and merged[-1][1] == b and merged[-1][2] == i:
            merged[-1][0] += text
        else:
            merged.append([text, b, i])
    if merged:
        merged[0][0] = merged[0][0].lstrip()
        merged[-1][0] = merged[-1][0].rstrip()
    return [(t, b, i) for t, b, i in merged if t]


def _style_attr(bold: bool, italic: bool):
    if bold and italic:
        return "Bold+Italic"
    if bold:
        return "Bold"
    if italic:
        return "Italic"
    return None


def _append_paragraph(content_el, ptype: str, runs) -> None:
    """One <Paragraph Type=…> with one <Text> element per style run.
    ``runs`` may be a plain string (single unstyled run)."""
    p = ET.SubElement(content_el, "Paragraph", {"Type": ptype})
    if isinstance(runs, str):
        runs = [(runs, False, False)]
    for text, bold, italic in runs:
        style = _style_attr(bold, italic)
        t = ET.SubElement(p, "Text", {"Style": style} if style else {})
        t.text = text


def _append_plate_note(content_el, img_tag) -> None:
    """An inline image/plate becomes a visible bracketed Action note — never a
    base64 dump (FDX cannot carry the image; a silent drop would violate the
    no-silent-loss rule)."""
    caption = _image_caption(img_tag)
    note = f"[Plate: {caption}]" if caption else "[Plate: untitled illustration]"
    _append_paragraph(content_el, "Action", note)


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_fdx(content: str, chapters: list = None, title: str = "Manuscript Title",
                 author: str = "Author Name", output_format: str = "chicago",
                 cover_image: str = None) -> io.BytesIO:
    """Final Draft .fdx: <TitlePage> with title/author, then the manuscript as
    Scene Heading (chapters) + Action (prose) paragraphs with Bold/Italic Text
    runs. Wording preserved verbatim. ``chapters``, ``output_format`` and
    ``cover_image`` are accepted for signature parity with the other
    ``generate_*`` exporters; structure is derived from the content HTML
    itself (headings), and FDX has no cover/house-style concept.

    Returns an ``io.BytesIO`` seeked to 0 containing UTF-8 XML with declaration.
    """
    soup = BeautifulSoup(content or "", "html.parser")
    _strip_toc(soup)
    _strip_frontmatter_blocks(soup, title, author)

    title_text = (title or "").strip() or "Untitled Manuscript"
    author_text = (author or "").strip()

    root = ET.Element("FinalDraft", {
        "DocumentType": "Script",
        "Template": "No",
        "Version": "1",
    })
    body = ET.SubElement(root, "Content")

    for node in soup.find_all(_BLOCK_TAGS):
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                _append_plate_note(body, img)
            continue
        text = _clean(node.get_text()).strip()
        if not text:
            continue
        if node.name in ("h1", "h2", "h3"):
            # Chapter → Scene Heading: keeps chapters as navigable landmarks in
            # Final Draft's Scene Navigator (see module docstring for rationale).
            _append_paragraph(body, "Scene Heading", text)
        else:
            if text in _SCENE_BREAK_MARKS:
                _append_paragraph(body, "Action", "* * *")
                continue
            runs = _merge_runs(_inline_runs(node))
            if runs:
                _append_paragraph(body, "Action", runs)
            for img in _block_images(node):
                _append_plate_note(body, img)

    # A manuscript that is bare text (no block tags) must not silently export
    # as an empty script — carry the text through as one Action paragraph.
    if len(body) == 0:
        stray = _clean(soup.get_text()).strip()
        if stray:
            _append_paragraph(body, "Action", stray)

    # Title page: Final Draft reads <TitlePage><Content> with centered
    # paragraphs (title, blank, "by", author).
    title_page = ET.SubElement(root, "TitlePage")
    tp_content = ET.SubElement(title_page, "Content")

    def _tp_line(text: str) -> None:
        p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Center"})
        t = ET.SubElement(p, "Text")
        t.text = text

    _tp_line(title_text)
    if author_text:
        _tp_line("")
        _tp_line("by")
        _tp_line(author_text)

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding="UTF-8", xml_declaration=True)
    buf.seek(0)
    return buf
