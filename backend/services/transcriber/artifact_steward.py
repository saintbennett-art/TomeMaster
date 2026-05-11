import os
import re
import time
import json
import tempfile

def to_rtf(text: str) -> str:
    """Converts plain text to a high-fidelity Unicode RTF string (Word Compatible)."""
    rtf_header = r"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times New Roman;}}\f0\fs24 "
    
    def rtf_encode_char(c):
        codepoint = ord(c)
        if codepoint < 128:
            if c == '\\': return '\\\\'
            if c == '{': return '\\{'
            if c == '}': return '\\}'
            return c
        else:
            return f'\\u{codepoint}?'

    escaped_text = "".join(rtf_encode_char(c) for c in text)
    processed = re.sub(r'\*\*(.*?)\*\*', r'\\b \1\\b0 ', escaped_text)
    processed = re.sub(r'\*(.*?)\*', r'\\i \1\\i0 ', processed)
    processed = processed.replace('\n', '\\par\n')
    return rtf_header + processed + "}"

def save_page_artifact(folder_path: str, page_num: str, text: str, source_file: str, physical_index: int = None) -> bool:
    """Universal physical handshake: writes a tangible RTF file via a safe local temp zone."""
    try:
        if physical_index is not None:
            rtf_name = f"page_{physical_index}.rtf"
        else:
            safe_num = re.sub(r'[\\/*?:"<>|]', '_', str(page_num)).strip()
            file_basename = os.path.splitext(os.path.basename(source_file))[0]
            rtf_name = f"page_{safe_num}.rtf" if safe_num.lower() != "unknown" else f"UNKNOWN_{file_basename}.rtf"
        
        rtf_path = os.path.join(folder_path, rtf_name)
        
        success = False
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.rtf', encoding='utf-8') as tf:
            temp_path = tf.name
            tf.write(to_rtf(text))
            tf.flush()
            os.fsync(tf.fileno())

        max_retries = 5
        for i in range(max_retries):
            try:
                if os.path.exists(rtf_path):
                    os.replace(temp_path, rtf_path)
                else:
                    os.rename(temp_path, rtf_path)
                success = True
                break
            except PermissionError:
                if i < max_retries - 1:
                    time.sleep(0.5)
                continue
            except Exception as e:
                break

        if not success and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass

        return success
    except Exception:
        return False
