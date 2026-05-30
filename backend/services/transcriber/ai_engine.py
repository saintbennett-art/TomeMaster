"""
[AI ENGINE]: OCR-specific LLM client factory and failover protocol.

Sits on top of the gateway-level ai_service.py — this handles the
vision-specific API calls (base64 image payloads, OCR prompts)
with multi-provider failover for the transcription pipeline.
"""
import os
import io
import base64
import asyncio

from PIL import Image


# ─── OCR PROMPTS ──────────────────────────────────────────────────

OCR_PROMPT = """
[SOVEREIGN TRANSCRIBER PROTOCOL]
Digitize the provided physical manuscript pages with absolute fidelity.

STRICT FORMATTING MANDATES:
1. ABSOLUTE VERBATIM ACCURACY: You must transcribe every single word exactly as written. DO NOT PARAPHRASE. DO NOT SUMMARIZE. DO NOT CORRECT GRAMMAR. DO NOT EDIT.
2. CONTINUOUS PROSE: Every paragraph must be a single, continuous, flowing block. Do NOT insert line breaks (\\n) at the physical paper boundaries.
3. STRUCTURAL SEPARATION: Use exactly a DOUBLE NEWLINE (\\n\\n) to separate distinct paragraphs.
4. TYPOGRAPHICAL STANDARDS: Use standard straight apostrophes (') and straight double quotes (") exclusively. No 'smart' quotes.
5. NO CHOPPY LINES: Maintain sentence continuity across line wraps.
6. PAGE NUMBER ISOLATION: You MUST completely strip the physical page number out of the <text> output. Put the page number ONLY in the <number> tag.
7. POETRY & LYRICS: IF and ONLY IF the page content is clearly a poem, song lyric, or list with intentional short lines, preserve the line breaks exactly. Otherwise, for standard prose, default to Continuous flowing paragraphs.

SYSTEMIC VALIDATION:
- Identify and extract the page number from the header/footer.
- OMIT any text intersected by light blue highlighter squiggles or ink marks (DELETION ZONES). Do not add placeholders.

ENCAPSULATION:
Output the transcription within XML-style <page> and <text> tags.
"""

MANUSCRIPT_REDLINE_PROMPT = """
[SOVEREIGN OCR ENGINE]
Digitize the provided manuscript scans with absolute fidelity.

STRICT FORMATTING MANDATES:
1. ABSOLUTE VERBATIM ACCURACY: You must transcribe every single word exactly as written. DO NOT PARAPHRASE. DO NOT SUMMARIZE. DO NOT CORRECT GRAMMAR. DO NOT EDIT.
2. CONTINUOUS PROSE: Maintain paragraph integrity as a single flowing string. Do NOT match physical page-edge line breaks.
3. STRUCTURAL SEPARATION: Use exactly a DOUBLE NEWLINE (\\n\\n) after any chapter heading and between paragraphs.
4. TYPOGRAPHICAL STANDARDS: Use standard straight apostrophes (') and straight double quotes (") exclusively. No 'smart' quotes.
5. PAGE NUMBER ISOLATION: You MUST completely strip the physical page number out of the <text> output. Put the page number ONLY in the <number> tag.
6. POETRY & LYRICS: IF and ONLY IF the page content is clearly a poem, song lyric, or list with intentional short lines, preserve the line breaks exactly. Otherwise, for standard prose, default to Continuous flowing paragraphs.

SYSTEMIC VALIDATION:
- Locate the page number at the header or footer. If illegible, set <number> to "UNKNOWN" and inject `[DIRECTORIAL ALERT: ILLEGIBLE PAGE NUMBER]`.
- IF BLANK: Output [BLANK_PAGE].
- DELETION ZONES: OMIT any text covered by light blue highlighter squiggles or ink marks. No placeholders.

ENCAPSULATION:
Output the transcription within XML-style <page> and <text> tags.
"""


# ─── CLIENT FACTORY ───────────────────────────────────────────────

def _get_ai_client(provider: str, api_key: str):
    """Sovereign Handshake Factory: Generates the requested AI client with prioritized credential resolution."""
    if provider == "gemini":
        from google import genai
        return genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY", ""))
    elif provider in ["openai", "groq"]:
        from openai import OpenAI
        base_url = "https://api.groq.com/openai/v1" if provider == "groq" else None
        key = api_key or os.environ.get("GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY", "")
        return OpenAI(api_key=key, base_url=base_url)
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""))
    return None


# ─── FAILOVER PROTOCOL ───────────────────────────────────────────

async def _call_ai_with_failover(
    img, primary_provider, primary_model, primary_key,
    fallback_provider=None, fallback_model=None
):
    """Spectrum Failover Protocol: Attempts execution with primary engine, gears-down to fallback on failure."""

    max_retries = 3
    last_err = None

    for attempt in range(max_retries):
        providers = [(primary_provider, primary_model, primary_key)]
        if fallback_provider and fallback_model:
            providers.append((fallback_provider, fallback_model, None))

        for prov, mod, key in providers:
            try:
                # [VISION GUARD]: Skip known non-vision models
                blind_keywords = ["versatile", "instant", "text", "instruct", "preview-text"]
                if prov == "groq" and any(k in mod.lower() for k in blind_keywords):
                    continue

                print(f"BOARDROOM PULSE: Engaging {prov}:{mod} (Attempt {attempt + 1}/{max_retries})...")
                client = _get_ai_client(prov, key)
                if not client:
                    continue

                if prov == "gemini":
                    payload = [OCR_PROMPT, img]
                    response = client.models.generate_content(model=mod, contents=payload)
                    return response.text, prov, mod
                else:
                    # OpenAI / Groq / Anthropic path
                    buffered = io.BytesIO()
                    with img.copy() as ocr_img:
                        ocr_img.thumbnail((2048, 2048))
                        ocr_img.save(buffered, format="JPEG", quality=85)
                    b64_payload = base64.b64encode(buffered.getvalue()).decode("utf-8")

                    if prov == "anthropic":
                        res = client.messages.create(
                            model=mod,
                            max_tokens=2500,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": OCR_PROMPT},
                                    {"type": "image", "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": b64_payload,
                                    }},
                                ],
                            }],
                        )
                        return res.content[0].text, prov, mod
                    else:
                        res = client.chat.completions.create(
                            model=mod,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a professional manuscript transcriber. Output in XML format: <page><number>PAGENUM</number><text>TRANSCRIPT</text></page>",
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": OCR_PROMPT},
                                        {"type": "image_url", "image_url": {
                                            "url": f"data:image/jpeg;base64,{b64_payload}"
                                        }},
                                    ],
                                },
                            ],
                            temperature=0.1,
                            max_tokens=2500,
                        )
                        return res.choices[0].message.content, prov, mod
            except Exception as e:
                print(f"[FAILOVER ALERT]: {prov}:{mod} failed -> {str(e)}")
                last_err = str(e)
                continue

        # [BACKOFF]: Wait if the entire spectrum failed
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2
            print(f"BOARDROOM: Spectrum Total Saturation. Cool-down: {wait_time}s...")
            await asyncio.sleep(wait_time)

    raise Exception(f"Boardroom Blackout: All assigned engines saturated. Last error: {last_err}")
