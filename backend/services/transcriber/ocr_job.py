"""
[OCR JOB]: Direct transcription loop — the engine behind "Start Transcription".

Restored from the pre-PR#13 monolith (git ddfa802^) and adapted to the
modular transcriber package. PR #13/#14 deleted this loop in favor of the
CrewAI pipeline, but that pipeline's dependency was never installed, leaving
the app with no working OCR path. This module is the canonical path; the
CrewAI pipeline remains an optional experiment behind /transcribe/start-pipeline.

Flow per asset:
  1. Smart routing — digital PDFs/Word docs are text-parsed (no API credits).
  2. Scanned assets go through vision OCR with spectrum failover
     (ai_engine._call_ai_with_failover).
  3. Extracted pages are saved as RTF artifacts, cached, and archived.
  4. A final physical stitch (industrial_stitcher.resort_from_cache)
     unifies all artifacts into the manuscript.

Abort: checks state_manager.TRANSCRIPTION_ABORT between assets and stops at
the next safe point, skipping the final stitch.
"""

import os
import re
import json
import time
import glob
import shutil
import asyncio
import threading

from .state_manager import (
    TRANSCRIPTION_LOCK,
    TRANSCRIPTION_STATE,
    TRANSCRIPTION_ABORT,
    TRANSCRIPTION_ARTIFACTS_DIR,
    _update_active_agent,
)
from . import asset_scanner, vision_processor
from .asset_scanner import extract_sequence_number
from .artifact_steward import save_page_artifact
from .ai_engine import _call_ai_with_failover
from .industrial_stitcher import resort_from_cache
from ..logger_service import log_api_usage

# Env-var fallback per provider when no key is passed explicitly.
_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "groq":   "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _fail(message: str):
    """Sets an honest error state and returns."""
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["status"] = "error"
        TRANSCRIPTION_STATE["error_message"] = message


def _abort_requested() -> bool:
    return TRANSCRIPTION_ABORT.is_set()


def _mark_aborted():
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["status"] = "idle"
        TRANSCRIPTION_STATE["error_message"] = "Transcription aborted by user."
    print("OCR JOB: Abort honored — stopping at safe point.")


