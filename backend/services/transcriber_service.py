import os
import asyncio
import subprocess
import glob
import time
import json
import threading
import traceback
import base64
import io
import re
from pathlib import Path
from PIL import Image
try:
    import webview
except ImportError:
    webview = None
import fitz # PyMuPDF for Systemic PDF Extraction
import shutil
import datetime
from .logger_service import log_api_usage as _log_api_usage
from .transcriber import asset_scanner, vision_processor, artifact_steward

# [MIGRATED]: Sequence logic moved to transcriber.asset_scanner
natural_sort_key = asset_scanner.natural_sort_key
industrial_sort_key = natural_sort_key
extract_sequence_number = asset_scanner.extract_sequence_number

# [LEDGER]: Standard filename for project state and history tracking
TRANSCRIPTION_STATE_FILE = "project_ledger.json"

# [SOVEREIGN CONFIG]: Tesseract OCR disabled due to low-fidelity results on manuscript handwriting.

# Shared state for frontend polling
TRANSCRIPTION_LOCK = threading.Lock()
TRANSCRIPTION_STATE = {
    "status": "idle", # 'idle', 'running', 'complete', 'error'
    "total_images": 0,
    "processed_images": 0,
    "current_batch": 0,
    "total_batches": 0,
    "text": None,
    "error_message": None,
    "current_image_b64": None,
    "current_extracted_text": None,
    "is_new_chunk": False,
    "page_audits": [],
    "mode": "batch", # 'live' or 'batch'
    "offset_delta": 0,
    "waiting_for_input": False,
    "last_processed_file": None,
    "stream_buffer": [], # Stores newest pages for lightweight frontend streaming
    "folder": None,
    "missing_pages_count": 0,
    "diary": [] # [DIARY]: Persistent history of project milestones
}

TRANSCRIPTION_ARTIFACTS_DIR = "Archive"

# Tracks whether a stitching thread is actually running in THIS process.
# Unlike the ledger status (which persists across restarts), this is always
# False at boot — prevents stale "stitching" ledger entries from blocking re-runs.
_stitching_active = threading.Event()

def log_to_diary(message: str):
    """[DIARY]: Records a milestone to the project ledger for contextual guidance."""
    global TRANSCRIPTION_STATE
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": timestamp, "message": message}
    
    if "diary" not in TRANSCRIPTION_STATE:
        TRANSCRIPTION_STATE["diary"] = []
    
    TRANSCRIPTION_STATE["diary"].append(entry)
    TRANSCRIPTION_STATE["error_message"] = message
    save_persistent_state()

def save_persistent_state():
    """[LEDGER]: Commits the current project state and diary to the local ledger."""
    global TRANSCRIPTION_STATE
    folder = TRANSCRIPTION_STATE.get("folder")
    if not folder or not os.path.exists(folder): return
    
    ledger_path = os.path.join(folder, TRANSCRIPTION_STATE_FILE)
    try:
        # Capture current reality
        data = {k: v for k, v in TRANSCRIPTION_STATE.items() if k not in ["current_image_b64", "stream_buffer"]}
        
        # [SOVEREIGN DNA FOUNDATION]: Preserve the author's voice in the physical ledger
        from .style_mirror import MIRROR
        data["authorial_dna"] = MIRROR.dna
        
        with open(ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"LEDGER ERROR: Failed to commit state: {e}")

def load_persistent_state(folder_path: str):
    """[LEDGER]: Instant Hydration - Recovers the absolute truth from the local ledger."""
    global TRANSCRIPTION_STATE
    ledger_path = os.path.join(folder_path, TRANSCRIPTION_STATE_FILE)
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                TRANSCRIPTION_STATE.update(saved)
                TRANSCRIPTION_STATE["folder"] = folder_path
                
                # [SOVEREIGN DNA RECOVERY]: Hydrate the Style Mirror with the author's persistent voice
                if "authorial_dna" in saved:
                    from .style_mirror import MIRROR
                    MIRROR.load_dna(saved["authorial_dna"])
                
                # [EFFICIENCY]: If the ledger says we are done, tell the engine to skip the re-scan
                if TRANSCRIPTION_STATE.get("status") == "complete" and TRANSCRIPTION_STATE.get("text"):
                    print("LEDGER: Instant Hydration Complete. Manuscript delivered.")
                    return True
            return True
        except Exception as e:
            print(f"LEDGER ERROR: Could not read ledger: {e}")
    return False

# [MIGRATED]: RTF logic moved to transcriber.artifact_steward
to_rtf = artifact_steward.to_rtf

def strip_rtf(content: str) -> str:
    """[SURGICAL CLEANSE]: Aggressively strips RTF tags from any block, regardless of positioning."""
    if not content or "{\\rtf" not in content:
        return content
    
    # 1. Identify the RTF boundaries
    start_idx = content.find("{\\rtf")
    if start_idx == -1: return content
    
    end_idx = content.rfind("}")
    if end_idx == -1: end_idx = len(content)
    else: end_idx += 1
    
    rtf_block = content[start_idx:end_idx]
    pre_rtf = content[:start_idx]
    post_rtf = content[end_idx:]

    # 2. Aggressive Header Strip
    # We strip from {\rtf1 until we hit the first character that isn't a control word or group
    # This usually ends at \fs24 or \f0
    text = re.sub(r'\{\\rtf1.*?\\fs\d+\s?', '', rtf_block, flags=re.DOTALL)
    
    # If the above failed (no \fs tag), fallback to stripping all groups at the start
    if text == rtf_block:
        text = re.sub(r'\{\\rtf1(?:\{.*?\})*', '', rtf_block, flags=re.DOTALL)

    # 3. Handle Control Words and Formatting
    # Replace \par with double newline for paragraph integrity
    text = text.replace('\\par\n', '\n\n').replace('\\par', '\n\n')
    
    # Strip remaining generic control words \word or \wordN
    text = re.sub(r'\\(?:[a-z]{1,32})(-?\d+)?\s?', ' ', text)
    
    # 4. Handle Unicode escapes \uN?
    def decode_unicode(match):
        try:
            return chr(int(match.group(1)))
        except:
            return match.group(0)
    text = re.sub(r'\\u(\d+)\?', decode_unicode, text)
    
    # 5. Final Unescape and cleanup
    text = text.replace('\\\\', '\\').replace('\\{', '{').replace('\\}', '}')
    
    # Remove any trailing '}' from the RTF block closure
    text = text.strip()
    if text.endswith("}"):
        text = text[:-1]
    
    # [INTEGRITY]: Reassemble
    result = pre_rtf + text + post_rtf
    
    # Normalize structural spacing to prevent runaway newlines/EOF characters
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()

