"""Fountain (.fountain) export — self-contained, portable module.

Converts a prose manuscript (editor HTML) into the plain-text Fountain
screenplay format (https://fountain.io/syntax):

- Title page:   ``Title:`` / ``Author:`` / ``Draft date:`` key lines.
- Chapters:     each h1/h2/h3 becomes a Fountain Section (``#`` / ``##`` / ``###``).
- Prose:        each paragraph becomes an Action block (blank-line separated).
- Inline:       <em>/<i> → *italic*, <strong>/<b> → **bold**, <u> → _underline_;
                literal ``*`` ``_`` ``\\`` in prose are backslash-escaped so
                wording survives verbatim through a Fountain parser.
- Misparse guard: any action line a Fountain parser would read as another
  element (scene heading ``INT./EXT.``, an ALL-CAPS character cue/transition,
  or a line starting with ``. ! @ ~ = # >``) is prefixed with the Fountain
  literal-action escape ``!``.
- Images:       inline plates are never dumped as base64 — each becomes a
  visible Fountain note ``[[Plate: <caption>]]`` so nothing silently vanishes.

Dependencies: Python stdlib + BeautifulSoup (bs4) only. No imports from the
rest of the application, so the module is reusable as-is in other projects.
"""

import io
import re
from datetime import date

from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
# Text hygiene
# ---------------------------------------------------------------------------

def _clean_text(s: str) -> str:
    """Drop zero-width spaces and normalize non-breaking spaces."""
    return s.replace("​", "").replace("\xa0", " ")


# Characters Fountain treats as inline emphasis / escape markers. Escaping the
# backslash itself first (it is in the class) keeps literal prose intact.
_INLINE_MARKERS = re.compile(r"([\\*_])")


def _escape_inline_text(s: str) -> str:
    """Backslash-escape literal ``*``, ``_`` and ``\\`` in prose so a Fountain
    parser renders them as characters instead of emphasis markup."""
    return _INLINE_MARKERS.sub(r"\\\1", _clean_text(s))


def _wrap_emphasis(inner: str, marker: str) -> str:
    """Wrap ``inner`` in an emphasis marker, hoisting boundary whitespace
    outside the markers — Fountain emphasis is invalid when the marker is
    followed/preceded by a space (``* word *`` does not parse)."""
    m = re.match(r"^(\s*)(.*?)(\s*)$", inner, re.S)
    lead, core, trail = m.groups()
    if not core:
        return inner
    return f"{lead}{marker}{core}{marker}{trail}"


# ---------------------------------------------------------------------------
# Inline HTML → Fountain markup
# ---------------------------------------------------------------------------

def _inline_to_fountain(node) -> str:
    """Render a node's inline children to Fountain emphasis, preserving exact
    wording. Squiggle/span wrappers collapse to their plain text; <br> becomes
    a hard line break inside the action block; <img> is skipped here because
    plates are emitted separately as visible notes."""
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(_escape_inline_text(str(child)))
        elif isinstance(child, Tag):
            if child.name == "br":
                parts.append("\n")
                continue
            if child.name == "img":
                continue
            inner = _inline_to_fountain(child)
            if child.name in ("strong", "b"):
                parts.append(_wrap_emphasis(inner, "**"))
            elif child.name in ("em", "i"):
                parts.append(_wrap_emphasis(inner, "*"))
            elif child.name == "u":
                parts.append(_wrap_emphasis(inner, "_"))
            else:
                parts.append(inner)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Misparse guard: force Action with the Fountain `!` escape when needed
# ---------------------------------------------------------------------------

# INT / EXT / EST / INT./EXT / I/E followed by a dot or space opens a scene heading.
_SCENE_HEADING = re.compile(r"^(INT|EXT|EST|INT\.?/EXT|I/E)[.\s]", re.I)

# Leading characters that force other Fountain elements:
#   .  scene heading   !  action (would consume a literal '!')   @  character
#   ~  lyric           =  synopsis / page break                  #  section
#   >  transition / centered text
_FORCING_LEADS = ".!@~=#>"


def _line_would_misparse(stripped: str) -> bool:
    """True when a bare action line would be read as a different Fountain
    element and therefore needs the ``!`` literal-action prefix."""
    if not stripped:
        return False
    lead = stripped[0]
    if lead in _FORCING_LEADS:
        # A leading '.' only forces a scene heading when NOT followed by
        # another '.' — an ellipsis ("...and then") is already plain action.
        if lead == "." and stripped.startswith(".."):
            return False
        return True
    if _SCENE_HEADING.match(stripped):
        return True
    # An all-uppercase line reads as a character cue (or a TO: transition).
    if stripped.upper() == stripped and any(ch.isalpha() for ch in stripped):
        return True
    return False


def _guard_action_line(line: str) -> str:
    stripped = line.strip()
    if _line_would_misparse(stripped):
        return "!" + line
    return line


def _paragraph_to_action(node) -> str:
    """One <p> → one Fountain Action block, each physical line escape-guarded."""
    rendered = _inline_to_fountain(node)
    lines = [_guard_action_line(ln) for ln in rendered.split("\n")]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Block-level walk (mirrors the contract of the sibling exporters)
