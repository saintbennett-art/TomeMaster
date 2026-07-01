"""ODT export round-trip: generate, unzip the package, parse content.xml and
assert title page / chapters / inline formatting / plates are really there.
(An .odt is a zip of XML parts: mimetype, content.xml, styles.xml, manifest.)"""
import base64
import io
import xml.etree.ElementTree as ET
import zipfile

import pytest

from services.export_odt import generate_odt

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
}


def _tiny_cover():
    """A small valid JPEG data-URL, generated via Pillow, used as a cover."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (120, 180), (30, 50, 110)).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _tiny_plate(color=(200, 60, 60)):
    """A small valid PNG data-URL used as an inline manuscript plate/figure."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


_PLATE_FIG_CAPTION = "Plate I: The harbor at dawn"
_PLATE_ALT_CAPTION = "Storm clouds gather"

_BOOK = {
    "content": (
        "<h1>The Lighthouse</h1><p>by Jane Doe</p>"
        "<h1>Chapter One: The Arrival</h1>"
        "<p>The keeper counted <strong>forty</strong> ships in the <em>grey</em> dawn.</p>"
        "<p>***</p>"
        "<h1>Chapter Two: The Storm</h1><p>The wind rose to a scream.</p>"
    ),
    "chapters": [
        {"suggested_title": "Chapter One: The Arrival", "display_page": 1},
        {"suggested_title": "Chapter Two: The Storm", "display_page": 5},
    ],
    "title": "The Lighthouse",
    "author": "Jane Doe",
    "output_format": "chicago",
}


def _book_with_plates():
    plate1 = _tiny_plate((200, 60, 60))
    plate2 = _tiny_plate((60, 120, 200))
    content = (
        "<h1>The Lighthouse</h1><p>by Jane Doe</p>"
        "<h1>Chapter One: The Arrival</h1>"
        "<p>The keeper counted the ships.</p>"
        f'<figure><img src="{plate1}" alt="ignored"/>'
        f"<figcaption>{_PLATE_FIG_CAPTION}</figcaption></figure>"
        "<p>Then he climbed the stairs.</p>"
        "<h1>Chapter Two: The Storm</h1>"
        f'<p>A photo follows.<img src="{plate2}" alt="{_PLATE_ALT_CAPTION}"/></p>'
        "<p>The wind rose to a scream.</p>"
    )
    return {**_BOOK, "content": content, "cover_image": _tiny_cover()}


def _generate(**overrides):
    args = {**_BOOK, **overrides}
    return generate_odt(
        args["content"], chapters=args.get("chapters"), title=args["title"],
        author=args["author"], output_format=args.get("output_format", "chicago"),
        cover_image=args.get("cover_image"),
    )


def _open(stream):
    return zipfile.ZipFile(io.BytesIO(stream.getvalue()))


def _content_root(z):
    return ET.fromstring(z.read("content.xml"))


def _all_text(root):
    return "".join(root.itertext())


# ─── Package validity ─────────────────────────────────────────────────────────

def test_odt_returns_seeked_stream_and_valid_package():
    stream = _generate()
    assert isinstance(stream, io.BytesIO)
    assert stream.tell() == 0, "stream must be seeked to 0"
    data = stream.getvalue()
    assert len(data) > 500, "ODT stream suspiciously small"
    with _open(stream) as z:
        assert z.read("mimetype") == b"application/vnd.oasis.opendocument.text", \
            "wrong ODF mimetype"
        names = z.namelist()
        assert "content.xml" in names and "styles.xml" in names
        assert "META-INF/manifest.xml" in names
        _content_root(z)  # must be well-formed XML
        ET.fromstring(z.read("styles.xml"))


# ─── Title page / front matter ────────────────────────────────────────────────

def test_odt_title_page_author_and_no_duplicate_title():
    with _open(_generate()) as z:
        text = _all_text(_content_root(z))
        # Manuscript's own leading title block is stripped → title appears
        # exactly once (on the generated title page), like the DOCX export.
        assert text.count("The Lighthouse") == 1, "title missing or duplicated"
        assert "by Jane Doe" in text, "author line missing"


def test_odt_title_page_never_suppressed():
    stream = _generate(content="<p>Body text only.</p>", title="Smoke Test",
                       author="Tester", chapters=[])
    with _open(stream) as z:
        text = _all_text(_content_root(z))
        assert "Smoke Test" in text, "title page suppressed"
        assert "Body text only." in text, "body wording not preserved"


# ─── Chapters: real outline headings + static Contents page ──────────────────

