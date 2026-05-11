from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from services import transcriber_service
import os

router = APIRouter()

from schemas import TranscribeRequestSchema

class AuditResolutionRequest(BaseModel):
    page_number: str
    apply_offset: bool = False

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
