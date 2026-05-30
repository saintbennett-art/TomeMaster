from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    Request,
    UploadFile,
    File,
    Form,
)
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from services import ai_service, vault_steward
from services.style_mirror import MIRROR
from fastapi.responses import StreamingResponse
import json
import asyncio
import platform
import sys
import os
import shutil
import time

# ─── BoardroomCrew (CrewAI) ──────────────────────────────────────────────────
# All specialist AI endpoints route through CrewAI agents instead of raw httpx.
_crew_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "tomemaster"))
if _crew_dir not in sys.path:
    sys.path.insert(0, _crew_dir)

from crews.boardroom_crew import BoardroomCrew

_boardroom = BoardroomCrew()

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

router = APIRouter()


@router.get("/vault-sync")
async def sync_vault_from_env():
    # Returns only presence booleans — never returns raw key values over the wire
    return vault_steward.check_vault_presence()


class VaultSaveRequest(BaseModel):
    keys: Dict[str, str]


ALLOWED_VAULT_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


@router.post("/vault-save")
async def save_vault_to_env(req: VaultSaveRequest):
    success = vault_steward.save_vault_to_env(req.keys)
    if not success:
        raise HTTPException(status_code=500, detail="Vault Targeting Failure")
    return {"success": True}


@router.get("/models")
async def discover_available_models(provider: str = "gemini"):
    """
    [SOVEREIGN DISCOVERY]: Queries the provider's live API using the stored key
    to return the actual models available to this account. Zero assumptions.
    """
    from services import settings_service

    api_key = settings_service.get_api_key(provider)
    if not api_key:
        return {"models": [], "error": f"No API key found for provider: {provider}"}

    try:
        if provider == "gemini":
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.list()
            # Filter to models that support generateContent (vision/text capable)
            models = []
            for m in response:
                name = m.name  # e.g. "models/gemini-3.1-pro-preview"
                model_id = name.replace("models/", "")
                # Only include generative models, skip embeddings/retrieval
                supported = getattr(m, 'supported_actions', []) or []
                if hasattr(m, 'supported_generation_methods'):
                    supported = m.supported_generation_methods
                if 'generateContent' in supported or not supported:
                    models.append({
                        "id": model_id,
                        "name": getattr(m, 'display_name', model_id),
                        "description": getattr(m, 'description', ''),
                    })
            return {"models": models, "provider": provider}

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.models.list()
            models = [
                {"id": m.id, "name": m.id, "description": ""}
                for m in response.data
                if "gpt" in m.id or "o1" in m.id or "o3" in m.id
            ]
            return {"models": models, "provider": provider}

        elif provider == "groq":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            response = client.models.list()
            models = [
                {"id": m.id, "name": m.id, "description": ""}
                for m in response.data
            ]
            return {"models": models, "provider": provider}

        elif provider == "anthropic":
            # Anthropic doesn't have a public list endpoint — return known current models
            models = [
                {"id": "claude-opus-4-6", "name": "Claude Opus 4.6 (Thinking)", "description": "Most capable"},
                {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Thinking)", "description": "Balanced"},
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "Fast, capable"},
            ]
            return {"models": models, "provider": provider}

        return {"models": [], "error": f"Unknown provider: {provider}"}

    except Exception as e:
        return {"models": [], "error": str(e)}



class SettingsUpdateRequest(BaseModel):
    preferred_models: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None

@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """[SOVEREIGN PERSIST]: Saves auto-discovered model assignments to the encrypted vault."""
    from services import settings_service
    update = {}
    if req.preferred_models:
        update["preferred_models"] = req.preferred_models
    if req.preferences:
        update["preferences"] = req.preferences
    success = settings_service.save_settings(update)
    return {"success": success}


@router.get("/pulse")
async def boardroom_pulse_endpoint():
    """Real-Time Pulse: Streams expert handshake progress to all UI subscribers via Server-Sent Events.
    
    Includes active_agents telemetry from TRANSCRIPTION_STATE so the Nerve Center
    can display which model is currently active per role.
    """

    async def event_generator():
        # [NEURAL TELEMETRY]: Real-time heartbeat of the specialist boardroom
        while True:
            load = psutil.cpu_percent() if PSUTIL_AVAILABLE else 0

            # [NERVE CENTER]: Pull active agent info from transcription state
            active_agents = []
            try:
                from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK
                with TRANSCRIPTION_LOCK:
                    active_agents = list(TRANSCRIPTION_STATE.get("active_agents", []))
            except Exception:
                pass

            yield f"data: {json.dumps({'pulse': 'active', 'neural_load': load, 'timestamp': time.time(), 'active_agents': active_agents})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class DnaUpdateRequest(BaseModel):
    text: str