# ---------------------------------------------------------------------------

_BLOCK_TAGS = ["h1", "h2", "h3", "p", "div", "figure", "img"]
_SECTION_DEPTH = {"h1": "#", "h2": "##", "h3": "###"}


def _is_nested_block(node) -> bool:
    """True when ``node``'s rendering is already owned by an ancestor block we
    also iterate (an <img> inside a <p>/<figure>, a <p> inside a <div>, …)."""
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
    """True when a block is purely plate(s): a bare <img>, a <figure> (its text
    is the caption), or a block whose only non-whitespace content is images."""
    name = getattr(node, "name", None)
    if name == "img":
        return True
    if not _block_images(node):
        return False
    if name == "figure":
        return True
    return not _clean_text(node.get_text()).strip()


def _image_caption(img_tag) -> str:
    """Caption for an <img>: the wrapping <figure>'s <figcaption> if present,
    else the ``alt`` / ``title`` attribute. '' when none."""
    fig = img_tag.find_parent("figure")
    if fig is not None:
        cap = fig.find("figcaption")
        if cap is not None:
            t = _clean_text(cap.get_text()).strip()
            if t:
                return t
    for attr in ("alt", "title"):
        v = _clean_text(img_tag.get(attr) or "").strip()
        if v:
            return v
    return ""


def _plate_note(img_tag) -> str:
    """One inline plate as a visible Fountain note — never a base64 dump."""
    caption = _image_caption(img_tag) or "image"
    # ']]' inside the caption would close the note early; soften it.
    caption = caption.replace("]]", "] ]")
    return f"[[Plate: {caption}]]"


def _strip_leading_frontmatter(soup, title: str, author: str) -> None:
    """Drop the manuscript's own leading title/author block so it is not
    duplicated under the generated Fountain title page. Conservative: only
    removes leading blocks that look like a title page, then stops at the
    first real chapter heading or body paragraph."""
    title_l = _clean_text(title or "").strip().lower()
    author_l = _clean_text(author or "").strip().lower()
    removed = 0
    for node in list(soup.find_all(["h1", "h2", "h3", "p", "div"])):
        if not getattr(node, "name", None) or not node.parent:
            continue
        text = _clean_text(node.get_text()).strip()
        if not text:
            node.decompose()
            continue
        t_lower = text.lower()
        is_title = bool(title_l) and t_lower == title_l
        is_author = bool(author_l) and t_lower in (author_l, f"by {author_l}")
        is_by_line = t_lower in ("by", "by:", "by-")
        is_label = t_lower in ("title page", "titlepage")
        if removed < 4 and (is_title or is_author or is_by_line or is_label):
            node.decompose()
            removed += 1
            continue
        break


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_fountain(content: str, chapters: list = None, title: str = "Manuscript Title",
                      author: str = "Author Name", output_format: str = "chicago",
                      cover_image: str = None) -> io.BytesIO:
    """Fountain .fountain export: title page (Title/Author/Draft date keys),
    each chapter heading as a Section, prose paragraphs as Action blocks with
    HTML emphasis converted and misparse-prone lines escaped with ``!``.

    ``output_format`` and ``cover_image`` are accepted for signature parity
    with the other exporters and intentionally ignored: Fountain has no cover
    or typography concept. Returns a UTF-8 io.BytesIO positioned at 0.
    """
    soup = BeautifulSoup(content or "", "html.parser")
    editor_toc = soup.find("div", class_="editor-toc")
    if editor_toc:
        editor_toc.decompose()
    _strip_leading_frontmatter(soup, title, author)

    title_text = _clean_text(title or "").strip() or "Untitled Manuscript"
    author_text = _clean_text(author or "").strip()

    lines = [f"Title: {title_text}"]
    if author_text:
        lines.append(f"Author: {author_text}")
    lines.append(f"Draft date: {date.today().isoformat()}")
    lines.append("")

    for node in soup.find_all(_BLOCK_TAGS):
        if _is_nested_block(node):
            continue
        if _block_has_only_images(node):
            for img in _block_images(node):
                lines.append(_plate_note(img))
                lines.append("")
            continue
        text = _clean_text(node.get_text()).strip()
        if not text:
            continue
        if node.name in _SECTION_DEPTH:
            lines.append(f"{_SECTION_DEPTH[node.name]} {text}")
            lines.append("")
        else:  # p / div prose block
            if text in ("***", "* * *", "#"):
                # Scene break: centered separator (spaces around the asterisks
                # keep Fountain from reading them as emphasis markers).
                lines.append("> * * * <")
                lines.append("")
                continue
            action = _paragraph_to_action(node)
            if action:
                lines.append(action)
                lines.append("")
            for img in _block_images(node):
                lines.append(_plate_note(img))
                lines.append("")

    fountain = "\n".join(lines).rstrip() + "\n"
    return io.BytesIO(fountain.encode("utf-8"))
