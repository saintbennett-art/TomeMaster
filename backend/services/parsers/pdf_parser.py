"""
PDF parser — native text extraction with Vision OCR fallback.

Imports fitz (PyMuPDF), PIL, and OpenAI only when called.
"""

import re
import io
import os
import base64

from .text_utils import (
    _is_heading_candidate,
    _should_join_paragraphs,
    _split_merged_headings,
    _mop_up_noise,
    _normalize_typography,
)


# ─── Vision OCR Prompt ────────────────────────────────────────────────────────


def _get_redline_prompt():
    """Fetched dynamically from the specialist registry."""
    from services.ai.specialist_registry import get_specialist_config

    return get_specialist_config("Vision OCR")["template"]


# ─── Blue-Ink Deletion Detection ─────────────────────────────────────────────


def _is_light_blue(color):
    """Detects if a color (tuple of 3 floats) is in the Light Blue/Cyan spectrum."""
    if not color or len(color) < 3:
        return False
    r, g, b = color
    return b > 0.6 and b > r and b > g


# ─── Page-Level Extraction ────────────────────────────────────────────────────


def _get_page_content_purged(page):
    """Extracts text from a page, skipping words that intersect with blue 'INK' or 'HIGHLIGHT' annotations.
    Preserves structural line and block breaks using dictionary mode."""
    import fitz

    # 1. Detection Phase: Identify Blue Deletion Zones
    annots = page.annots()
    blue_rects = []
    if annots:
        for annot in annots:
            if annot.type[0] in [8, 15]:
                if _is_light_blue(
                    annot.colors.get("stroke")
                ) or _is_light_blue(annot.colors.get("fill")):
                    if annot.rect.width > 10 and annot.rect.height > 10:
                        blue_rects.append(annot.rect)

    # 2. Extraction Phase: Iterate through blocks and lines to preserve prose flow
    text_dict = page.get_text("dict")

    dots_counts = 0

    final_blocks = []
    for b in text_dict["blocks"]:
        if b["type"] != 0:
            continue

        block_lines = []
        for l in b["lines"]:
            line_text = ""
            for s in l["spans"]:
                s_text = s["text"]
                s_rect = fitz.Rect(s["bbox"])

                if re.search(r"\.{3,}|(?:\s\.\s){2,}", s_text) or re.search(
                    r"\d+$", s_text.strip()
                ):
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
                        line_text += (
                            " "
                            if line_text and not line_text.endswith(" ")
                            else ""
                        ) + s_text
                else:
                    line_text += (
                        " "
                        if line_text and not line_text.endswith(" ")
                        else ""
                    ) + s_text

            if line_text.strip():
                block_lines.append(line_text.strip())

        if block_lines:
            final_blocks.append("\n\n".join(block_lines))

    if dots_counts > 4:
        return ""

    return _mop_up_noise("\n\n".join(final_blocks))


# ─── Full PDF Parse ───────────────────────────────────────────────────────────