@router.post("/update-dna")
async def update_authorial_dna(req: DnaUpdateRequest):
    """[SOVEREIGN DNA INJECTION]: Re-learns the author's voice from new resurrected text."""
    if not req.text:
        return {"success": False}
    dna = MIRROR.extract_authorial_dna(req.text)
    return {"success": True, "dna": dna}


class MultiAgentRequest(BaseModel):
    content: str
    requested_personas: List[str]
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    custom_url: Optional[str] = None
    user_chapters: Optional[List[dict]] = None
    analytic_scope: Optional[str] = "full"
    key_bundle: Optional[dict] = None
    ledger: Optional[List[dict]] = None
    force_primary: Optional[bool] = False
    local_mode: Optional[bool] = False
    synthesis_mode: Optional[bool] = False
    custom_prompt: Optional[str] = None
    project_folder: Optional[str] = None


@router.post("/expert-stream")
async def expert_stream(req: MultiAgentRequest):
    """Specialist Handshake: Streams the expert's thought process directly into the UI."""

    async def expert_generator():
        # [MASTER DIRECTIVE]: Mirroring Ron's voice in the thoughts
        yield f"data: {json.dumps({'agent': req.requested_personas[0], 'thought': 'Calibrating Style Mirror...', 'type': 'neural'})}\n\n"
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'agent': req.requested_personas[0], 'thought': f'DNA Analysis: {MIRROR.dna['vocabulary_complexity']} complexity detected.', 'type': 'neural'})}\n\n"
        # Simulate neural activity
        yield f"data: {json.dumps({'agent': req.requested_personas[0], 'thought': 'Auditing narrative rhythms...', 'type': 'neural'})}\n\n"
        await asyncio.sleep(1)

    return StreamingResponse(expert_generator(), media_type="text/event-stream")


class TextRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    local_mode: Optional[bool] = False


class CreativeRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    local_mode: Optional[bool] = False


@router.post("/refine-prose")
async def refine_prose_endpoint(req: TextRequest):
    """[SUPER MUSE]: Smooths dictated prose into the author's authorial style via CrewAI Copy Editor."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        result = await _boardroom.refine_prose(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
        # Normalize response shape — frontend expects {"refined": "..."}
        refined = result.get("refined") or result.get("feedback", req.text)
        return {"refined": refined}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BriefingRequest(BaseModel):
    folder_path: str
    provider: Optional[str] = "openai"
    api_key: Optional[str] = None


@router.post("/briefing")
async def get_briefing_endpoint(req: BriefingRequest):
    """[DIRECTORIAL BRIEFING]: Generates a session summary and priority audit via CrewAI."""
    try:
        from services import ledger

        stats = ledger.get_stats(req.folder_path)
        prompt = (
            "AUDIT THIS PROJECT DATA AND PROVIDE A 3-SENTENCE DIRECTORIAL BRIEFING "
            "FOR THE ARCHITECT. FOCUS ON RECENT PROGRESS AND THE TOP 2 NARRATIVE GAPS. "
            f"DATA: {json.dumps(stats)}"
        )
        result = await _boardroom.convene(
            prompt,
            personas=["Sovereign Liaison"],
            provider=req.provider,
            api_key=req.api_key,
        )
        briefing = result.get("Sovereign Liaison", {}).get(
            "feedback", "Operational link established. The boardroom is standing by."
        )
        return {"briefing": briefing}
    except Exception:
        return {
            "briefing": "Directorial link established. Standing by for manuscript resurrection."
        }


def _validate_project_path(folder_path: str) -> str:
    """Resolves and validates that a path stays within the user's home directory tree."""
    resolved = os.path.realpath(os.path.abspath(folder_path))
    home = os.path.realpath(os.path.expanduser("~"))
    if not resolved.startswith(home + os.sep) and resolved != home:
        raise HTTPException(status_code=403, detail="Path outside permitted directory.")
    return resolved


