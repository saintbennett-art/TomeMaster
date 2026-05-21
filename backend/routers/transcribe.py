from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from services import transcriber_service
import os
import sys
import threading

router = APIRouter()

from schemas import TranscribeRequestSchema

class AuditResolutionRequest(BaseModel):
    page_number: str
    apply_offset: bool = False

class PipelineRequest(BaseModel):
    """Request body for the CrewAI pipeline endpoint."""
    folder_path: str = "./test_batch"

# ─────────────────────────────────────────────────────────
# LEGACY ENDPOINTS — transcriber_service.py (OCR dispatch)
# These remain the default until the CrewAI pipeline is
# battle-tested. The two systems share TRANSCRIPTION_STATE
# so the frontend can poll /status regardless of which was used.
# ─────────────────────────────────────────────────────────

@router.get("/ingest")
async def ingest_project_baseline(folder_path: str):
    """[LEDGER]: Ingests the project baseline and hydrates the UI."""
    success = transcriber_service.ingest_project_baseline(folder_path)
    return {"status": "success" if success else "failed"}

@router.get("/status")
async def get_transcription_status(summary: bool = False):
    """[LEDGER]: Polls the global state and delivers new pages to the UI."""
    with transcriber_service.TRANSCRIPTION_LOCK:
        state = dict(transcriber_service.TRANSCRIPTION_STATE)
        
        # [SMART STREAM]: Destructive fetch of the buffer
        buffer = state.get("stream_buffer", [])
        transcriber_service.TRANSCRIPTION_STATE["stream_buffer"] = []
        
        if summary:
            # Drop heavy data for lightweight polling
            state.pop("text", None)
            state.pop("pages", None)
            # Add the incremental updates
            state["new_pages"] = buffer
            
        return state

@router.post("/start")
def start_transcription(req: TranscribeRequestSchema):
    """Triggers the OCR background thread. All provider/model/key config resolved from Settings vault."""
    from services import settings_service

    # [SOVEREIGN DISCOVERY]: Resolve vision engine from the user's configured vault
    # The API key in settings determines the provider and model — nothing is hardcoded.
    vision_model  = settings_service.get_preferred_model("TRANSCRIBER_LEAD") or \
                    settings_service.get_preferred_model("vision")
    vision_config = settings_service.get_model_for_role("TRANSCRIBER_LEAD")
    provider      = vision_config.get("provider", "gemini")
    api_key       = vision_config.get("key", "")
    model         = vision_config.get("model", vision_model)

    # [FALLBACK CHAIN]: Velocity Engine (Groq) as spectrum fallback
    fallback_config   = settings_service.get_model_for_role("COPY_EDITOR")  # closest to velocity
    fallback_provider = "groq"
    fallback_key      = settings_service.get_api_key("groq")
    fallback_model    = settings_service.get_preferred_model("logic")

    success, used_folder = transcriber_service.start_transcription_background(
        api_key, provider, req.folder_path, req.reset_cache, req.mode, model,
        fallback_provider=fallback_provider, fallback_model=fallback_model
    )
    if not success:
        return {"status": "cancelled"}
    return {"status": "started", "folder_path": used_folder, "provider": provider, "model": model}

@router.post("/clear")
def clear_transcription():
    """Wipes the current transcription state."""
    transcriber_service.clear_transcription_state()
    return {"status": "cleared"}

@router.post("/resolve")
def resolve_audit(req: AuditResolutionRequest):
    """Resumes a paused transcription after user input."""
    success = transcriber_service.resolve_audit_input(req.page_number, req.apply_offset)
    return {"status": "success" if success else "failed"}

@router.get("/resort")
async def resort_manuscript_get(folder_path: str):
    """Triggers manuscript unification."""
    import threading
    from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["status"] = "stitching"
        TRANSCRIPTION_STATE["error_message"] = "Assembling manuscript from root artifacts..."
    if not transcriber_service._stitching_active.is_set():
        thread = threading.Thread(target=transcriber_service.resort_from_cache, args=(folder_path,))
        thread.daemon = True
        thread.start()
    return {"status": "stitching"}


# ─────────────────────────────────────────────────────────
# CREWAI PIPELINE ENDPOINT — TomeMasterPipeline
# [N3 FIX]: Bridges the CrewAI Flow to the FastAPI layer.
# The pipeline runs: Security → Transcription → Chapterization
#   → Marketing + Pacing (parallel) → Watermark/Finalize
# The frontend polls /status as usual — TranscriptionCrew's
# ui_sync_callback writes to TRANSCRIPTION_STATE automatically.
# ─────────────────────────────────────────────────────────

def _run_pipeline_thread(folder_path: str):
    """Background thread: runs the full CrewAI TomeMasterPipeline."""
    from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK

    # Set initial state so the frontend shows progress
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["status"] = "running"
        TRANSCRIPTION_STATE["folder"] = folder_path
        TRANSCRIPTION_STATE["error_message"] = "CrewAI pipeline starting..."
        TRANSCRIPTION_STATE["stream_buffer"] = []

    try:
        # Import the pipeline from the CrewAI source tree
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        src_path = os.path.join(project_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from tomemaster.main import TomeMasterPipeline, TomeMasterState

        # Override the default folder_path with the user's request
        pipeline = TomeMasterPipeline()
        pipeline.state = TomeMasterState(folder_path=folder_path)
        pipeline.kickoff()

        # Pipeline complete — update state with final results
        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["status"] = "complete"
            TRANSCRIPTION_STATE["text"] = pipeline.state.chapterized_book or pipeline.state.raw_manuscript
            TRANSCRIPTION_STATE["error_message"] = None
            # Expose the full pipeline output for the UI
            TRANSCRIPTION_STATE["pipeline_results"] = {
                "raw_manuscript": pipeline.state.raw_manuscript[:500] + "..." if len(pipeline.state.raw_manuscript) > 500 else pipeline.state.raw_manuscript,
                "chapterized": bool(pipeline.state.chapterized_book),
                "marketing_blurb": pipeline.state.marketing_blurb[:300] if pipeline.state.marketing_blurb else None,
                "pacing_report": pipeline.state.pacing_report[:300] if pipeline.state.pacing_report else None,
                "is_freemium": pipeline.state.is_freemium,
            }

    except Exception as e:
        import traceback
        with TRANSCRIPTION_LOCK:
            TRANSCRIPTION_STATE["status"] = "error"
            TRANSCRIPTION_STATE["error_message"] = f"Pipeline error: {str(e)}"
        traceback.print_exc()


@router.post("/start-pipeline")
def start_pipeline(req: PipelineRequest):
    """
    [N3]: Launches the full CrewAI TomeMasterPipeline in a background thread.

    This runs the complete pipeline:
      Phase 0: Vault/license check
      Phase 1: Batch transcription (OCR via vision agents)
      Phase 2: Chapterization (structural editor)
      Phase 3: Marketing + Pacing analysis (parallel fan-out)
      Phase 4: Watermark/finalize

    The frontend polls GET /status as usual — the transcription crew's
    ui_sync_callback writes progress to the shared TRANSCRIPTION_STATE.
    """
    from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK

    with TRANSCRIPTION_LOCK:
        if TRANSCRIPTION_STATE.get("status") == "running":
            return {"status": "already_running", "message": "A transcription is already in progress."}

    thread = threading.Thread(target=_run_pipeline_thread, args=(req.folder_path,), daemon=True)
    thread.start()

    return {
        "status": "started",
        "engine": "crewai_pipeline",
        "folder_path": req.folder_path,
        "message": "Full CrewAI pipeline launched. Poll /status for progress."
    }
