"""
[INDUSTRIAL STITCHER]: Heavy I/O operations for reading and writing the final manuscript.

Owns resort_from_cache() (the stitcher) and ingest_project_baseline() (project hydration).
These are the two biggest I/O functions — they read/write RTF files, build the
Unified_Manuscript.md, and trigger the Phase 2 cleanup pipeline.
"""
import os
import re
import glob
import time
import shutil
import threading

from .state_manager import (
    TRANSCRIPTION_LOCK,
    TRANSCRIPTION_STATE,
    TRANSCRIPTION_ARTIFACTS_DIR,
    _stitching_active,
    save_persistent_state,
    load_persistent_state,
)
from .text_formatter import (
    strip_rtf,
    restore_text_flow_if_fragmented,
    check_and_strip_manuscript_markers,
)
from .asset_scanner import natural_sort_key, extract_sequence_number

# Alias for backward compat
industrial_sort_key = natural_sort_key


def ingest_project_baseline(folder_path: str):
    """
    Directorial Pulse: Scans a folder on anchor to hydrate UI counters and Editor.
    Ends the 'Starting at 0' amnesia by recognizing existing work instantly.
    """
    try:
        # [HUMAN PATHING]: Preserve native Windows formatting
        folder_path = os.path.normpath(folder_path.strip())

        # 0. State Recovery Attempt
        load_persistent_state(folder_path)

        # 1. Industrial Discovery (Root Only — Physical Reality)
        all_images = []
        root_rtf_names = []
        valid_exts = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}

        if os.path.exists(folder_path):
            for f in os.listdir(folder_path):
                f_lower = f.lower()
                if f_lower == "cover.jpg":
                    continue
                ext = os.path.splitext(f_lower)[1]
                if ext in valid_exts:
                    all_images.append(os.path.join(folder_path, f))
                elif ext == ".rtf":
                    root_rtf_names.append(f)

        all_images.sort(key=natural_sort_key)

        # [ZAP]: Physical Verification
        manuscript_path = os.path.join(folder_path, "Unified_Manuscript.md")
        lock_path = os.path.join(folder_path, "Unified_Manuscript.md.STITCH_LOCK")
        manuscript_exists = os.path.exists(manuscript_path)
        lock_exists = os.path.exists(lock_path)

        # [GAP DISCOVERY]
        missing_count = 0
        if manuscript_exists:
            try:
                with open(manuscript_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    missing_count = len(re.findall(r'\[DIRECTORIAL ALERT: PAGE \d+ MISSING', content))
            except Exception:
                pass

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["missing_pages_count"] = missing_count

        final_text = None
        new_status = "idle"

        with TRANSCRIPTION_LOCK:
            if len(root_rtf_names) > 0:
                # [S2]: UNSEALED RTF ARTIFACTS IN ROOT
                print(f"BOARDROOM: ingest found {len(root_rtf_names)} RTF(s) in root: {root_rtf_names[:10]}")
                if lock_exists:
                    status_msg = (
                        f"Voice of TomeMaster: Resuming partial assembly — "
                        f"{len(root_rtf_names)} artifact(s) found. Injecting silently."
                    )
                else:
                    status_msg = (
                        f"Voice of TomeMaster: {len(root_rtf_names)} recovered page(s) found in root. "
                        f"Injecting silently into the manuscript now."
                    )

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
                        status_msg = (
                            "Voice of TomeMaster: A significant expansion detected. Your current manuscript "
                            "is partially populated; preparing to inject this monumental new volume."
                        )
                    else:
                        status_msg = (
                            "Voice of TomeMaster: A monumental undertaking detected. I am preparing "
                            "the engine for a fresh, full-scale manuscript digitization."
                        )
                else:
                    status_msg = (
                        "Voice of TomeMaster: Surgical assets identified in the root. "
                        "Preparing for a targeted transcription injection into your foundations."
                    )
                new_status = "idle"

            elif manuscript_exists:
                # [S4]: UNIFIED FOUNDATIONS
                try:
                    # [PHASE 2]: Prefer Clean_Manuscript.md over raw
                    clean_manuscript_path = os.path.join(folder_path, "Clean_Manuscript.md")
                    if os.path.exists(clean_manuscript_path):
                        with open(clean_manuscript_path, "r", encoding="utf-8") as f:
                            final_text = f.read()
                        print("BOARDROOM: Loaded Clean_Manuscript.md (Phase 2 processed)")
                    else:
                        with open(manuscript_path, "r", encoding="utf-8") as f:
                            raw_text = f.read()
                            final_text = check_and_strip_manuscript_markers(raw_text)

                    if "MISSING" in final_text:
                        status_msg = (
                            "Voice of TomeMaster: I have identified disruptions in the manuscript sequence. "
                            "I have injected anchors at the missing coordinates. Place the missing photos "
                            "in the root for a Surgical Injection."
                        )
                    else:
                        status_msg = (
                            "Voice of TomeMaster: The transcription phase is 100% complete. "
                            "The manuscript foundations are stable. Proceed immediately to Structural "
                            "Arrangement to delineate chapters. The Boardroom specialists will stand by "
                            "until your structure is set."
                        )
                    new_status = "complete"
                except Exception:
                    new_status = "idle"
                    status_msg = "Voice of TomeMaster: Failed to load existing manuscript."
            else:
                status_msg = (
                    "Voice of TomeMaster: The workspace is currently empty. "
                    "Please deposit manuscript page images into the root folder to begin digitization."
                )
                new_status = "idle"

            TRANSCRIPTION_STATE.update({
                "status": new_status,
                "folder": folder_path,
                "error_message": status_msg,
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
    if not folder_path:
        return False
    if _stitching_active.is_set():
        print("BOARDROOM: Stitching already active in this process. Skipping duplicate call.")
        return False
    _stitching_active.set()
    folder_path = folder_path.strip().replace("\\", "/")
    output_path = os.path.join(folder_path, "Unified_Manuscript.md")
    tmp_path = output_path + ".tmp"
    print(f"BOARDROOM: Executing Industrial Hydration for: {folder_path}")

    try:
        # 1. Industrial Discovery: Root Scan ONLY
        all_rtfs = []
        if os.path.exists(folder_path):
            for f in os.listdir(folder_path):
                if f.lower().endswith(".rtf"):
                    all_rtfs.append(os.path.join(folder_path, f).replace("\\", "/"))

        all_rtfs.sort(key=industrial_sort_key)

        print(
            f"BOARDROOM: resort_from_cache scanning '{folder_path}' — "
            f"found {len(all_rtfs)} RTF files: {[os.path.basename(r) for r in all_rtfs[:10]]}"
        )

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

        # [SEQUENCE RECOVERY]: Parse existing manuscript for sealed pages
        manuscript_pages = {}
        if os.path.exists(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as mr:
                    m_content = mr.read()
                    pattern = (
                        r'--- \[PAGE START: page_(\d+)\.rtf\] ---\n'
                        r'(.*?)(?=\n--- \[PAGE START:|\n--- \[MISSING PAGE:|\n--- \[UNSORTED|$)'
                    )
                    matches = re.finditer(pattern, m_content, re.DOTALL)
                    for match in matches:
                        p_num = int(match.group(1))
                        p_text = match.group(2).strip()
                        p_text = re.sub(
                            r'\[DIRECTORIAL ALERT: PAGE \d+ MISSING[^\]]*\]\n*', '', p_text
                        ).strip()
                        p_text = restore_text_flow_if_fragmented(p_text)
                        manuscript_pages[p_num] = p_text
            except Exception as e:
                print(f"BOARDROOM WARNING: Failed to parse manuscript history: {e}")

        # [ACTIVE DISCOVERY]: Pages currently in Root
        page_to_rtf = {
            extract_sequence_number(f): f
            for f in all_rtfs
            if extract_sequence_number(f) is not None
        }
        root_nums = set(page_to_rtf.keys())

        # [SEQUENCE CALIBRATION]
        all_known_nums = set(manuscript_pages.keys()).union(root_nums)
        if not all_known_nums:
            print("BOARDROOM: No sequence numbers found. Reverting to basic count.")
            total_goal = TRANSCRIPTION_STATE.get("total_images", 0)
            expected_range = range(0, total_goal)
        else:
            min_page = min(all_known_nums)
            max_page = max(all_known_nums)
            start_floor = 1 if (0 < min_page <= 2) else min_page
            expected_range = range(start_floor, max_page + 1)

        print(
            f"BOARDROOM: resort_from_cache — {len(root_nums)} root RTFs, "
            f"{len(manuscript_pages)} existing pages, logical range={expected_range}"
        )

        still_missing = sorted([
            i for i in expected_range
            if i not in root_nums and (i not in manuscript_pages or not manuscript_pages[i].strip())
        ])

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("# TomeMaster Unified Manuscript\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

                if still_missing:
                    gap_str = ", ".join(map(str, still_missing))
                    f.write(f"\n> [DIRECTORIAL ALERT]: Sequence Disruption at pages: {gap_str}.\n")
                    f.write("> Action Required: Place missing page photos in the root for automated injection.\n")
                else:
                    f.write("\n> [SYSTEM STATUS]: Manuscript sequence is 100% verified. No gaps detected.\n")

                f.write("\n--- [START OF DOCUMENT] ---\n\n")

                final_text_list = []
                processed_rtfs = []
                injected_pages = []

                # [SOVEREIGN IMAGE DISCOVERY]
                valid_exts = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
                root_images = {}
                for img_file in os.listdir(folder_path):
                    if os.path.splitext(img_file)[1].lower() in valid_exts:
                        seq = extract_sequence_number(img_file)
                        if seq is not None:
                            root_images[seq] = os.path.join(folder_path, img_file)

                for i in expected_range:
                    if i in root_nums:
                        rtf_path = page_to_rtf[i]
                        try:
                            with open(rtf_path, "r", encoding="utf-8", errors="ignore") as r:
                                content = r.read()
                                clean_content = strip_rtf(content)
                                clean_content = restore_text_flow_if_fragmented(clean_content)
                                clean_content = re.sub(
                                    r'^(Page|PAGE)\s*\d+\s*$', '', clean_content, flags=re.MULTILINE
                                ).strip()

                                f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                                f.write(clean_content + "\n\n")
                                final_text_list.append(clean_content)
                                processed_rtfs.append(rtf_path)
                                injected_pages.append(i)

                                if i in root_images:
                                    processed_rtfs.append(root_images[i])
                        except Exception as e:
                            print(f"BOARDROOM ERROR: Failed to stitch page {i}: {e}")

                    elif i in manuscript_pages and manuscript_pages[i].strip():
                        f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                        f.write(manuscript_pages[i] + "\n\n")
                        final_text_list.append(manuscript_pages[i])

                    else:
                        gap_marker = f"[DIRECTORIAL ALERT: PAGE {i} MISSING - Awaiting Transcription Injection]"
                        f.write(f"--- [PAGE START: page_{i}.rtf] ---\n")
                        f.write(gap_marker + "\n\n")

                f.flush()
                os.fsync(f.fileno())

            # [ATOMIC SEALING]
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
                        print(f"BOARDROOM WARNING: Output path locked, retrying {attempt + 1}/{max_retries}...")
                        time.sleep(1)

                if sealed:
                    archive_dir = os.path.join(folder_path, "Archive")
                    if not os.path.exists(archive_dir):
                        os.makedirs(archive_dir)
                    for path in processed_rtfs:
                        dest_path = os.path.join(archive_dir, os.path.basename(path))
                        try:
                            if os.path.exists(dest_path):
                                if os.path.exists(path):
                                    os.remove(path)
                            else:
                                if os.path.exists(path):
                                    shutil.move(path, dest_path)
                        except Exception as e:
                            print(f"BOARDROOM WARNING: Failed to archive {path}: {e}")
                else:
                    print(f"BOARDROOM ERROR: CRITICAL LOCK FAILURE on {output_path}. Aborting.")

                # [STATE SYNC]
                if injected_pages:
                    inj_str = ", ".join(map(str, injected_pages))
                    if still_missing:
                        miss_str = ", ".join(map(str, still_missing))
                        completion_msg = (
                            f"Voice of TomeMaster: {len(injected_pages)} page(s) injected (pages {inj_str}). "
                            f"{len(still_missing)} page(s) still missing: {miss_str}."
                        )
                    else:
                        completion_msg = (
                            f"Voice of TomeMaster: {len(injected_pages)} page(s) injected (pages {inj_str}). "
                            f"Manuscript sequence is now 100% complete."
                        )
                else:
                    completion_msg = "Voice of TomeMaster: Assembly complete. No new pages were injected."

                with TRANSCRIPTION_LOCK:
                    TRANSCRIPTION_STATE.update({
                        "status": "complete",
                        "processed_images": len(all_known_nums),
                        "missing_pages_count": len(still_missing),
                        "text": "\n\n".join(final_text_list),
                        "error_message": completion_msg,
                    })
                save_persistent_state()
                print(f"BOARDROOM: Manuscript Sealed at {output_path}")

                # ═══ PHASE 2: POST-STITCH CLEANUP ═══
                try:
                    from services.transcriber.post_stitch_cleanup import run_post_stitch_cleanup
                    cleanup_ok = run_post_stitch_cleanup(folder_path)
                    if cleanup_ok:
                        clean_path = os.path.join(folder_path, "Clean_Manuscript.md")
                        if os.path.exists(clean_path):
                            with open(clean_path, "r", encoding="utf-8") as cf:
                                clean_text = cf.read()
                            with TRANSCRIPTION_LOCK:
                                TRANSCRIPTION_STATE["text"] = clean_text.strip()
                            print("BOARDROOM: Clean manuscript loaded into editor state")
                except Exception as cleanup_err:
                    print(f"BOARDROOM WARNING: Phase 2 cleanup failed (non-fatal): {cleanup_err}")

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