def run_transcription_job(
    api_key: str,
    folder_path: str,
    provider: str = "gemini",
    reset_cache: bool = False,
    mode: str = "batch",
    model_override: str = None,
    fallback_provider: str = None,
    fallback_model: str = None,
):
    """Blocking worker — run in a daemon thread by start_transcription_background."""
    try:
        if not model_override:
            _fail(
                f"No vision model resolved for provider '{provider}'. "
                "Open Settings and verify an API key is sealed for a vision-capable provider."
            )
            return

        # [PROCESS STEWARDSHIP]: Lower priority to prevent system saturation
        try:
            import psutil
            p = psutil.Process(os.getpid())
            if os.name == "nt":
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                p.nice(10)
        except Exception:
            pass

        # [KEY GATE]: ai_engine builds its own clients; we only verify a key exists.
        if not api_key or not str(api_key).strip():
            api_key = os.environ.get(_ENV_KEYS.get(provider, "OPENAI_API_KEY"), "")
        if not api_key:
            _fail(f"Missing API key for provider '{provider}'. Seal one in Settings → Intelligence.")
            return

        # [PATH NORMALIZATION]
        folder_path = os.path.abspath(folder_path).strip().replace("\\", "/")
        project_root = folder_path
        if project_root.rstrip("/").endswith(TRANSCRIPTION_ARTIFACTS_DIR):
            project_root = os.path.dirname(project_root.rstrip("/"))
        if folder_path.rstrip("/").endswith(TRANSCRIPTION_ARTIFACTS_DIR):
            artifacts_path = folder_path
        else:
            artifacts_path = os.path.join(folder_path, TRANSCRIPTION_ARTIFACTS_DIR)

        cache_file = os.path.join(project_root, "_tome_master_cache.json")

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "status": "indexing",
                "processed_images": 0,
                "total_images": 0,
                "error_message": "Scanning directory for manuscript evidence...",
            })

        all_files, _scanned_done, _scanned_todo, _cover_path, total_pages = (
            asset_scanner.scan_manuscript_folder(folder_path, artifacts_path)
        )
        total_files = len(all_files)
        total_images_target = total_pages

        if total_files == 0:
            _fail("No manuscript evidence (JPG, PNG, PDF, DOCX) identified in the project folder.")
            return

        # [CACHE]: Load or reset incremental progress
        master_pages = []
        if reset_cache:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    print(f"OCR JOB: Failed to wipe cache: {e}")
        elif os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    master_pages = json.load(f).get("pages", [])
            except Exception as e:
                print(f"OCR JOB: Cache load failed, starting fresh: {e}")

        # [HYDRATION]: Existing RTF artifacts — ROOT ONLY. Scanning Archive here
        # would let stale artifacts from prior runs mark pages as done forever.
        existing_rtfs = set()
        if os.path.exists(folder_path):
            for rtf_file in glob.glob(os.path.join(folder_path, "*.rtf")):
                existing_rtfs.add(os.path.basename(rtf_file).lower())

        files_needing_processing = 0
        for i, f_path in enumerate(all_files):
            if (f"page_{i}.rtf" in existing_rtfs) or (f"page_{i+1}.rtf" in existing_rtfs):
                continue
            files_needing_processing += 1
        already_processed = total_files - files_needing_processing
        print(f"OCR JOB: {already_processed} files have RTFs, {files_needing_processing} need processing")

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "processed_images": already_processed,
                "total_images": total_images_target,
            })

        # [AUTO-STITCH]: Everything already digitized — go straight to assembly
        if files_needing_processing == 0:
            print("OCR JOB: All pages already digitized. Executing physical stitch...")
            resort_from_cache(folder_path)
            return

        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE.update({
                "status": "running",
                "total_batches": total_images_target,
                "current_batch": already_processed,
                "text": None,
                "error_message": None,
                "current_image_b64": None,
                "mode": mode,
                "waiting_for_input": False,
            })

        async def _consumer(queue):
            while True:
                i, f_path = await queue.get()
                label = f_path
                try:
                    if _abort_requested():
                        continue  # drain without processing

                    # Live-mode pause gate
                    while TRANSCRIPTION_STATE.get("waiting_for_input"):
                        if _abort_requested():
                            break
                        await asyncio.sleep(1)
                    if _abort_requested():
                        continue

                    # ─── SMART ROUTING: digital documents parse for free ───
                    parsed_shortcut = False
                    raw_text = ""
                    if vision_processor.is_parseable_document(f_path):
                        parsed = vision_processor.parse_document_text(f_path)
                        if parsed:
                            raw_text = parsed
                            with TRANSCRIPTION_LOCK:
                                _update_active_agent("TRANSCRIBER_LEAD", "text-parser", "local", "working")
                                TRANSCRIPTION_STATE["current_extracted_text"] = raw_text.strip()
                                TRANSCRIPTION_STATE["current_image_b64"] = None
                                TRANSCRIPTION_STATE["is_new_chunk"] = True
                            log_api_usage("TextParser", "local", "native-extraction",
                                          {"total_tokens": 0}, folder_path, 0.01)
                            print(f"[SMART ROUTE]: {os.path.basename(f_path)} -> text parse (no OCR)")
                            parsed_shortcut = True

                    if not parsed_shortcut:
                        # ─── OCR PATH: vision model with spectrum failover ───
                        images_to_process = vision_processor.process_asset(f_path, folder_path)
                        if not images_to_process:
                            continue

                        for img, label in images_to_process:
                            if _abort_requested():
                                break
                            with TRANSCRIPTION_LOCK:
                                TRANSCRIPTION_STATE["current_image_b64"] = vision_processor.generate_telemetry(img)
                                _update_active_agent("TRANSCRIBER_LEAD", model_override or "resolving...", provider, "working")

                            call_start = time.time()
                            try:
                                raw_text, used_prov, used_mod = await _call_ai_with_failover(
                                    img, provider, model_override, api_key,
                                    fallback_provider=fallback_provider,
                                    fallback_model=fallback_model,
                                )
                                with TRANSCRIPTION_LOCK:
                                    _update_active_agent("TRANSCRIBER_LEAD", used_mod, used_prov, "working")
                                log_api_usage("Transcriber", used_prov, used_mod,
                                              {"total_tokens": 0}, folder_path,
                                              round(time.time() - call_start, 2))
                            except Exception as failover_e:
                                with TRANSCRIPTION_LOCK:
                                    TRANSCRIPTION_STATE["status"] = "error"
                                    TRANSCRIPTION_STATE["error_message"] = f"Spectrum Blackout: {failover_e}"
                                    _update_active_agent("TRANSCRIBER_LEAD", model_override or "unknown", provider, "error")
                                return

                            with TRANSCRIPTION_LOCK:
                                TRANSCRIPTION_STATE["current_extracted_text"] = raw_text.strip()
                                TRANSCRIPTION_STATE["is_new_chunk"] = True

                    if _abort_requested():
                        continue

                    # ─── PAGE EXTRACTION (shared by both routes) ───
                    pages = re.findall(r"<page>.*?</page>", raw_text, re.DOTALL)
                    new_page_entries = []
                    for p in pages:
                        num_match = re.search(r"<number>(.*?)</number>", p, re.DOTALL)
                        text_match = re.search(r"<text>(.*?)</text>", p, re.DOTALL)
                        if not (num_match and text_match):
                            continue
                        t_text = text_match.group(1).strip()
                        extracted_num = num_match.group(1).strip()

                        # [FIDELITY]: Filename sequence number wins; the AI's
                        # guess is a fallback for opaque filenames only.
                        final_page_num = str(extract_sequence_number(label) or i)
                        if extracted_num.isdigit() and not extract_sequence_number(label):
                            final_page_num = str(int(extracted_num) + TRANSCRIPTION_STATE["offset_delta"])

                        if save_page_artifact(folder_path, final_page_num, t_text, label, int(final_page_num)):
                            page_data = {
                                "extracted_page_number": final_page_num,
                                "raw_extracted_number": extracted_num,
                                "text": t_text,
                                "preview": " ".join(t_text.split()[:10]) + "..." if t_text else "",
                                "source_file": os.path.basename(label),
                                "physical_index": int(final_page_num),
                            }
                            with TRANSCRIPTION_LOCK:
                                master_pages.append(page_data)
                            new_page_entries.append(page_data)
                        else:
                            print(f"OCR JOB WARNING: Physical save failed for page {final_page_num}.")

                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["processed_images"] += 1
                        TRANSCRIPTION_STATE["last_processed_file"] = os.path.basename(label)
                        TRANSCRIPTION_STATE["error_message"] = (
                            f"Page {TRANSCRIPTION_STATE['processed_images']} of "
                            f"{total_images_target} digitized — {os.path.basename(label)}"
                        )
                        TRANSCRIPTION_STATE["pages"] = list(master_pages)
                        TRANSCRIPTION_STATE["page_audits"] = [
                            {"page": pg.get("extracted_page_number", "?"),
                             "preview": pg.get("preview", ""),
                             "source_file": pg.get("source_file", "unknown")}
                            for pg in master_pages
                        ]
                        # [SMART STREAM]: Feed the editor's incremental poll buffer
                        TRANSCRIPTION_STATE.setdefault("stream_buffer", []).extend([
                            {"index": pg["physical_index"], "text": pg["text"],
                             "filename": pg["source_file"]}
                            for pg in new_page_entries
                        ])

                    # ─── ATOMIC CACHE COMMIT ───
                    temp_cache = cache_file + f".tmp_{threading.get_ident()}"
                    try:
                        with TRANSCRIPTION_LOCK:
                            master_pages_copy = list(master_pages)
                        with open(temp_cache, "w", encoding="utf-8") as f:
                            json.dump({"processed_index": i + 1, "pages": master_pages_copy}, f)
                            f.flush()
                            os.fsync(f.fileno())
                        for retry in range(5):
                            try:
                                os.replace(temp_cache, cache_file)
                                break
                            except PermissionError:
                                if retry == 4:
                                    print("OCR JOB WARNING: Persistent permission denied on cache update.")
                                else:
                                    time.sleep(0.5)
                    except Exception as disk_e:
                        print(f"OCR JOB DISK ERROR: Failed to update cache: {disk_e}")
                    finally:
                        if os.path.exists(temp_cache):
                            try:
                                os.remove(temp_cache)
                            except Exception:
                                pass

                    # ─── ARCHIVE THE SOURCE ASSET ───
                    try:
                        archive_dir = os.path.join(folder_path, TRANSCRIPTION_ARTIFACTS_DIR)
                        os.makedirs(archive_dir, exist_ok=True)
                        dest_path = os.path.join(archive_dir, os.path.basename(label))
                        if os.path.exists(dest_path):
                            if os.path.exists(label):
                                os.remove(label)
                        elif os.path.exists(label):
                            shutil.move(label, dest_path)
                    except Exception as move_e:
                        print(f"OCR JOB WARNING: Failed to archive {label}: {move_e}")

                except Exception as loop_e:
                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["status"] = "error"
                        TRANSCRIPTION_STATE["error_message"] = str(loop_e)
                    print(f"OCR JOB ERROR: Worker exception: {loop_e}")
                finally:
                    queue.task_done()

        async def _orchestrator():
            queue = asyncio.Queue()
            jobs_queued = 0
            for i, f_path in enumerate(all_files):
                if (f"page_{i}.rtf" in existing_rtfs) or (f"page_{i+1}.rtf" in existing_rtfs):
                    with TRANSCRIPTION_LOCK:
                        if TRANSCRIPTION_STATE["processed_images"] <= i:
                            TRANSCRIPTION_STATE["processed_images"] += 1
                            TRANSCRIPTION_STATE["current_batch"] += 1
                    continue
                queue.put_nowait((i, f_path))
                jobs_queued += 1

            if jobs_queued == 0:
                return
            workers = [asyncio.create_task(_consumer(queue)) for _ in range(min(3, jobs_queued))]
            await queue.join()
            for w in workers:
                w.cancel()

        asyncio.run(_orchestrator())

        if _abort_requested():
            _mark_aborted()
            return
        with TRANSCRIPTION_LOCK:
            if TRANSCRIPTION_STATE.get("status") == "error":
                return  # a worker already reported the failure — don't stitch over it

        # [FINAL STITCH]: Unify all physical artifacts into the manuscript
        print("OCR JOB: Digitization complete. Executing final physical stitch...")
        resort_from_cache(folder_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        if _abort_requested():
            _mark_aborted()
        else:
            _fail(str(e))
    finally:
        print("OCR JOB: Transcription thread terminated.")