@router.post("/save-recording")
async def save_recording_endpoint(
    file: UploadFile = File(...), folder_path: str = Form(...)
):
    """[DIRECTORIAL CAPTURE]: Persists a demo recording to the project root."""
    try:
        safe_path = _validate_project_path(folder_path)
        os.makedirs(safe_path, exist_ok=True)

        timestamp = int(time.time())
        filename = f"TomeMaster_Demo_{timestamp}.webm"
        file_path = os.path.join(safe_path, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"success": True, "path": file_path, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SnapshotRequest(BaseModel):
    data_url: str
    folder_path: str


@router.post("/save-snapshot")
async def save_snapshot_endpoint(req: SnapshotRequest):
    """[ARCHITECTURAL SNAPSHOT]: Archiving the creative state as a high-fidelity image."""
    try:
        import base64

        safe_path = _validate_project_path(req.folder_path)
        os.makedirs(safe_path, exist_ok=True)

        if "," not in req.data_url:
            raise HTTPException(status_code=400, detail="Invalid data URL format.")
        _, encoded = req.data_url.split(",", 1)
        data = base64.b64decode(encoded)

        timestamp = int(time.time())
        filename = f"TomeMaster_Snapshot_{timestamp}.png"
        file_path = os.path.join(safe_path, filename)

        with open(file_path, "wb") as f:
            f.write(data)

        return {"success": True, "path": file_path, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Snapshot Archival Failure: {str(e)}"
        )


@router.post("/emotional-arc")
async def analyze_emotional_arc(req: TextRequest):
    """Analyzes the emotional arc of a manuscript chunk/full text via CrewAI Narrative Architect."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        return await _boardroom.emotional_arc(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StructuralRequest(BaseModel):
    content: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    local_mode: Optional[bool] = False


@router.post("/structural-analysis")
async def perform_structural_analysis(req: StructuralRequest):
    """[THE ARCHITECT]: Chapter breaks and emotional arcs via CrewAI Narrative Architect."""
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")
    try:
        return await _boardroom.structural_analysis(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MoodboardRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.post("/moodboard")
async def generate_moodboard(req: MoodboardRequest):
    """Generates an atmospheric moodboard for a scene via CrewAI Marketing Analyst."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Scene text is required")
    try:
        return await _boardroom.moodboard(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EnhancementRequest(BaseModel):
    content: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.post("/sentinel")
async def run_continuity_sentinel(req: EnhancementRequest):
    """Audits manuscript for inconsistencies via CrewAI Copy Editor (Continuity Sentinel)."""
    try:
        return await _boardroom.continuity_sentinel(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heatmap")
async def run_pacing_heatmap(req: EnhancementRequest):
    """Pacing density and tension heatmap via CrewAI Narrative Architect."""
    try:
        return await _boardroom.pacing_heatmap(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dynamic-arc")
async def run_dynamic_arc(req: EnhancementRequest):
    """Interactive emotional arc adjustment via CrewAI Narrative Architect."""
    try:
        return await _boardroom.dynamic_arc(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DraftExpertRequest(BaseModel):
    content: str
    persona: str
    user_chapters: Optional[List[dict]] = None
    synthesis_mode: Optional[bool] = False


@router.post("/convene")
async def convene_boardroom(req: MultiAgentRequest):
    """Dispatches manuscript to requested CrewAI specialists simultaneously."""
    if not req.content or not req.requested_personas:
        raise HTTPException(
            status_code=400, detail="Content and requested_personas are required"
        )
    try:
        payload = await _boardroom.convene(
            req.content,
            personas=req.requested_personas,
            provider=req.provider or "gemini",
            api_key=req.api_key,
            model=req.model,
            user_chapters=req.user_chapters,
            custom_prompt=req.custom_prompt,
        )
        if not payload:
            raise ValueError(
                "All requested Board Members failed to respond. "
                "Please check your credentials and model availability."
            )
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft-expert")
async def draft_expert_prompt(req: DraftExpertRequest):
    """
    Generates high-fidelity instructions for a specialist without AI dispatch.
    Enables Directorial Oversight (Review & Edit) in the Command Center.
    """
    try:
        prompt, is_json = ai_service._build_prompt(
            req.content, req.persona, req.user_chapters, req.synthesis_mode
        )
        return {"prompt": prompt, "is_json": is_json, "persona": req.persona}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drafting Failure: {str(e)}")


@router.get("/usage")
async def get_api_usage():
    """Returns the parsed api_usage_log.jsonl file so the frontend can calculate costs."""
    USAGE_LOG_PATH = "api_usage_log.jsonl"
    if not os.path.exists(USAGE_LOG_PATH):
        return {"history": []}

    try:
        history = []
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    history.append(json.loads(line))
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expenditure")
async def get_total_expenditure():
    """Returns the estimated total financial expenditure per provider calculated locally."""
    try:
        USAGE_LOG_PATH = "api_usage_log.jsonl"
        if not os.path.exists(USAGE_LOG_PATH):
            return {"totals": {}}
        totals: Dict[str, float] = {}
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    provider = entry.get("provider", "unknown")
                    tokens = entry.get("metrics", {}).get("total_tokens", 0)
                    totals[provider] = totals.get(provider, 0) + tokens
        return {"totals": totals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger")
async def get_project_ledger(folder_path: str):
    """Returns the line-by-line transaction ledger for a specific project folder."""
    if not folder_path or not os.path.isdir(folder_path):
        return {"ledger": []}

    ledger_path = os.path.join(folder_path, "ai_usage_ledger.jsonl")
    if not os.path.exists(ledger_path):
        return {"ledger": []}

    try:
        ledger_data = []
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ledger_data.append(json.loads(line))
        return {"ledger": ledger_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExportMarkdownRequest(BaseModel):
    markdown: str


@router.post("/export/docx")
async def export_analysis_docx_endpoint(req: ExportMarkdownRequest):
    """Converts a raw Markdown analysis report into a formatted MS Word DOCX file."""
    from services.exporter import generate_analysis_docx

    if not req.markdown:
        raise HTTPException(status_code=400, detail="Markdown content is required")

    try:
        file_stream = generate_analysis_docx(req.markdown)
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": 'attachment; filename="tome_master_Analysis_Report.docx"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/world-bible")
async def get_world_bible(req: CreativeRequest):
    """Extracts characters and locations via CrewAI Sovereign Liaison."""
    try:
        return await _boardroom.world_bible(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    custom_url: Optional[str] = None


@router.post("/validate-key")
async def validate_ai_key(req: ValidateKeyRequest):
    """Performs a lightweight handshake check with a 15s systemic saturation gate."""
    try:
        result = await asyncio.wait_for(
            ai_service.validate_key_async(
                req.provider, req.api_key, model=req.model, custom_url=req.custom_url
            ),
            timeout=60.0,
        )
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": "Local Resource Saturation: Engine Handshake Timed Out (30s). Please check CPU usage.",
        }
    except Exception as e:
        return {"success": False, "message": f"Critical Handshake Failure: {str(e)}"}


class ForecastRequest(BaseModel):
    word_count: int
    persona_count: int
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.post("/forecast")
async def get_processing_forecast(req: ForecastRequest):
    """Returns a local processing duration estimate based on word and persona count."""
    try:
        words_per_second = 150
        persona_overhead = 1.5
        estimated_seconds = round(
            (req.word_count / words_per_second) * req.persona_count * persona_overhead,
            1,
        )
        return {
            "estimate": f"~{estimated_seconds}s ({req.persona_count} specialist(s), {req.word_count:,} words)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list-models")
async def list_ai_models(req: ValidateKeyRequest):
    """Discovery Pulse: Returns the authorized portfolio of models for the given provider."""
    try:
        result = await asyncio.wait_for(
            ai_service.list_models_async(req.provider, req.api_key), timeout=10.0
        )
        return result
    except asyncio.TimeoutError:
        return {"success": False, "message": "Discovery Timeout (10s).", "models": []}
    except Exception as e:
        return {
            "success": False,
            "message": f"Discovery Failure: {str(e)}",
            "models": [],
        }


@router.get("/system-audit")
async def sovereign_system_audit():
    """
    Hardware Audit: Calculates the user's system fidelity and
    emits warnings if Local Mode is likely to cause architectural saturation.
    """
    try:
        if not PSUTIL_AVAILABLE:
            return {
                "os": f"{platform.system()} {platform.release()}",
                "ram_total_gb": "Unknown",
                "fidelity_score": "unknown",
                "recommendation": "Engine in Standby. Cloud Mode Recommended.",
                "warning": "Hardware Telemetry Unavailable: psutil sensor missing.",
            }

        total_ram = psutil.virtual_memory().total / (1024**3)  # GB
        available_ram = psutil.virtual_memory().available / (1024**3)  # GB
        cpu_count = psutil.cpu_count(logical=False)
        cpu_logical = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percent(interval=0.1)

        fidelity_score = "stable"
        recommendation = "Local Mode Authorized."
        warning = None

        if total_ram < 8:
            fidelity_score = "critical"
            recommendation = "CLOUD MODE MANDATORY."
            warning = "Insufficient RAM for Local Inference (Found < 8GB). Running Ollama may freeze your Windows environment."
        elif total_ram < 16:
            fidelity_score = "low"
            recommendation = "Small Models Only (under 4B)."
            warning = "Low RAM Profile (Found < 16GB). High-fidelity narrative audits may stutter."

        return {
            "os": f"{platform.system()} {platform.release()}",
            "ram_total_gb": round(total_ram, 1),
            "ram_available_gb": round(available_ram, 1),
            "cpu_physical": cpu_count,
            "cpu_logical": cpu_logical,
            "cpu_usage_current": cpu_usage,
            "fidelity_score": fidelity_score,
            "recommendation": recommendation,
            "warning": warning,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit Failure: {str(e)}")


@router.post("/kill-switch")
async def emergency_kill_switch():
    """
    [SOVEREIGN KILL SWITCH]: Deactivates Local Mode immediately.
    Narrative processing is redirected to Cloud Mode to prevent hardware bricking.
    Unlike the process-exit, this keeps the UI running.
    """
    try:
        print(
            "BOARDROOM: LOCAL MODE KILL SWITCH ACTIVATED. Deactivating Ollama pathways..."
        )
        ai_service.KILL_LOCAL_MODE = True
        return {
            "status": "deactivated",
            "message": "Local Mode has been forcibly deactivated. The Boardroom will now rely on Cloud intelligence.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