def parse_pdf_smart(content: bytes, api_key: str = "") -> dict:
    """Intelligently parses PDF using native text scraping if available,
    falling back to Vision OCR for pure image scans."""
    import fitz
    from PIL import Image

    pdf_doc = fitz.open(stream=content, filetype="pdf")

    # Heuristic: Does the PDF have a native digital text layer?
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

            collected_text += page_content + "\n\n"

            first_line = page_content.split("\n")[0].strip()
            if len(first_line) < 100 and len(first_line) > 0:
                toc.append(
                    {
                        "title": first_line,
                        "style": "pdf-page-marker",
                        "page_number": page_num + 1,
                    }
                )

        full_text = collected_text.strip()

        clean_content = re.sub(r"(?<!\n)\n(?!\n)", " ", full_text)
        paragraphs = [
            p.strip()
            for p in re.split(r"\n{2,}", clean_content)
            if p.strip()
        ]

        html_fragments = [f"<p>{p}</p>" for p in paragraphs]

    else:
        # PATH B: VISION OCR
        from services.settings_service import get_preferred_model

        provider = "gemini"
        model = get_preferred_model("vision")

        if not api_key:
            from dotenv import load_dotenv

            load_dotenv()
            openai_key = os.getenv("OPENAI_API_KEY", "")
            gemini_key = os.getenv("GEMINI_API_KEY", "")

            if gemini_key:
                api_key = gemini_key
                provider = "gemini"
            elif openai_key:
                api_key = openai_key
                provider = "openai"
                model = "gpt-4o"

        if not api_key:
            raise ValueError(
                "Missing API Key for Manuscript Vision Analysis. "
                "Please configure your Vault."
            )

        from services.transcriber_service import _get_ai_client

        client = _get_ai_client(provider, api_key)

        collected_text = ""
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            if provider == "gemini":
                response = client.models.generate_content(
                    model=model, contents=[_get_redline_prompt(), img]
                )
                raw_text = response.text
            else:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=90)
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": _get_redline_prompt(),
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=2500,
                )
                raw_text = response.choices[0].message.content

            text_match = re.search(
                r"<text>(.*?)</text>", raw_text, re.DOTALL
            )
            if text_match:
                page_content = text_match.group(1).strip()
                if "output this placeholder text" in page_content:
                    page_content = ""
                if "[BLANK_PAGE]" in page_content:
                    page_content = ""

                page_content = _split_merged_headings(page_content)

                if collected_text and not collected_text.endswith("\n\n"):
                    collected_text += "\n\n"
                collected_text += page_content + "\n\n"

                first_line = page_content.split("\n")[0].strip()
                if len(first_line) < 100 and len(first_line) > 0:
                    toc.append(
                        {
                            "title": first_line,
                            "style": "pdf-page-marker",
                            "page_number": page_num + 1,
                        }
                    )

        full_text = collected_text.strip()

        paragraphs = [
            p.strip() for p in re.split(r"\n+", full_text) if p.strip()
        ]

        if paragraphs:
            current_p = paragraphs[0]
            for i in range(1, len(paragraphs)):
                next_p = paragraphs[i]
                if _should_join_paragraphs(current_p, next_p):
                    current_p += " " + next_p
                else:
                    tag = (
                        "h1"
                        if _is_heading_candidate(current_p)
                        else "p"
                    )
                    html_fragments.append(f"<{tag}>{current_p}</{tag}>")
                    current_p = next_p
            tag = "h1" if _is_heading_candidate(current_p) else "p"
            html_fragments.append(f"<{tag}>{current_p}</{tag}>")

    pdf_doc.close()

    html = f"<div class='pdf-manuscript'>{''.join(html_fragments)}</div>"

    return {
        "text": _normalize_typography(full_text.strip()),
        "html": _normalize_typography(html),
        "toc": toc,
    }


# ─── Streaming PDF Parse ─────────────────────────────────────────────────────


