"""
[TEXT FORMATTER]: Pure functions for RTF manipulation and text cleanup.

No side effects, no state access — these are freely unit-testable.
Handles RTF stripping, text flow restoration, manuscript marker processing,
and paragraph-joining heuristics.
"""
import re

from .artifact_steward import to_rtf  # noqa: F401 — re-export for backward compat


def strip_rtf(content: str) -> str:
    """[SURGICAL CLEANSE]: Aggressively strips RTF tags from any block, regardless of positioning."""
    if not content or "{\\rtf" not in content:
        return content

    # 1. Identify the RTF boundaries
    start_idx = content.find("{\\rtf")
    if start_idx == -1:
        return content

    end_idx = content.rfind("}")
    if end_idx == -1:
        end_idx = len(content)
    else:
        end_idx += 1

    rtf_block = content[start_idx:end_idx]
    pre_rtf = content[:start_idx]
    post_rtf = content[end_idx:]

    # 2. Aggressive Header Strip
    text = re.sub(r'\{\\rtf1.*?\\fs\d+\s?', '', rtf_block, flags=re.DOTALL)
    if text == rtf_block:
        text = re.sub(r'\{\\rtf1(?:\{.*?\})*', '', rtf_block, flags=re.DOTALL)

    # 3. Handle Control Words and Formatting
    text = text.replace('\\par\n', '\n\n').replace('\\par', '\n\n')
    text = re.sub(r'\\(?:[a-z]{1,32})(-?\d+)?\s?', ' ', text)

    # 4. Handle Unicode escapes \uN?
    def decode_unicode(match):
        try:
            return chr(int(match.group(1)))
        except Exception:
            return match.group(0)
    text = re.sub(r'\\u(\d+)\?', decode_unicode, text)

    # 5. Final Unescape and cleanup
    text = text.replace('\\\\', '\\').replace('\\{', '{').replace('\\}', '}')
    text = text.strip()
    if text.endswith("}"):
        text = text[:-1]

    # [INTEGRITY]: Reassemble
    result = pre_rtf + text + post_rtf
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def restore_text_flow_if_fragmented(text: str) -> str:
    """[FLOW RESTORATION]: Detects if a page has an EOL on every line, and merges them to restore text flow."""
    if not text:
        return ""

    blocks = re.split(r'\n+', text.strip())
    if len(blocks) < 3:
        return text

    non_terminating_count = 0
    for block in blocks[:-1]:
        if block and block[-1] not in '.?!"\':;':
            non_terminating_count += 1

    if (non_terminating_count / len(blocks)) > 0.4:
        # [POETRY DEFENSE]: Short lines = intentional formatting
        avg_len = sum(len(b) for b in blocks) / len(blocks)
        if avg_len < 45:
            return text
        merged = re.sub(r'([^.?!"\'\:\;])\s*\n+\s*([a-zA-Z0-9\(\[\"\'\-])', r'\1 \2', text)
        return merged

    return text


def check_and_strip_manuscript_markers(text: str) -> str:
    """[DIRECTORIAL CLEANSE]: Audits markers for continuity and strips tags on-the-fly for the editor."""
    if not text:
        return ""

    marker_pattern = r'(--- \[PAGE START: page_(\d+)\.rtf\] ---)'
    matches = list(re.finditer(marker_pattern, text))

    if not matches:
        return strip_rtf(text)

    # Extract numbers and check for continuity
    nums = [int(m.group(2)) for m in matches]
    # is_sequential check unused but kept for future audit use
    # is_sequential = all(nums[i] == nums[i-1] + 1 for i in range(1, len(nums)))

    segments = []

    # Include the preamble
    preamble = text[:matches[0].start()].strip()
    if preamble:
        segments.append(preamble)

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        block_content = text[start:end].strip()
        clean_block = strip_rtf(content=block_content)

        current_num = int(match.group(2))
        prev_num = int(matches[i - 1].group(2)) if i > 0 else (current_num - 1)

        if current_num == prev_num + 1:
            segments.append(clean_block)
        else:
            segments.append(match.group(1))
            segments.append(clean_block)

    return "\n\n".join(s for s in segments if s.strip()).strip()


def _should_join_paragraphs(prev_text: str, next_text: str) -> bool:
    """Intelligent safeguard to prevent Chapter Headings and short titles from being merged."""
    prev = prev_text.strip()
    if not prev:
        return False

    if re.search(r'[.?!:"\'\)\]]$', prev):
        return False

    if len(prev) < 60:
        return False

    if re.search(r'\d+$', prev) and len(prev) < 100:
        return False

    if re.match(r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)', prev, re.I):
        return False

    if prev.isupper() and len(prev) > 3:
        return False

    return True
