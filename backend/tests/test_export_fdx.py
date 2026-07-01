"""Final Draft (.fdx) export: valid FDX XML with title page, Scene Heading
chapters, Action prose, Bold/Italic Text runs, and lossless special chars.
Calls generate_fdx directly (the module is not yet routed); output is parsed
with ElementTree, matching how Final Draft itself would read it."""
import io
import xml.etree.ElementTree as ET

from services.export_fdx import VALID_PARAGRAPH_TYPES, generate_fdx

_BOOK = {
    "content": (
        "<h1>The Lighthouse</h1><p>by Jane Doe</p>"
        "<h1>Chapter One: The Arrival</h1><p>The keeper counted the ships.</p>"
        "<h1>Chapter Two: The Storm</h1><p>The wind rose to a scream.</p>"
    ),
    "chapters": [
        {"suggested_title": "Chapter One: The Arrival", "display_page": 1},
        {"suggested_title": "Chapter Two: The Storm", "display_page": 5},
    ],
    "title": "The Lighthouse",
    "author": "Jane Doe",
}


def _root(**overrides):
    """Run the exporter and parse its stream back into an Element."""
    kwargs = {**_BOOK, **overrides}
    stream = generate_fdx(
        kwargs["content"],
        chapters=kwargs.get("chapters"),
        title=kwargs["title"],
        author=kwargs["author"],
    )
    assert isinstance(stream, io.BytesIO), "exporter must return io.BytesIO"
    assert stream.tell() == 0, "stream must be seeked to 0"
    return ET.parse(stream).getroot()


def _body_paragraphs(root):
    """The script-body paragraphs (direct <Content>, not the <TitlePage> one)."""
    return root.find("Content").findall("Paragraph")


def _para_text(p):
    return "".join(t.text or "" for t in p.findall("Text"))


def test_fdx_stream_has_xml_declaration_and_root_attrs():
    raw = generate_fdx(**{k: v for k, v in _BOOK.items() if k != "chapters"}).getvalue()
    assert raw.startswith(b"<?xml"), "XML declaration missing"
    assert b"UTF-8" in raw.split(b"\n", 1)[0].upper(), "declaration must state UTF-8"
    root = ET.fromstring(raw)
    assert root.tag == "FinalDraft"
    assert root.get("DocumentType") == "Script"
    assert root.get("Template") == "No"
    assert root.get("Version") == "1"
    assert root.find("Content") is not None, "script <Content> missing"


def test_fdx_title_page_has_title_and_author():
    root = _root()
    tp = root.find("TitlePage")
    assert tp is not None, "<TitlePage> missing"
    lines = [_para_text(p) for p in tp.find("Content").findall("Paragraph")]
    assert "The Lighthouse" in lines, f"title missing from title page: {lines}"
    assert "by" in lines and "Jane Doe" in lines, f"author block missing: {lines}"


def test_fdx_chapters_become_scene_headings_and_prose_becomes_action():
    root = _root()
    paras = _body_paragraphs(root)
    headings = [_para_text(p) for p in paras if p.get("Type") == "Scene Heading"]
    actions = [_para_text(p) for p in paras if p.get("Type") == "Action"]
    assert headings == ["Chapter One: The Arrival", "Chapter Two: The Storm"]
    assert "The keeper counted the ships." in actions
    assert "The wind rose to a scream." in actions
    # Every emitted paragraph type must be one Final Draft recognizes.
    assert all(p.get("Type") in VALID_PARAGRAPH_TYPES for p in paras), \
        [p.get("Type") for p in paras]


def test_fdx_strips_duplicated_frontmatter_title_block():
    """The manuscript's own leading title/author block must not become bogus
    scene headings — the title belongs to <TitlePage> only."""
    root = _root()
    body_texts = [_para_text(p) for p in _body_paragraphs(root)]
    assert "The Lighthouse" not in body_texts, "title duplicated into script body"
    assert "by Jane Doe" not in body_texts, "author line duplicated into script body"