def restore_text_flow_if_fragmented(text: str) -> str:
    """[FLOW RESTORATION]: Detects if a page has an EOL on every line, and merges them to restore text flow."""
    if not text: return ""
    
    # Check if this text is heavily fragmented (EOL on almost every line without punctuation)
    # Split by double newlines (since strip_rtf converts \par to \n\n)
    blocks = re.split(r'\n+', text.strip())
    if len(blocks) < 3:
        return text # Not enough lines to be "fragmented"
        
    # Count how many blocks DO NOT end with sentence-terminating punctuation
    non_terminating_count = 0
    for block in blocks[:-1]: # exclude last block
        if block and block[-1] not in '.?!\"\':;':
            non_terminating_count += 1
            
    # If more than 40% of the blocks don't end in punctuation, it's a fragmented OCR page
    if (non_terminating_count / len(blocks)) > 0.4:
        # [POETRY DEFENSE]: Check average line length. 
        # If the average line length is very short (< 45 chars), it's likely intentional poetry or a list.
        avg_len = sum(len(b) for b in blocks) / len(blocks)
        if avg_len < 45:
            return text # Preserve intentional short-line formatting
            
        # Merge lines where the previous block doesn't end in punctuation
        merged = re.sub(r'([^.?!\"\'\:\;])\s*\n+\s*([a-zA-Z0-9\(\[\"\'\-])', r'\1 \2', text)
        return merged
        
    return text

def check_and_strip_manuscript_markers(text: str) -> str:
    """[DIRECTORIAL CLEANSE]: Audits markers for continuity and strips tags on-the-fly for the editor."""
    if not text: return ""
    
    # 1. Identify all page markers
    marker_pattern = r'(--- \[PAGE START: page_(\d+)\.rtf\] ---)'
    matches = list(re.finditer(marker_pattern, text))
    
    if not matches:
        # No markers, but still might be a raw RTF dump or already stripped
        return strip_rtf(text)
        
    # 2. Extract numbers and check for continuity
    nums = [int(m.group(2)) for m in matches]
    is_sequential = all(nums[i] == nums[i-1] + 1 for i in range(1, len(nums)))
    
    # 3. Split and process segments
    segments = []
    
    # Include the preamble (text before the first marker)
    preamble = text[:matches[0].start()].strip()
    if preamble:
        # Preamble might contain the document header
        segments.append(preamble)
        
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        
        # Extract and strip the content block
        block_content = text[start:end].strip()
        clean_block = strip_rtf(content=block_content)
        
        # [GRANULAR CONTINUITY]: Check if THIS page is sequential with the PREVIOUS one
        current_num = int(match.group(2))
        prev_num = int(matches[i-1].group(2)) if i > 0 else (current_num - 1)
        
        if current_num == prev_num + 1:
            # Sequential: Just add the clean prose (Industrial Stitching)
            segments.append(clean_block)
        else:
            # Gap Detected: Preserve the marker for directorial visibility
            segments.append(match.group(1))
            segments.append(clean_block)
            
    # 4. Reassemble with normalized spacing
    return "\n\n".join(s for s in segments if s.strip()).strip()

