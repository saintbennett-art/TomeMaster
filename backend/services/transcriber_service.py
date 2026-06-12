"""
[TRANSCRIBER SERVICE]: Facade module — backward-compatible import surface.

All logic has been extracted into focused sub-modules inside backend/services/transcriber/.
This file re-exports every public name so existing imports across the codebase resolve
without modification:

    from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK
    from services.transcriber_service import _get_ai_client
    from services import transcriber_service  # then transcriber_service.resort_from_cache(...)

Sub-module map:
    state_manager.py      — TRANSCRIPTION_STATE, LOCK, ledger, diary, agent tracking
    text_formatter.py     — strip_rtf, restore_text_flow, manuscript markers, paragraph join
    dialog_service.py     — pick_file, pick_directory (native OS pickers)
    ai_engine.py          — _get_ai_client, _call_ai_with_failover, OCR prompts
    industrial_stitcher.py — resort_from_cache, ingest_project_baseline
    post_stitch_cleanup.py — Phase 2 cleanup pipeline (already existed)
    asset_scanner.py       — natural_sort_key, extract_sequence_number (already existed)
    artifact_steward.py    — to_rtf, save_page_artifact (already existed)
    vision_processor.py    — is_parseable_document, parse_document_text (already existed)
    legacy_parser.py       — .doc, .wpd, .wps, .odt parsing (already existed)
"""

# ─── STATE MANAGER ────────────────────────────────────────────────
from .transcriber.state_manager import (  # noqa: F401
    TRANSCRIPTION_LOCK,
    TRANSCRIPTION_STATE,
    TRANSCRIPTION_ABORT,
    TRANSCRIPTION_ARTIFACTS_DIR,
    TRANSCRIPTION_STATE_FILE,
    _stitching_active,
    _update_active_agent,
    _clear_active_agents,
    log_to_diary,
    save_persistent_state,
    load_persistent_state,
    clear_transcription_state,
    resolve_audit_input,
    set_transcription_offset,
)

# ─── TEXT FORMATTER ────────────────────────────────────────────────
from .transcriber.text_formatter import (  # noqa: F401
    strip_rtf,
    restore_text_flow_if_fragmented,
    check_and_strip_manuscript_markers,
    _should_join_paragraphs,
)

# ─── DIALOG SERVICE ───────────────────────────────────────────────
from .transcriber.dialog_service import (  # noqa: F401
    pick_file,
    pick_directory,
)

# ─── AI ENGINE ─────────────────────────────────────────────────────
from .transcriber.ai_engine import (  # noqa: F401
    OCR_PROMPT,
    MANUSCRIPT_REDLINE_PROMPT,
    _get_ai_client,
    _call_ai_with_failover,
)

# ─── INDUSTRIAL STITCHER ──────────────────────────────────────────
from .transcriber.industrial_stitcher import (  # noqa: F401
    ingest_project_baseline,
    resort_from_cache,
)

# ─── EXISTING SUB-MODULES (re-export for backward compat) ─────────
from .transcriber import asset_scanner, vision_processor, artifact_steward  # noqa: F401

natural_sort_key = asset_scanner.natural_sort_key
industrial_sort_key = natural_sort_key
extract_sequence_number = asset_scanner.extract_sequence_number
save_page_artifact = artifact_steward.save_page_artifact
to_rtf = artifact_steward.to_rtf

# ─── UI WINDOW (desktop app sets this) ────────────────────────────
# desktop_app.py does: transcriber_service.UI_WINDOW = window
# We use a property-like pattern via __setattr__ to propagate the assignment
# into dialog_service where pick_file/pick_directory actually use it.
from .transcriber import dialog_service as _dialog_service

UI_WINDOW = _dialog_service.UI_WINDOW  # initial value (None)


def _set_ui_window(window):
    """Propagate UI_WINDOW assignment to dialog_service."""
    global UI_WINDOW
    UI_WINDOW = window
    _dialog_service.UI_WINDOW = window


def start_transcription_background(
    api_key: str,
    provider: str,
    folder_path: str = None,
    reset_cache: bool = False,
    mode: str = "batch",
    model: str = None,
    fallback_provider: str = None,
    fallback_model: str = None,
):
    """Dispatcher: Spawns the folder picker and launches the CrewAI pipeline.

    The legacy run_transcription_job() has been removed. This function now wires
    directly to the CrewAI TomeMasterPipeline via _run_pipeline_thread in
    routers/transcribe.py.
    """
    import os
    import threading as _threading

    current_status = TRANSCRIPTION_STATE.get("status", "standby")
    with TRANSCRIPTION_LOCK:
        if current_status in ["running", "indexing", "processing"] and not reset_cache:
            print(
                f"BOARDROOM: Re-entrancy blocked. Engine is already in {current_status} "
                f"mode for {TRANSCRIPTION_STATE.get('folder')}"
            )
            return True, TRANSCRIPTION_STATE.get("folder")
        TRANSCRIPTION_STATE["status"] = "Initializing file system..."

    folder = folder_path if folder_path else pick_directory()
    if not folder:
        return False, None

    # [SOVEREIGN ANCHOR]: Ingest baseline for the new folder
    ingest_project_baseline(folder)

    # [SOVEREIGN RESET]: Optional hard-wipe
    if reset_cache:
        cache_path = os.path.join(folder, "_tome_master_cache.json")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception:
                pass

    # Initialize state
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE.update({
            "folder": folder,
            "status": "indexing",
            "progress": 0,
            "processed_images": 0,
            "total_images": 0,
            "error_message": "Assembling high-velocity scanning engine...",
            "current_image_b64": None,
            "current_extracted_text": None,
            "is_new_chunk": False,
            "pages": [],
            "page_audits": [],
            "stream_buffer": [],
            "total_batches": 0,
            "current_batch": 0,
            "text": None,
        })

    # [ABORT RESET]: A new job invalidates any prior abort request
    TRANSCRIPTION_ABORT.clear()

    # [CREWAI PIPELINE]: Launch via the pipeline thread
    from routers.transcribe import _run_pipeline_thread

    job_thread = _threading.Thread(
        target=_run_pipeline_thread,
        args=(folder,),
        daemon=True,
    )
    job_thread.start()

    return True, folder