def test_fdx_bold_italic_style_runs():
    content = (
        "<h1>Chapter One</h1>"
        "<p>Plain then <strong>bold</strong> then <em>italic</em> then "
        "<strong><em>both</em></strong> end.</p>"
    )
    root = _root(content=content, title="Styles", author="Tester")
    action = next(p for p in _body_paragraphs(root) if p.get("Type") == "Action")
    runs = [(t.get("Style"), t.text or "") for t in action.findall("Text")]
    assert (None, "Plain then ") == runs[0]
    assert ("Bold", "bold") in runs, runs
    assert ("Italic", "italic") in runs, runs
    assert ("Bold+Italic", "both") in runs, runs
    # Reassembled paragraph preserves the exact wording, spaces included.
    assert _para_text(action) == "Plain then bold then italic then both end."


def test_fdx_special_chars_survive_round_trip():
    sentence = "Fish & Chips <cost> 5 > 4 — “smart quotes” and ‘apostrophes’ stay."
    content = f"<h1>Chapter One</h1><p>{sentence.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</p>"
    root = _root(content=content, title="Chars & Co", author="Tester")
    actions = [_para_text(p) for p in _body_paragraphs(root) if p.get("Type") == "Action"]
    assert sentence in actions, f"special chars mangled: {actions}"
    # The title attribute path must escape correctly too (title holds an '&').
    tp_lines = [_para_text(p) for p in root.find("TitlePage").find("Content").findall("Paragraph")]
    assert "Chars & Co" in tp_lines


def test_fdx_inline_image_becomes_bracketed_note_never_base64():
    plate = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    content = (
        "<h1>Chapter One</h1>"
        "<p>Before the plate.</p>"
        f'<figure><img src="{plate}" alt="ignored"/>'
        "<figcaption>Plate I: The harbor at dawn</figcaption></figure>"
        f'<p>A photo follows.<img src="{plate}" alt="Storm clouds gather"/></p>'
    )
    raw = generate_fdx(content, title="Plates", author="Tester").getvalue()
    text = raw.decode("utf-8")
    assert "base64" not in text and "data:image" not in text, "base64 leaked into FDX"
    root = ET.fromstring(raw)
    actions = [_para_text(p) for p in _body_paragraphs(root) if p.get("Type") == "Action"]
    assert "[Plate: Plate I: The harbor at dawn]" in actions, actions
    assert "[Plate: Storm clouds gather]" in actions, actions
    assert "Before the plate." in actions and "A photo follows." in actions, \
        "prose around plates dropped"


def test_fdx_scene_break_marker_normalized():
    content = "<h1>Chapter One</h1><p>Before.</p><p>***</p><p>After.</p>"
    root = _root(content=content, title="Breaks", author="Tester")
    actions = [_para_text(p) for p in _body_paragraphs(root) if p.get("Type") == "Action"]
    assert "* * *" in actions, "scene break marker lost"
    assert "Before." in actions and "After." in actions


def test_fdx_bare_text_content_not_silently_dropped():
    """Content with no block tags still exports its text (one Action para)."""
    root = _root(content="Just a bare sentence.", title="Bare", author="Tester")
    actions = [_para_text(p) for p in _body_paragraphs(root) if p.get("Type") == "Action"]
    assert actions == ["Just a bare sentence."]


def test_fdx_signature_parity_ignores_format_and_cover():
    """output_format / cover_image are accepted (parity with generate_*) and
    must not change or break the output."""
    a = generate_fdx(_BOOK["content"], title=_BOOK["title"], author=_BOOK["author"]).getvalue()
    b = generate_fdx(
        _BOOK["content"], chapters=_BOOK["chapters"], title=_BOOK["title"],
        author=_BOOK["author"], output_format="penguin",
        cover_image="data:image/jpeg;base64,AAAA",
    ).getvalue()
    assert a == b, "format/cover params must be inert for FDX"
