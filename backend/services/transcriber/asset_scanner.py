import os
import glob
import re
import fitz # PyMuPDF for page counting
from typing import List, Tuple, Optional

# [SOVEREIGN COVER PROTOCOL]: Filenames that match these patterns are cover assets,
# not manuscript pages — they go to the project cover slot, never the OCR queue.
COVER_NAME_PATTERNS = re.compile(
    r'^(cover|front.?cover|back.?cover|book.?cover|jacket|title.?page)',
    re.IGNORECASE
)

def natural_sort_key(s: str):
    """[NATURAL SORT]: Sequence logic for manuscript numbering (1, 2, 10...)."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', os.path.basename(s))]

def extract_sequence_number(filename: str) -> int:
    """[FIDELITY]: Extracts the first continuous integer sequence from a filename."""
    if not filename: return None
    match = re.search(r'(\d+)', os.path.basename(filename))
    return int(match.group(1)) if match else None

def is_cover_asset(filename: str) -> bool:
    """Returns True if the file is a cover/jacket image that should NOT be OCR'd."""
    name = os.path.splitext(os.path.basename(filename))[0]  # strip extension
    return bool(COVER_NAME_PATTERNS.match(name))

def scan_manuscript_folder(folder_path: str, artifacts_dir: str) -> Tuple[List[str], int, int, Optional[str], int]:
    """
    [ASSET SCANNER]: Identifies all valid manuscript images and calculates 
    the delta between identified work and existing artifacts.
    Returns: (all_files, already_processed, files_needing_processing, cover_path, total_pages)
    """
    all_files = []
    seen_filenames = set()
    cover_path = None
    # [FIX]: Include Word documents — they should be TEXT-PARSED, not OCR'd.
    # The transcription loop checks is_parseable_document() before routing.
    extensions = ["jpg", "jpeg", "png", "pdf", "webp", "docx", "doc"]
    total_pages = 0
    
    for ext in extensions:
        for f_path in glob.glob(os.path.join(folder_path, f"*.{ext}")):
            fname = os.path.basename(f_path)
            if fname in seen_filenames:
                continue
            seen_filenames.add(fname)

            if is_cover_asset(fname):
                # [COVER ROUTING]: First matching cover wins; log and skip OCR
                if cover_path is None:
                    cover_path = f_path
                    print(f"BOARDROOM: Cover asset detected — routed to project cover slot: {fname}")
                else:
                    print(f"BOARDROOM: Additional cover asset skipped: {fname}")
            else:
                all_files.append(f_path)
                # [PAGE DISCOVERY]: Count actual pages for multi-page assets
                lower_path = f_path.lower()
                if lower_path.endswith(".pdf"):
                    try:
                        doc = fitz.open(f_path)
                        total_pages += len(doc)
                        doc.close()
                    except:
                        total_pages += 1 # Fallback to 1 if corrupt
                elif lower_path.endswith((".docx", ".doc")):
                    # Word docs are variable-length; estimate 1 page per file
                    # (actual page count determined during parsing)
                    total_pages += 1
                else:
                    total_pages += 1
                
    all_files = sorted(all_files, key=natural_sort_key)
    
    # Check for existing artifacts to calculate already_processed count.
    # ROOT ONLY — Archive holds completed work from prior runs and must
    # never influence the discovery of pages that still need processing.
    existing_rtfs = set()
    if os.path.exists(folder_path):
        for rtf_file in glob.glob(os.path.join(folder_path, "*.rtf")):
            existing_rtfs.add(os.path.basename(rtf_file).lower())
    
    files_needing_processing = 0
    # Note: files_needing_processing is now less accurate than total_pages, 
    # but we'll use total_pages for the UI.
    for i, f_path in enumerate(all_files):
        # This check is still per-file, which is a bit rough for PDFs.
        # But we'll refine the already_processed count below.
        rtf_name_0 = f"page_{i}.rtf"
        rtf_name_1 = f"page_{i+1}.rtf"
        if rtf_name_0.lower() not in existing_rtfs and rtf_name_1.lower() not in existing_rtfs:
            files_needing_processing += 1
            
    # For now, we'll keep already_processed as the number of existing RTFs
    already_processed = len(existing_rtfs)
    
    return all_files, already_processed, files_needing_processing, cover_path, total_pages