def test_odt_chapters_are_outline_level_1_headings():
    with _open(_generate()) as z:
        root = _content_root(z)
        heads = root.findall(".//text:h", _NS)
        head_texts = ["".join(h.itertext()) for h in heads]
        assert "Chapter One: The Arrival" in head_texts, "chapter not a text:h heading"
        assert "Chapter Two: The Storm" in head_texts
        for h in heads:
            assert h.get(f"{{{_NS['text']}}}outline-level") == "1", \
                "chapter heading must be outline level 1"
        # Headings start a new page: their style declares fo:break-before="page".
        style_names = {h.get(f"{{{_NS['text']}}}style-name") for h in heads}
        styles_xml = z.read("styles.xml").decode("utf-8", "replace")
        assert len(style_names) == 1
        assert 'break-before="page"' in styles_xml, "chapter page break missing"


def test_odt_contents_page_lists_chapters():
    with _open(_generate()) as z:
        text = _all_text(_content_root(z))
        assert "Contents" in text, "Contents page missing"
        # Each chapter title appears twice: Contents entry + body heading.
        assert text.count("Chapter One: The Arrival") == 2, "chapter missing from Contents"
        assert text.count("Chapter Two: The Storm") == 2


# ─── Inline formatting ────────────────────────────────────────────────────────

def test_odt_preserves_bold_and_italic_spans():
    with _open(_generate()) as z:
        root = _content_root(z)
        spans = {
            ("".join(s.itertext())): s.get(f"{{{_NS['text']}}}style-name")
            for s in root.findall(".//text:span", _NS)
        }
        assert spans.get("forty"), "bold run lost its span"
        assert spans.get("grey"), "italic run lost its span"
        assert spans["forty"] != spans["grey"], "bold and italic map to one style"
        styles_xml = z.read("styles.xml").decode("utf-8", "replace")
        assert f'style:name="{spans["forty"]}"' in styles_xml
        assert 'font-weight="bold"' in styles_xml, "bold character style missing"
        assert 'font-style="italic"' in styles_xml, "italic character style missing"


def test_odt_scene_break_renders_centered_hash():
    with _open(_generate()) as z:
        text = _all_text(_content_root(z))
        assert "#" in text, "scene-break marker dropped"
        assert "***" not in text, "scene break not normalized to '#'"


# ─── output_format: chicago vs penguin (font + line spacing) ─────────────────

def test_odt_chicago_uses_times_double_spacing():
    with _open(_generate(output_format="chicago")) as z:
        styles_xml = z.read("styles.xml").decode("utf-8", "replace")
        assert "Times New Roman" in styles_xml, "chicago font missing"
        assert 'line-height="200%"' in styles_xml, "chicago double spacing missing"


def test_odt_penguin_uses_garamond_150_spacing():
    with _open(_generate(output_format="penguin")) as z:
        styles_xml = z.read("styles.xml").decode("utf-8", "replace")
        assert "Garamond" in styles_xml, "penguin font missing"
        assert 'line-height="150%"' in styles_xml, "penguin 1.5 spacing missing"
        assert 'line-height="200%"' not in styles_xml.replace(
            'line-height="150%"', ""), "penguin body must not be double spaced"


# ─── Cover + inline plates ────────────────────────────────────────────────────

def test_odt_embeds_cover_and_plates_with_captions():
    with _open(generate_odt(**{
        "content": _book_with_plates()["content"],
        "chapters": [],
        "title": "The Lighthouse",
        "author": "Jane Doe",
        "output_format": "chicago",
        "cover_image": _tiny_cover(),
    })) as z:
        pics = [n for n in z.namelist() if n.startswith("Pictures/")]
        # cover (jpeg) + 2 plates (png)
        assert len(pics) >= 3, f"images not embedded in ODT: {pics}"
        assert sum(n.lower().endswith(".png") for n in pics) >= 2, "plate PNGs missing"
        manifest = z.read("META-INF/manifest.xml").decode("utf-8", "replace")
        for n in pics:
            assert n in manifest, f"{n} not declared in manifest"
        root = _content_root(z)
        # Each embedded picture is referenced by a draw:image inside a frame.
        images = root.findall(".//draw:image", _NS)
        hrefs = {img.get("{http://www.w3.org/1999/xlink}href") for img in images}
        assert len(images) >= 3, "draw:image references missing from content"
        assert hrefs <= set(pics) and len(hrefs) >= 3, "image hrefs don't match package parts"
        text = _all_text(root)
        assert _PLATE_FIG_CAPTION in text, "figure caption missing"
        assert _PLATE_ALT_CAPTION in text, "alt-derived caption missing"


def test_odt_malformed_plate_is_surfaced_not_silently_dropped():
    content = (
        "<h1>Chapter One: The Arrival</h1>"
        "<p>Before.</p>"
        '<figure><img src="data:image/png;base64,NOT_VALID_BASE64=="/></figure>'
        "<p>After.</p>"
    )
    stream = generate_odt(content, chapters=[], title="Broken Plate", author="Tester")
    with _open(stream) as z:
        text = _all_text(_content_root(z))
        assert "could not be embedded" in text, "malformed plate not surfaced"
        assert "Before." in text and "After." in text, "export aborted around bad plate"
        assert not [n for n in z.namelist() if n.startswith("Pictures/")], \
            "malformed plate must not embed bytes"