OCR_PROMPT = """
[SOVEREIGN TRANSCRIBER PROTOCOL]
Digitize the provided physical manuscript pages with absolute fidelity.

STRICT FORMATTING MANDATES:
1. ABSOLUTE VERBATIM ACCURACY: You must transcribe every single word exactly as written. DO NOT PARAPHRASE. DO NOT SUMMARIZE. DO NOT CORRECT GRAMMAR. DO NOT EDIT.
2. CONTINUOUS PROSE: Every paragraph must be a single, continuous, flowing block. Do NOT insert line breaks (\n) at the physical paper boundaries. 
3. STRUCTURAL SEPARATION: Use exactly a DOUBLE NEWLINE (\n\n) to separate distinct paragraphs.
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
3. STRUCTURAL SEPARATION: Use exactly a DOUBLE NEWLINE (\n\n) after any chapter heading and between paragraphs.
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

def _should_join_paragraphs(prev_text: str, next_text: str) -> bool:
    """Intelligent safeguard to prevent Chapter Headings and short titles from being merged."""
    prev = prev_text.strip()
    if not prev: return False
    
    # 1. Punctuation is King: If it ends in ANY punctuation, never join!
    if re.search(r'[.?!:"\'\)\]]$', prev):
        return False
        
    # 2. PROSE LENGTH RULE: Any line shorter than a full printed prose line (e.g. < 60 chars) 
    # is likely a Heading, Title, or Name. Don't join!
    if len(prev) < 60:
        return False
        
    # 2b. If it ends in a number (Page Number / TOC), don't join!
    if re.search(r'\d+$', prev) and len(prev) < 100:
        return False
        
    # 3. If it starts with common Chapter/Section markers, don't join!
    if re.match(r'^(Chapter|Prologue|Epilogue|Forward|Prelude|Author|Title|Subtitle|Part)', prev, re.I):
        return False
        
    # 4. If it's ALL CAPS, it's likely a heading. Don't join!
    if prev.isupper() and len(prev) > 3:
        return False
    return True



# [MIGRATED]: Artifact handshake moved to transcriber.artifact_steward
save_page_artifact = artifact_steward.save_page_artifact


# Global window foundation for native dialogs
UI_WINDOW = None

def pick_file(title="Select Manuscript File", extensions=None) -> str:
    """Summons the native Windows file picker with corrected extension handling."""
    global UI_WINDOW
    
    # Standard authorial extensions
    if not extensions:
        extensions = [
            ("Manuscript Files", "*.pdf;*.docx;*.txt;*.rtf;*.md;*.markdown"),
            ("All Files", "*.*")
        ]
    
    if UI_WINDOW and webview:
        try:
            # pywebview expects a list of descriptions with patterns in parens
            wv_types = [f"{desc} ({patt})" for desc, patt in extensions]
            result = UI_WINDOW.create_file_dialog(webview.OPEN_DIALOG, directory='', allow_multiple=False, file_types=wv_types)
            if result and len(result) > 0:
                return os.path.abspath(result[0]).replace('\\', '/')
            return None
        except Exception as e:
            print(f"Native Viewport File Picker Failure: {e}")
    
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        # tkinter expects a list of (description, pattern) tuples
        tk_types = [(desc, patt.replace(';', ' ')) for desc, patt in extensions]
        file_path = filedialog.askopenfilename(title=title, filetypes=tk_types)
        root.destroy()
        if file_path and os.path.exists(file_path):
            return os.path.abspath(file_path).replace('\\', '/')
        return None
    except Exception as e:
        print(f"Native File Picker Failure: {e}")
        return None

def pick_directory() -> str:
    """Summons the native Windows folder picker via the Boardroom Viewport or Tkinter."""
    global UI_WINDOW
    
    # [APEX DIALOG]: Use the native pywebview window if we are in the standalone app
    if UI_WINDOW and webview:
        try:
            result = UI_WINDOW.create_file_dialog(webview.FOLDER_DIALOG, directory='', save_filename='')
            if result and len(result) > 0:
                folder = result[0]
                if folder and os.path.exists(folder):
                    return os.path.abspath(folder).replace('\\', '/')
            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f'BOARDROOM CRITICAL: {str(e)}')
            print(f'Native Viewport Picker Failure: {e}')
            print(f"Native Viewport Picker Failure: {e}")
            # Fall through to Tkinter
    
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # [DIRECTORIAL ESTABLISHMENT]: Create a hidden root window
        root = tk.Tk()
        root.withdraw()
        
        # Bring to front
        root.attributes('-topmost', True)
        
        # Open the dialog
        folder = filedialog.askdirectory(title="Select TomeMaster Project Folder")
        
        # Cleanup
        root.destroy()
        
        if folder and os.path.exists(folder):
            return os.path.abspath(folder).replace('\\', '/')
        return None
    except Exception as e:
        print(f"BOARDROOM CRITICAL: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"Native Picker Failure: {e}")
        return None

# [DEPRECATED]: celery_app removed during CrewAI migration. Transcription is now
# triggered via TomeMasterPipeline in src/tomemaster/main.py. This function is
# retained as legacy reference only.
def run_transcription_job(api_key: str, folder_path: str, provider: str = "openai", reset_cache: bool = False, mode: str = "batch", model_override: str = None, fallback_provider: str = None, fallback_model: str = None):
    if not model_override:
        raise ValueError(f"Directorial Error: No model selected for {provider}. Please open the Vault and choose a commissioned model.")
    global TRANSCRIPTION_STATE
    try:
        # [PROCESS STEWARDSHIP]: Lower priority to prevent system bricking
        try:
            import psutil
            p = psutil.Process(os.getpid())
            if os.name == 'nt':
                # Windows 'Below Normal' priority
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                p.nice(10) # Unix positive nice value
            print("BOARDROOM: Resource Stewardship active. Background process deprioritized.")
        except:
            pass

        # [SOVEREIGN ESTABLISHMENT]: Normalize Windows paths immediately
        folder_path = os.path.abspath(folder_path).strip().replace('\\', '/')
        
        # [GOVERNANCE GUARD]: Determine true project root if established to a subfolder
        project_root = folder_path
        if project_root.rstrip('/').endswith(TRANSCRIPTION_ARTIFACTS_DIR):
            project_root = os.path.dirname(project_root.rstrip('/'))

        # [SOVEREIGN ROOT GUARD]: Prevent recursive artifact nesting
        if folder_path.rstrip('/').endswith(TRANSCRIPTION_ARTIFACTS_DIR):
            artifacts_path = folder_path
        else:
            artifacts_path = os.path.join(folder_path, TRANSCRIPTION_ARTIFACTS_DIR)

        # [PERSISTENCE ROOT]: Cache is stored in the PROJECT ROOT, keeping source folder pure
        cache_file = os.path.join(project_root, "_tome_master_cache.json")

        
        if provider == "gemini":
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY", "")
            
            if not api_key:
                TRANSCRIPTION_STATE["status"] = "error"
                TRANSCRIPTION_STATE["error_message"] = "Invalid or missing Gemini API Key."
                return
                
            from google import genai
            client = genai.Client(api_key=api_key)
            model_id = model_override
        elif provider == "groq":
            if not api_key:
                api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                TRANSCRIPTION_STATE["status"] = "error"
                TRANSCRIPTION_STATE["error_message"] = "Invalid or missing Groq API Key."
                return
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        else:
            # OpenAI Path (Default)
            if not api_key or not str(api_key).strip():
                api_key = os.environ.get("OPENAI_API_KEY", "")

            if not api_key or not str(api_key).strip():
                TRANSCRIPTION_STATE["status"] = "error"
                TRANSCRIPTION_STATE["error_message"] = "Invalid or missing OpenAI API Key."
                return

            from openai import OpenAI
            client = OpenAI(api_key=api_key)

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "status": "indexing",
                "processed_images": 0,
                "total_images": 0,
                "error_message": "Scanning directory for manuscript evidence..."
            })
        
        # [MODULAR INDEXING]: Delegate discovery and sequence sorting to the AssetScanner
        all_files, already_processed, files_needing_processing, cover_path, total_pages = asset_scanner.scan_manuscript_folder(
            folder_path, artifacts_path
        )
        total_files = len(all_files)
        total_images_target = total_pages
        
        if total_files == 0:
            TRANSCRIPTION_STATE["status"] = "error"
            TRANSCRIPTION_STATE["error_message"] = "Directorial Rejection: No manuscript evidence (JPG, PNG, or PDF) identified."
            return

        # [SOVEREIGN INGESTION]: Single-page processing for absolute transparency
        batch_size = 1
        total_batches = total_files
        
        # Load persistent caching state
        start_index = 0
        master_pages = []
        if reset_cache:
            print(f"BOARDROOM: Reset active. Wiping old progress for {folder_path}...")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    print(f"BOARDROOM ERROR: Failed to wipe cache: {e}")
        elif os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    master_pages = cache.get("pages", [])
            except Exception as e:
                print("Cache load failed, starting fresh:", e)

        # [HYDRATION]: Build a set of existing RTF artifacts (Root + Archive)
        existing_rtfs = set()
        for area in [folder_path, artifacts_path]:
            if os.path.exists(area):
                for rtf_file in glob.glob(os.path.join(area, "*.rtf")):
                    existing_rtfs.add(os.path.basename(rtf_file).lower())
        
        # Also check _manuscript_source subdirectory for legacy support
        src_subdir = os.path.join(folder_path, "_manuscript_source")
        if os.path.isdir(src_subdir):
            for rtf_file in glob.glob(os.path.join(src_subdir, "*.rtf")):
                existing_rtfs.add(os.path.basename(rtf_file).lower())
        
        files_needing_processing = 0
        missing_sample_names = []
        for i, f_path in enumerate(all_files):
            basename = os.path.basename(f_path)
            
            # [KISS SKIP]: Does page_{i}.rtf (or page_{i+1}.rtf) exist for this image index?
            rtf_name_0 = f"page_{i}.rtf"
            rtf_name_1 = f"page_{i+1}.rtf"
            if rtf_name_0.lower() in existing_rtfs or rtf_name_1.lower() in existing_rtfs:
                continue
            
            files_needing_processing += 1
            if len(missing_sample_names) < 10:
                missing_sample_names.append(basename)
        
        already_processed = total_files - files_needing_processing
        print(f"BOARDROOM: Index-to-Index Scan: {already_processed} files have RTFs, {files_needing_processing} files need processing")
        if missing_sample_names:
            print(f"BOARDROOM: Sample of missing files: {', '.join(missing_sample_names)}...")
        
        # [SOVEREIGN DETECTION]: Is this an Injection or a fresh build?
        manuscript_exists = os.path.exists(os.path.join(folder_path, "Unified_Manuscript.md"))
        status_msg = "Voice of TomeMaster: Industrial Patching sequence initiated. I am transcribing the new artifacts and surgically merging them into the existing manuscript coordinates. Stand by while I heal the document structure." if manuscript_exists and already_processed > 0 else "Voice of TomeMaster: Beginning full-spectrum transcription. I will digitize each page with absolute fidelity. Please stand by."

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "processed_images": already_processed,
                "total_images": total_images_target,
                "error_message": status_msg
            })
        
        # [SOVEREIGN AUTO-STITCH]: If 100% of files are already processed, leapfrog directly to completion
        if files_needing_processing == 0 and total_files > 0:
            print("BOARDROOM: Mission Complete detected. Executing Sequence-Based Physical Stitch...")
            resort_from_cache(folder_path)
            return

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "status": "running",
                "total_images": total_images_target,
                "processed_images": already_processed,
                "total_batches": total_images_target,
                "current_batch": already_processed,
                "text": None,
                "error_message": None,
                "current_image_b64": None,
                "mode": mode,
                "waiting_for_input": False
            })

        # [SOVEREIGN SKIP]: Build a high-speed set of already-indexed images
        processed_images_set = {p.get("source_file") for p in master_pages if p.get("source_file")}

        # [PERSISTENCE ROOT]: Cache is stored in the PROJECT ROOT, keeping source folder pure
        cache_file = os.path.join(project_root, "_tome_master_cache.json")
        print(f"BOARDROOM: Neural Cache Target: {cache_file}")

        async def _consumer(queue):
            while True:
                job = await queue.get()
                i, f_path = job
                
                # Check if we should pause for user input in Live Mode
                while TRANSCRIPTION_STATE.get("waiting_for_input"):
                    await asyncio.sleep(1)
                
                try:
                    # [MODULAR VISION]: Delegate asset unpacking and telemetry generation to VisionProcessor
                    images_to_process = vision_processor.process_asset(f_path, folder_path)
                    
                    if not images_to_process:
                        continue
                            
                    for img, label in images_to_process:
                        with TRANSCRIPTION_LOCK:
                            TRANSCRIPTION_STATE["current_image_b64"] = vision_processor.generate_telemetry(img)
                        
                        batch_start_time = time.time()
                        
                        try:
                            # Direct await instead of asyncio.run
                            raw_text, used_prov, used_mod = await _call_ai_with_failover(
                                img, provider, model_override, api_key,
                                fallback_provider=fallback_provider,
                                fallback_model=fallback_model
                            )
                            
                            metrics = {"total_tokens": 0}
                            duration = round(time.time() - batch_start_time, 2)
                            _log_api_usage("Transcriber", used_prov, used_mod, metrics, folder_path, duration)
                        except Exception as failover_e:
                            with TRANSCRIPTION_LOCK:
                                TRANSCRIPTION_STATE["status"] = "error"
                                TRANSCRIPTION_STATE["error_message"] = f"Spectrum Blackout: {str(failover_e)}"
                            return

                        with TRANSCRIPTION_LOCK:
                            TRANSCRIPTION_STATE["current_extracted_text"] = raw_text.strip()
                            TRANSCRIPTION_STATE["is_new_chunk"] = True
                            
                        pages = re.findall(r'<page>.*?</page>', raw_text, re.DOTALL)
                        for p_idx, p in enumerate(pages):
                            num_match = re.search(r'<number>(.*?)</number>', p, re.DOTALL)
                            text_match = re.search(r'<text>(.*?)</text>', p, re.DOTALL)
                            if num_match and text_match:
                                t_text = text_match.group(1).strip()
                                extracted_num = num_match.group(1).strip()
                                
                                 # [FIDELITY]: Use the filename's absolute sequence number for the artifact slot
                                final_page_num = str(extract_sequence_number(label) or i)
                                if extracted_num.isdigit() and not extract_sequence_number(label):
                                    # Fallback to AI's guess only if filename is opaque
                                    final_page_num = str(int(extracted_num) + TRANSCRIPTION_STATE["offset_delta"])

                                if save_page_artifact(folder_path, final_page_num, t_text, label, int(final_page_num)):
                                    page_data = {
                                        "extracted_page_number": final_page_num,
                                        "raw_extracted_number": extracted_num,
                                        "text": t_text,
                                        "preview": " ".join(t_text.split()[:10]) + "..." if t_text else "",
                                        "source_file": os.path.basename(label),
                                        "physical_index": int(final_page_num)
                                    }
                                    with TRANSCRIPTION_LOCK:
                                        master_pages.append(page_data)
                                else:
                                    print(f"BOARDROOM WARNING: Physical Save Failed for page {final_page_num}.")

                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["processed_images"] += 1
                        TRANSCRIPTION_STATE["last_processed_file"] = os.path.basename(label)
                        TRANSCRIPTION_STATE["error_message"] = f"Page {TRANSCRIPTION_STATE['processed_images']} of {total_images_target} digitized — {os.path.basename(label)}"
                        TRANSCRIPTION_STATE["pages"] = list(master_pages)
                        TRANSCRIPTION_STATE["page_audits"] = [
                            {"page": p.get("extracted_page_number", "?"), "preview": p.get("preview", ""), "source_file": p.get("source_file", "unknown")} 
                            for p in master_pages
                        ]
                    
                    try:
                        import threading
                        temp_cache = cache_file + f".tmp_{threading.get_ident()}"
                        with TRANSCRIPTION_LOCK:
                            master_pages_copy = list(master_pages)
                        
                        with open(temp_cache, "w", encoding="utf-8") as f:
                            json.dump({"processed_index": i + 1, "pages": master_pages_copy}, f)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        max_rename_retries = 5
                        for retry in range(max_rename_retries):
                            try:
                                if os.path.exists(cache_file):
                                    os.replace(temp_cache, cache_file)
                                else:
                                    os.rename(temp_cache, cache_file)
                                break
                            except PermissionError:
                                if retry == max_rename_retries - 1:
                                    print(f"BOARDROOM WARNING: Persistent Permission Denied on cache update.")
                                else:
                                    time.sleep(0.5)
                    except Exception as disk_e:
                        print(f"CRITICAL DISK ERROR: Failed to update cache. {disk_e}")
                    finally:
                        if os.path.exists(temp_cache):
                            try: os.remove(temp_cache)
                            except: pass
                    
                    try:
                        archive_dir = os.path.join(folder_path, TRANSCRIPTION_ARTIFACTS_DIR)
                        if not os.path.exists(archive_dir):
                            os.makedirs(archive_dir)
                        
                        dest_path = os.path.join(archive_dir, os.path.basename(label))
                        if os.path.exists(dest_path):
                            if os.path.exists(label):
                                os.remove(label)
                        else:
                            if os.path.exists(label):
                                shutil.move(label, dest_path)
                    except Exception as move_e:
                        print(f"BOARDROOM WARNING: Failed to archive image {label}: {move_e}")

                except Exception as loop_e:
                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["status"] = "error"
                        TRANSCRIPTION_STATE["error_message"] = str(loop_e)
                    print(f"BOARDROOM ERROR: Async worker exception: {loop_e}")
                finally:
                    queue.task_done()

        async def _async_orchestrator():
            queue = asyncio.Queue()
            jobs_queued = 0
            
            for i, f_path in enumerate(all_files):
                rtf_name_0 = f"page_{i}.rtf"
                rtf_name_1 = f"page_{i+1}.rtf"
                if rtf_name_0.lower() in existing_rtfs or rtf_name_1.lower() in existing_rtfs:
                    with TRANSCRIPTION_LOCK:
                        if TRANSCRIPTION_STATE["processed_images"] <= i:
                            TRANSCRIPTION_STATE["processed_images"] += 1
                            TRANSCRIPTION_STATE["current_batch"] += 1
                            if i % 10 == 0 or i == total_files - 1:
                                TRANSCRIPTION_STATE["error_message"] = f"Verified {i + 1} of {total_images_target} — {os.path.basename(f_path)} already sealed."
                    continue
                queue.put_nowait((i, f_path))
                jobs_queued += 1
                
            if jobs_queued == 0:
                return
                
            num_workers = min(3, jobs_queued)
            workers = [asyncio.create_task(_consumer(queue)) for _ in range(num_workers)]
            await queue.join()
            for w in workers:
                w.cancel()

        # [SOVEREIGN INGESTION]: Run the concurrent workers
        asyncio.run(_async_orchestrator())

        # [SOVEREIGN FINAL STITCH]: Unify all physical artifacts (0-498) into the editor
        print("BOARDROOM: Mission Success. Executing Final Physical Stitch...")
        resort_from_cache(folder_path)

    except Exception as e:
        print(f"BOARDROOM CRITICAL: Job Failure: {e}")
        import traceback
        traceback.print_exc()
        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["status"] = "error"
            TRANSCRIPTION_STATE["error_message"] = str(e)
    finally:
        # [SOVEREIGN RELEASE]: Always drop the lock to prevent system deadlocks
        print("BOARDROOM: Transcription Thread terminated. Releasing locks.")

def ingest_project_baseline(folder_path: str):
    """
    Directorial Pulse: Scans a folder on anchor to hydrate UI counters and Editor.
    Ends the 'Starting at 0' amnesia by recognizing existing work instantly.
    """
    global TRANSCRIPTION_STATE
    try:
        # [HUMAN PATHING]: Preserve native Windows formatting for display and discovery
        folder_path = os.path.normpath(folder_path.strip())
        
        # 0. State Recovery Attempt (Speed boost only, still requires full scan for accuracy)
        load_persistent_state(folder_path)
        
        # 1. Industrial Discovery (Root Only - Physical Reality)
        # [SOVEREIGN TRUST]: We only scan the root. No second-guessing by checking Archive.
        all_images = []
        root_rtf_names = []
        valid_exts = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
        
        if os.path.exists(folder_path):
            # Single High-Fidelity Scan
            for f in os.listdir(folder_path):
                f_lower = f.lower()
                if f_lower == "cover.jpg": continue
                ext = os.path.splitext(f_lower)[1]
                if ext in valid_exts:
                    all_images.append(os.path.join(folder_path, f))
                elif ext == ".rtf":
                    root_rtf_names.append(f)
        
        # [NATURAL SEQUENCE]: Sort images 1, 2, 3...
        all_images.sort(key=natural_sort_key)
        
        # [ZAP]: Physical Verification of Workstation State
        manuscript_path = os.path.join(folder_path, "Unified_Manuscript.md")
        lock_path = os.path.join(folder_path, "Unified_Manuscript.md.STITCH_LOCK")
        
        manuscript_exists = os.path.exists(manuscript_path)
        lock_exists = os.path.exists(lock_path)
        
        # [GAP DISCOVERY]: Count missing pages to signal the Industrial Scout
        missing_count = 0
        if manuscript_exists:
            try:
                with open(manuscript_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    missing_count = len(re.findall(r'\[DIRECTORIAL ALERT: PAGE \d+ MISSING', content))
            except: pass

        # [LEDGER LAW]: total_images is immutable — set once by transcription, never touched here.
        # Only missing_pages_count is updated from the physical manuscript scan.
        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["missing_pages_count"] = missing_count
            
        final_text = None
        new_status = "idle"
        
        # 4. Hydrate State via Sovereign Scenarios
        with TRANSCRIPTION_LOCK:
            if len(root_rtf_names) > 0:
                # [S2]: UNSEALED RTF ARTIFACTS IN ROOT — silent injection, no OCR required.
                print(f"BOARDROOM: ingest found {len(root_rtf_names)} RTF(s) in root: {root_rtf_names[:10]}")
                if lock_exists:
                    status_msg = f"Voice of TomeMaster: Resuming partial assembly — {len(root_rtf_names)} artifact(s) found. Injecting silently."
                else:
                    status_msg = f"Voice of TomeMaster: {len(root_rtf_names)} recovered page(s) found in root. Injecting silently into the manuscript now."

                new_status = "stitching"
                if not _stitching_active.is_set():
                    print(f"BOARDROOM: Starting resort_from_cache thread for '{folder_path}'")
                    TRANSCRIPTION_STATE["status"] = "stitching"
                    t = threading.Thread(target=resort_from_cache, args=(folder_path,))
                    t.daemon = True
                    t.start()
                else:
                    print("BOARDROOM: resort_from_cache already running — skipping duplicate thread.")

            elif len(all_images) > 0:
                # [S1]: FRESH WORK IN ROOT
                is_monumental = len(all_images) > 10
                
                if is_monumental:
                    if manuscript_exists:
                        status_msg = "Voice of TomeMaster: A significant expansion detected. Your current manuscript is partially populated; preparing to inject this monumental new volume."
                    else:
                        status_msg = "Voice of TomeMaster: A monumental undertaking detected. I am preparing the engine for a fresh, full-scale manuscript digitization."
                else:
                    status_msg = "Voice of TomeMaster: Surgical assets identified in the root. Preparing for a targeted transcription injection into your foundations."
                
                new_status = "idle"

            elif manuscript_exists:
                # [S4]: UNIFIED FOUNDATIONS
                try:
                    with open(manuscript_path, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        final_text = check_and_strip_manuscript_markers(raw_text)
                    
                    if "MISSING" in final_text:
                        status_msg = "Voice of TomeMaster: I have identified disruptions in the manuscript sequence. I have injected anchors at the missing coordinates. Place the missing photos in the root for a Surgical Injection."
                    else:
                        status_msg = "Voice of TomeMaster: The transcription phase is 100% complete. The manuscript foundations are stable. Proceed immediately to Structural Arrangement to delineate chapters. The Boardroom specialists will stand by until your structure is set."
                    
                    new_status = "complete"
                except:
                    new_status = "idle"
                    status_msg = "Voice of TomeMaster: Failed to load existing manuscript."
            else:
                # EMPTY STATE
                status_msg = "Voice of TomeMaster: The workspace is currently empty. Please deposit manuscript page images into the root folder to begin digitization."
                new_status = "idle"

            TRANSCRIPTION_STATE.update({
                "status": new_status,
                "folder": folder_path,
                "error_message": status_msg
            })
            if final_text:
                TRANSCRIPTION_STATE["text"] = final_text.strip()
                
            save_persistent_state()
            
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"BOARDROOM WARNING: Baseline Ingest failed: {e}")
        return False
def resort_from_cache(folder_path: str):
    """Industrial Grade Hydrator: Assembles any number of pages (10-1000+) from physical RTF files."""
    if not folder_path: return False
    if _stitching_active.is_set():
        print("BOARDROOM: Stitching already active in this process. Skipping duplicate call.")
        return False
    _stitching_active.set()
    folder_path = folder_path.strip().replace('\\', '/')
    output_path = os.path.join(folder_path, "Unified_Manuscript.md")
    tmp_path = output_path + ".tmp"
    print(f"BOARDROOM: Executing Industrial Hydration for: {folder_path}")

    try:
        # 1. Industrial Discovery: Root Scan ONLY (Archive scan strictly forbidden)
        all_rtfs = []
        if os.path.exists(folder_path):
            for f in os.listdir(folder_path):
                if f.lower().endswith(".rtf"):
                    all_rtfs.append(os.path.join(folder_path, f).replace('\\', '/'))

        all_rtfs.sort(key=industrial_sort_key)

        print(f"BOARDROOM: resort_from_cache scanning '{folder_path}' — found {len(all_rtfs)} RTF files: {[os.path.basename(r) for r in all_rtfs[:10]]}")

        if not all_rtfs:
            print("BOARDROOM: Bucket is empty. Stitcher standing down.")
            with TRANSCRIPTION_LOCK:
                TRANSCRIPTION_STATE["status"] = "idle"
                TRANSCRIPTION_STATE["error_message"] = "Directorial Stand-down: No artifacts found for assembly."
            return True
        
        # 2. Format-Agnostic Sorting Logic
        numbered_rtfs = []
        unknown_rtfs = []
        
        for rtf in all_rtfs:
            bn = os.path.basename(rtf).lower()
            if "unknown" in bn:
                unknown_rtfs.append(rtf)
            else:
                numbered_rtfs.append(rtf)

        numbered_rtfs.sort(key=industrial_sort_key)
        
        # [SEQUENCE RECOVERY]: Parse the existing manuscript to find which pages are already 'Sealed'
        manuscript_pages = {} # {page_num: content}
        if os.path.exists(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as mr:
                    m_content = mr.read()
                    pattern = r'--- \[PAGE START: page_(\d+)\.rtf\] ---\n(.*?)(?=\n--- \[PAGE START:|\n--- \[MISSING PAGE:|\n--- \[UNSORTED|$)'
                    matches = re.finditer(pattern, m_content, re.DOTALL)
                    for match in matches:
                        p_num = int(match.group(1))
                        p_text = match.group(2).strip()
                        # Strip any nested DIRECTORIAL ALERTS that got stuck inside previous pages
                        p_text = re.sub(r'\[DIRECTORIAL ALERT: PAGE \d+ MISSING[^\]]*\]\n*', '', p_text).strip()
                        p_text = restore_text_flow_if_fragmented(p_text)
                        manuscript_pages[p_num] = p_text
            except Exception as e:
                print(f"BOARDROOM WARNING: Failed to parse manuscript history: {e}")

        # [ACTIVE DISCOVERY]: Get the pages currently in the Root
        page_to_rtf = {extract_sequence_number(f): f for f in all_rtfs if extract_sequence_number(f) is not None}
        root_nums = set(page_to_rtf.keys())

        # [SEQUENCE CALIBRATION]: Determine the absolute range based on physical evidence
        all_known_nums = set(manuscript_pages.keys()).union(root_nums)
        if not all_known_nums:
            print("BOARDROOM: No sequence numbers found. Reverting to basic count.")
            total_goal = TRANSCRIPTION_STATE.get("total_images", 0)
            expected_range = range(0, total_goal)
        else:
            min_page = min(all_known_nums)
            max_page = max(all_known_nums)
            # [FIDELITY]: Always start at 1 if the sequence is near 1, otherwise honor the min
            start_floor = 1 if (0 < min_page <= 2) else min_page
            expected_range = range(start_floor, max_page + 1)

        print(f"BOARDROOM: resort_from_cache — {len(root_nums)} root RTFs, {len(manuscript_pages)} existing pages, logical range={expected_range}")
            
        # Pages still missing after this injection: had no content AND are not being injected now.
        still_missing = sorted([
            i for i in expected_range
            if i not in root_nums and (i not in manuscript_pages or not manuscript_pages[i].strip())
        ])

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                # 1. Write Directorial Header
                f.write(f"# TomeMaster Unified Manuscript\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

                if still_missing:
                    gap_str = ", ".join(map(str, still_missing))
                    f.write(f"\n> [DIRECTORIAL ALERT]: Sequence Disruption at pages: {gap_str}.\n")
                    f.write(f"> Action Required: Place missing page photos in the root for automated injection.\n")
                else:
                    f.write(f"\n> [SYSTEM STATUS]: Manuscript sequence is 100% verified. No gaps detected.\n")

                f.write(f"\n--- [START OF DOCUMENT] ---\n\n")

                # 2. Sequential Reconstruction (Surgical Injection)
                final_text_list = []
                processed_rtfs = []
                injected_pages = []
                
                # [SOVEREIGN IMAGE DISCOVERY]: Map images for archival handover
                valid_exts = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
                root_images = {}
                for img_file in os.listdir(folder_path):
                    if os.path.splitext(img_file)[1].lower() in valid_exts:
                        seq = extract_sequence_number(img_file)
                        if seq is not None: root_images[seq] = os.path.join(folder_path, img_file)

                for i in expected_range:
                    if i in root_nums:
                        # [INJECTION]: New content from Root RTF
                        rtf_path = page_to_rtf[i]
                        try:
                            with open(rtf_path, "r", encoding="utf-8", errors="ignore") as r:
                                content = r.read()
                                clean_content = strip_rtf(content)
                                clean_content = restore_text_flow_if_fragmented(clean_content)
                                clean_content = re.sub(r'^(Page|PAGE)\s*\d+\s*$', '', clean_content, flags=re.MULTILINE).strip()

                                f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                                f.write(clean_content + "\n\n")
                                final_text_list.append(clean_content)
                                processed_rtfs.append(rtf_path)
                                injected_pages.append(i)
                                
                                # [FIDELITY]: Queue the associated image for archiving
                                if i in root_images:
                                    processed_rtfs.append(root_images[i]) 
                        except Exception as e:
                            print(f"BOARDROOM ERROR: Failed to stitch page {i}: {e}")

                    elif i in manuscript_pages and manuscript_pages[i].strip():
                        # [PRESERVATION]: Existing page with real content
                        f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                        f.write(manuscript_pages[i] + "\n\n")
                        final_text_list.append(manuscript_pages[i])

                    else:
                        # [GAP]: Page still missing — write marker to file only, not the editor
                        gap_marker = f"[DIRECTORIAL ALERT: PAGE {i} MISSING - Awaiting Transcription Injection]"
                        f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                        f.write(gap_marker + "\n\n")
                
                f.flush()
                os.fsync(f.fileno())

            # [ATOMIC SEALING]: Finalize the unified manuscript
            if os.path.exists(tmp_path):
                max_retries = 3
                sealed = False
                for attempt in range(max_retries):
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        os.rename(tmp_path, output_path)
                        sealed = True
                        break
                    except PermissionError:
                        print(f"BOARDROOM WARNING: Output path locked, retrying {attempt+1}/{max_retries}...")
                        time.sleep(1)
                
                if sealed:
                    # Move successfully injected files (RTFs AND JPGs) to Archive
                    archive_dir = os.path.join(folder_path, "Archive")
                    if not os.path.exists(archive_dir): os.makedirs(archive_dir)
                    for path in processed_rtfs:
                        dest_path = os.path.join(archive_dir, os.path.basename(path))
                        try:
                            if os.path.exists(dest_path):
                                if os.path.exists(path): os.remove(path)
                            else:
                                if os.path.exists(path): shutil.move(path, dest_path)
                        except Exception as e:
                            print(f"BOARDROOM WARNING: Failed to archive {path}: {e}")
                else:
                    print(f"BOARDROOM ERROR: CRITICAL LOCK FAILURE on {output_path}. Aborting.")
                
                # [STATE SYNC]: Update UI and persistent state
                if injected_pages:
                    inj_str = ", ".join(map(str, injected_pages))
                    if still_missing:
                        miss_str = ", ".join(map(str, still_missing))
                        completion_msg = f"Voice of TomeMaster: {len(injected_pages)} page(s) injected (pages {inj_str}). {len(still_missing)} page(s) still missing: {miss_str}."
                    else:
                        completion_msg = f"Voice of TomeMaster: {len(injected_pages)} page(s) injected (pages {inj_str}). Manuscript sequence is now 100% complete."
                else:
                    completion_msg = "Voice of TomeMaster: Assembly complete. No new pages were injected."

                with TRANSCRIPTION_LOCK:
                    TRANSCRIPTION_STATE.update({
                        "status": "complete",
                        "processed_images": len(all_known_nums),
                        "missing_pages_count": len(still_missing),
                        "text": "\n\n".join(final_text_list),
                        "error_message": completion_msg
                    })
                save_persistent_state()
                print(f"BOARDROOM: Manuscript Sealed at {output_path}")
            return True

        except Exception as e:
            print(f"BOARDROOM ERROR during stitching: {e}")
            with TRANSCRIPTION_LOCK:
                TRANSCRIPTION_STATE["status"] = "error"
                TRANSCRIPTION_STATE["error_message"] = f"Industrial Stitching Failed: {str(e)}"
            return False
    except Exception as e:
        print(f"BOARDROOM ERROR: Global Hydration Failure. {str(e)}")
        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["status"] = "error"
            TRANSCRIPTION_STATE["error_message"] = f"Global Assembly Failure: {str(e)}"
        return False
    finally:
        _stitching_active.clear()

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
    
async def _call_ai_with_failover(img, primary_provider, primary_model, primary_key, fallback_provider=None, fallback_model=None):
    """Spectrum Failover Protocol: Attempts execution with primary engine, gears-down to fallback on failure."""
    
    # [SOVEREIGN RESILIENCE]: 3-try outer loop for transient network saturation
    max_retries = 3
    last_err = None
    
    for attempt in range(max_retries):
        providers = [(primary_provider, primary_model, primary_key)]
        if fallback_provider and fallback_model:
            providers.append((fallback_provider, fallback_model, None)) # Use env/vault key
            
        for prov, mod, key in providers:
            try:
                # [VISION GUARD]: Skip known non-vision models
                blind_keywords = ["versatile", "instant", "text", "instruct", "preview-text"]
                if prov == "groq" and any(k in mod.lower() for k in blind_keywords):
                    continue

                print(f"BOARDROOM PULSE: Engaging {prov}:{mod} (Attempt {attempt+1}/{max_retries})...")
                client = _get_ai_client(prov, key)
                if not client: continue
                
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
                    b64_payload = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    if prov == "anthropic":
                        res = client.messages.create(
                            model=mod,
                            max_tokens=2500,
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": OCR_PROMPT},
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_payload}}
                            ]}]
                        )
                        return res.content[0].text, prov, mod
                    else:
                        # OpenAI/Groq
                        res = client.chat.completions.create(
                            model=mod,
                            messages=[
                                {"role": "system", "content": "You are a professional manuscript transcriber. Output in XML format: <page><number>PAGENUM</number><text>TRANSCRIPT</text></page>"},
                                {"role": "user", "content": [
                                    {"type": "text", "text": OCR_PROMPT},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_payload}"}}
                                ]}
                            ],
                            temperature=0.1,
                            max_tokens=2500
                        )
                        return res.choices[0].message.content, prov, mod
            except Exception as e:
                print(f"[FAILOVER ALERT]: {prov}:{mod} failed -> {str(e)}")
                last_err = str(e)
                # [SOVEREIGN HANDOVER]: Instantly try the next provider in the list
                continue 
        
        # [BACKOFF]: Only wait if the ENTIRE spectrum (primary + fallback) failed
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2
            print(f"BOARDROOM: Spectrum Total Saturation. Cool-down: {wait_time}s...")
            await asyncio.sleep(wait_time)
            
    raise Exception(f"Boardroom Blackout: All assigned engines saturated. Last error: {last_err}")

def start_transcription_background(api_key: str, provider: str, folder_path: str = None, reset_cache: bool = False, mode: str = "batch", model: str = None, fallback_provider: str = None, fallback_model: str = None):
    """Triggered by the API endpoint to spawn the folder picker and launch the background thread."""
    
    global TRANSCRIPTION_STATE
    with TRANSCRIPTION_LOCK:
        current_status = TRANSCRIPTION_STATE.get("status", "standby")
        if current_status in ["running", "indexing", "processing"] and not reset_cache:
            print(f"BOARDROOM: Re-entrancy blocked. Engine is already in {current_status} mode for {TRANSCRIPTION_STATE.get('folder')}")
            return True, TRANSCRIPTION_STATE.get('folder')
        TRANSCRIPTION_STATE["status"] = "Initializing file system..."

    folder = folder_path if folder_path else pick_directory()
    if not folder:
        # User canceled the folder picker dialog
        return False, None

    # [SOVEREIGN ANCHOR]: Automatically ingest the baseline for the new folder
    ingest_project_baseline(folder)

    # [SOVEREIGN RESET]: Optional hard-wipe of progress for a clean slate
    if reset_cache:
        cache_path = os.path.join(folder, "_tome_master_cache.json")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except:
                pass


    # Initialize the state globally
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE.update({
            "folder": folder,
            "status": "Initializing file system...",
            "progress": 0,
            "processed_images": 0,
            "total_images": 0,
            "error_message": None,
            "current_image_b64": None,
            "current_extracted_text": None,
            "is_new_chunk": False,
            "pages": [], # Clear local pages buffer for UI
            "page_audits": [],
            "stream_buffer": [] # [SOVEREIGN PURGE]: Clear the stream buffer to prevent bleeding
        })
    # [ATOMIC STATE RESET]: Purge legacy telemetry before launching the fresh thread
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE.update({
            "status": "indexing",
            "total_images": 0, "processed_images": 0, "current_batch": 0, "total_batches": 0,
            "text": None, "error_message": "Assembling high-velocity scanning engine...",
            "current_image_b64": None, "current_extracted_text": None, "is_new_chunk": False,
            "stream_buffer": []
        })
    
    # [CERTIFICATION GRADE]: Dispatched to the distributed Celery worker fleet.
    # This prevents local resource exhaustion and ensures process resilience.
    from celery_app import app as celery_app
    celery_app.send_task(
        'services.transcriber_service.run_transcription_job',
        args=[api_key, folder, provider, reset_cache, mode, model],
        kwargs={"fallback_provider": fallback_provider, "fallback_model": fallback_model}
    )
    
    return True, folder

def clear_transcription_state():
    """Wipes the global state and disk artifacts to allow for a fresh project start."""
    global TRANSCRIPTION_STATE
    folder = None
    with TRANSCRIPTION_LOCK:
        folder = TRANSCRIPTION_STATE.get("folder")
        TRANSCRIPTION_STATE.update({
            "status": "idle",
            "folder": None,
            "total_images": 0,
            "processed_images": 0,
            "current_batch": 0,
            "total_batches": 0,
            "text": None,
            "error_message": None,
            "current_image_b64": None,
            "current_extracted_text": None,
            "is_new_chunk": False,
            "pages": [],
            "page_audits": [],
            "stream_buffer": [],
            "mode": "batch",
            "offset_delta": 0,
            "waiting_for_input": False,
            "last_processed_file": None
        })

    # [EDITORIAL CLEANSE]: Remove disk artifacts so hydration cannot resurrect cleared content
    if folder:
        manuscript_path = os.path.join(folder, "Unified_Manuscript.md")
        lock_path = manuscript_path + ".STITCH_LOCK"
        for path in [manuscript_path, lock_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"[DIRECTORIAL CLEANSE]: Removed {os.path.basename(path)}")
            except Exception as e:
                print(f"[DIRECTORIAL CLEANSE WARNING]: Could not remove {path}: {e}")

    print("[DIRECTORIAL CLEANSE]: Application memory and disk state cleared for new project.")
    return True


def resolve_audit_input(page_number: str, apply_offset: bool = False):
    """Called by the frontend to resolve an 'UNKNOWN' or 'COLLISION' event."""
    global TRANSCRIPTION_STATE
    with TRANSCRIPTION_LOCK:
        if not TRANSCRIPTION_STATE.get("waiting_for_input"):
            return False
            
        folder = TRANSCRIPTION_STATE.get("folder")
        old_filename = TRANSCRIPTION_STATE.get("last_processed_file")
        
        if folder and old_filename:
            # [DIRECTORIAL ANCHOR]: Resolve where the artifacts are stored
            artifacts_dir = os.path.join(folder, TRANSCRIPTION_ARTIFACTS_DIR)
            target_dir = artifacts_dir if os.path.exists(artifacts_dir) else folder

            # [CLEANUP]: Delete the temporary UNKNOWN rtf file
            file_basename = os.path.splitext(old_filename)[0]
            temp_rtf = os.path.join(target_dir, f"UNKNOWN_{file_basename}.rtf")
            if os.path.exists(temp_rtf):
                try:
                    os.remove(temp_rtf)
                except: pass
            
            # [RE-WRITE]: Save the corrected RTF
            # We need the text from the last processed page
            pages = TRANSCRIPTION_STATE.get("pages", [])
            if pages:
                last_page = pages[-1]
                # Update its number in state
                last_page["extracted_page_number"] = page_number
                
                # Re-save with correct name in the artifacts directory
                new_rtf_path = os.path.join(target_dir, f"page_{page_number}.rtf")
                with open(new_rtf_path, "w", encoding="utf-8") as f:
                    f.write(to_rtf(last_page.get("text", "")))

        # [REALIGNMENT]: Apply offset for future pages if requested
        if apply_offset and page_number.isdigit():
            # Calculate what the delta should be based on this correction
            # (Simple logic: user input - AI's last raw guess)
            raw_ai_num = TRANSCRIPTION_STATE["pages"][-1].get("raw_extracted_number", "0")
            if raw_ai_num.isdigit():
                TRANSCRIPTION_STATE["offset_delta"] = int(page_number) - int(raw_ai_num)

        # Resume the thread
        TRANSCRIPTION_STATE["waiting_for_input"] = False
        return True

def set_transcription_offset(delta: int):
    """Manually set the page number offset for the remainder of the project."""
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["offset_delta"] = delta
    return True