def stream_pdf_smart(
    content: bytes,
    api_key: str = "",
    is_demo: bool = False,
    folder_path: str = None,
):
    """Streams a PDF, automatically choosing between native text or Vision OCR per page."""
    import json
    import fitz
    from PIL import Image

    pdf_doc = fitz.open(stream=content, filetype="pdf")
    total_pages = len(pdf_doc)

    limit = 20 if is_demo else total_pages
    total_pages = limit

    yield json.dumps(
        {"type": "status", "message": "Inhaling PDF document..."}
    ) + "\n"

    sample_text = ""
    for i in range(min(10, total_pages)):
        sample_text += _get_page_content_purged(
            pdf_doc.load_page(i)
        ).strip()

    if len(sample_text) > 150:
        yield json.dumps(
            {
                "type": "status",
                "message": "Native text layer detected! Transcribing lightning fast!",
            }
        ) + "\n"
        tail_buffer = ""
        for page_num in range(total_pages):
            page_content = _get_page_content_purged(
                pdf_doc.load_page(page_num)
            ).strip()

            if not page_content:
                page_content = ""

            if tail_buffer:
                if _should_join_paragraphs(tail_buffer, page_content):
                    page_content = tail_buffer + " " + page_content
                else:
                    yield json.dumps(
                        {
                            "type": "page",
                            "page": page_num,
                            "html": f"<p>{tail_buffer}</p>",
                            "text": tail_buffer,
                        }
                    ) + "\n"

            paragraphs = [
                p.strip()
                for p in re.split(r"\n+", page_content)
                if p.strip()
            ]

            if not paragraphs:
                tail_buffer = ""
                continue

            tail_buffer = paragraphs.pop()

            if paragraphs:
                page_html = "".join(
                    [
                        f"<h1>{p}</h1>"
                        if _is_heading_candidate(p)
                        else f"<p>{p}</p>"
                        for p in paragraphs
                    ]
                )
                yield json.dumps(
                    {
                        "type": "page",
                        "page": page_num + 1,
                        "total_pages": total_pages,
                        "html": page_html,
                        "text": "\n\n".join(paragraphs),
                    }
                ) + "\n"

        if tail_buffer:
            yield json.dumps(
                {
                    "type": "page",
                    "page": total_pages,
                    "html": f"<p>{tail_buffer}</p>",
                    "text": tail_buffer,
                }
            ) + "\n"

    else:
        # VISION OCR PATH
        provider = "gemini"
        model = "gemini-1.5-pro"

        if not api_key:
            from dotenv import load_dotenv

            load_dotenv()
            openai_key = os.getenv("OPENAI_API_KEY", "")
            gemini_key = os.getenv("GEMINI_API_KEY", "")

            if gemini_key:
                api_key = gemini_key
                provider = "gemini"
            elif openai_key:
                api_key = openai_key
                provider = "openai"
                model = "gpt-4o"

        if not api_key:
            yield json.dumps(
                {
                    "type": "error",
                    "message": "Missing API Key for Vision Analysis.",
                }
            ) + "\n"
            return

        from services.transcriber_service import _get_ai_client

        client = _get_ai_client(provider, api_key)

        tail_buffer = ""
        for page_num in range(total_pages):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes(
                "RGB", [pix.width, pix.height], pix.samples
            )

            if provider == "gemini":
                response = client.models.generate_content(
                    model=model, contents=[_get_redline_prompt(), img]
                )
                raw_text = response.text
                from services.logger_service import log_api_usage

                metrics = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "candidates_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
                log_api_usage(
                    f"OCR Page {page_num + 1}",
                    provider,
                    model,
                    metrics,
                    folder_path,
                )
            else:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=90)
                img_b64 = base64.b64encode(buffered.getvalue()).decode(
                    "utf-8"
                )

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": _get_redline_prompt(),
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=2500,
                )

                from services.logger_service import log_api_usage

                metrics = {
                    "total_tokens": response.usage.total_tokens
                }
                log_api_usage(
                    f"OCR Page {page_num + 1}",
                    provider,
                    model,
                    metrics,
                    folder_path,
                )

                raw_text = response.choices[0].message.content

            text_match = re.search(
                r"<text>(.*?)</text>", raw_text, re.DOTALL
            )
            if text_match:
                page_content = text_match.group(1).strip()
                if "[BLANK_PAGE]" in page_content:
                    page_content = ""

                page_content = _split_merged_headings(page_content)

                if tail_buffer:
                    if _should_join_paragraphs(tail_buffer, page_content):
                        page_content = tail_buffer + " " + page_content
                    else:
                        yield json.dumps(
                            {
                                "type": "page",
                                "page": page_num,
                                "html": f"<p>{tail_buffer}</p>",
                                "text": tail_buffer,
                            }
                        ) + "\n"

                paragraphs = [
                    p.strip()
                    for p in re.split(r"\n+", page_content)
                    if p.strip()
                ]

                if not paragraphs:
                    tail_buffer = ""
                    continue

                tail_buffer = paragraphs.pop()
                if paragraphs:
                    page_html = "".join(
                        [
                            f"<h1>{p}</h1>"
                            if _is_heading_candidate(p)
                            else f"<p>{p}</p>"
                            for p in paragraphs
                        ]
                    )
                    yield json.dumps(
                        {
                            "type": "page",
                            "page": page_num + 1,
                            "total_pages": total_pages,
                            "html": page_html,
                            "text": "\n\n".join(paragraphs),
                        }
                    ) + "\n"

        if tail_buffer:
            yield json.dumps(
                {
                    "type": "page",
                    "page": total_pages,
                    "html": f"<p>{tail_buffer}</p>",
                    "text": tail_buffer,
                }
            ) + "\n"

    pdf_doc.close()
    yield json.dumps(
        {"type": "done", "message": "Compilation complete!"}
    ) + "\n"
