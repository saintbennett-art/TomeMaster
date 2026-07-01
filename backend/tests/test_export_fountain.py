"""Fountain export: title page keys, per-chapter sections, emphasis conversion,
misparse escaping, and plate placeholders (never base64)."""
import base64
import io
import re

from services.export_fountain import generate_fountain


_BOOK = {
    "content": (
        "<h1>The Lighthouse</h1><p>by Jane Doe</p>"
        "<h1>Chapter One: The Arrival</h1><p>The keeper counted the ships.</p>"
        "<h1>Chapter Two: The Storm</h1><p>The wind rose to a scream.</p>"
    ),
    "title": "The Lighthouse",
    "author": "Jane Doe",
}


def _render(content, **kw):
    args = {"title": _BOOK["title"], "author": _BOOK["author"], **kw}
    buf = generate_fountain(content, chapters=[], output_format="chicago", **args)
    assert isinstance(buf, io.BytesIO)
    assert buf.tell() == 0, "stream must be seeked to 0"
    return buf.getvalue().decode("utf-8")


def test_title_page_keys_lead_the_document():
    text = _render(_BOOK["content"])
    lines = text.split("\n")
    assert lines[0] == "Title: The Lighthouse"
    assert lines[1] == "Author: Jane Doe"
    assert re.fullmatch(r"Draft date: \d{4}-\d{2}-\d{2}", lines[2]), lines[2]
    assert lines[3] == "", "title page must end with a blank line"


def test_each_chapter_becomes_a_section():
    text = _render(_BOOK["content"])
    assert "# Chapter One: The Arrival" in text
    assert "# Chapter Two: The Storm" in text
    # The manuscript's own leading title/author block is stripped: the title
    # appears only in the Title: key, never as a duplicate section.
    assert "# The Lighthouse" not in text
    assert text.count("The Lighthouse") == 1
    # Prose paragraphs survive verbatim as action.
    assert "The keeper counted the ships." in text
    assert "The wind rose to a scream." in text


def test_heading_levels_map_to_section_depth():
    text = _render("<h1>Part One</h1><h2>Chapter One</h2><h3>Scene A</h3>")
    assert "# Part One" in text
    assert "## Chapter One" in text
    assert "### Scene A" in text


def test_emphasis_converts_to_fountain_markup():
    text = _render(
        "<h1>Chapter One</h1>"
        "<p>He read the <em>Herald</em> and felt <strong>nothing</strong> at all.</p>"
    )
    assert "*Herald*" in text
    assert "**nothing**" in text
    assert "He read the *Herald* and felt **nothing** at all." in text


def test_literal_asterisks_and_underscores_are_escaped():
    text = _render("<h1>Chapter One</h1><p>He typed *stars* and snake_case aloud.</p>")
    assert r"\*stars\*" in text
    assert r"snake\_case" in text


def test_all_caps_line_is_escaped_as_literal_action():
    text = _render("<h1>Chapter One</h1><p>HE SCREAMED HER NAME INTO THE DARK.</p>")
    assert "!HE SCREAMED HER NAME INTO THE DARK." in text


def test_scene_heading_lookalike_is_escaped():
    text = _render(
        "<h1>Chapter One</h1>"
        "<p>INT. HOUSE - DAY was scrawled across the first page of her script.</p>"
    )
    assert "!INT. HOUSE - DAY was scrawled across the first page of her script." in text


def test_forcing_lead_characters_are_escaped():
    text = _render(
        "<h1>Chapter One</h1>"
        "<p>.45 caliber, he said.</p>"
        "<p># is what she typed first.</p>"
        "<p>&gt; and so the quote began.</p>"
    )
    assert "!.45 caliber, he said." in text
    assert "!# is what she typed first." in text
    assert "!> and so the quote began." in text


def test_ellipsis_lead_is_not_escaped():
    text = _render("<h1>Chapter One</h1><p>...and then the lights went out.</p>")
    assert "\n...and then the lights went out." in text
    assert "!..." not in text


def test_normal_prose_is_not_escaped():
    text = _render(_BOOK["content"])
    assert "!The keeper" not in text
    assert "!The wind" not in text


def test_plates_become_notes_never_base64():
    plate = "data:image/png;base64," + base64.b64encode(b"\x89PNG fakebytes").decode()
    text = _render(
        "<h1>Chapter One</h1>"
        "<p>The keeper counted the ships.</p>"
        f'<figure><img src="{plate}" alt="ignored"/>'
        "<figcaption>Plate I: The harbor at dawn</figcaption></figure>"
        f'<p>A photo follows.<img src="{plate}" alt="Storm clouds gather"/></p>'
    )
    assert "[[Plate: Plate I: The harbor at dawn]]" in text
    assert "[[Plate: Storm clouds gather]]" in text
    assert "base64" not in text, "plates must never be dumped as base64"


def test_cover_and_output_format_are_ignored_for_parity():
    with_extras = generate_fountain(
        _BOOK["content"], chapters=[], title=_BOOK["title"], author=_BOOK["author"],
        output_format="penguin", cover_image="data:image/jpeg;base64,AAAA",
    ).getvalue()
    without = generate_fountain(
        _BOOK["content"], chapters=[], title=_BOOK["title"], author=_BOOK["author"],
    ).getvalue()
    assert with_extras == without


def test_untitled_and_authorless_manuscript():
    text = _render("<p>Just one paragraph.</p>", title="", author="")
    lines = text.split("\n")
    assert lines[0] == "Title: Untitled Manuscript"
    assert not any(l.startswith("Author:") for l in lines)
    assert "Just one paragraph." in text


def test_output_is_utf8_and_ends_with_newline():
    raw = generate_fountain(
        "<h1>Chapter One</h1><p>Café — “quotes” stay verbatim.</p>",
        chapters=[], title="T", author="A",
    ).getvalue()
    text = raw.decode("utf-8")  # raises on bad encoding
    assert "Café — “quotes” stay verbatim." in text
    assert text.endswith("\n")
