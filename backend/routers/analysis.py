from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from services import ai_service
from services.style_mirror import MIRROR
from fastapi.responses import StreamingResponse
import json
import asyncio
import platform
import sys
import os
import shutil
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

router = APIRouter()

@router.get("/vault-sync")
async def sync_vault_from_env():
    # [SOVEREIGN RECOVERY]: Extract keys from the server bedrock
    return {
        "gemini": os.environ.get("GEMINI_API_KEY", ""),
        "openai": os.environ.get("OPENAI_API_KEY", ""),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY", "")
    }

class VaultSaveRequest(BaseModel):
    keys: Dict[str, str]

@router.post("/vault-save")
async def save_vault_to_env(req: VaultSaveRequest):
    # [SOVEREIGN ANCHORING]: Write keys back to the server bedrock
    env_path = ".env" # Check root first
    if not os.path.exists(env_path):
        env_path = "backend/.env"
        
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        key_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY"
        }
        
        new_lines = []
        updated_keys = set()
        
        for line in lines:
            found = False
            for provider, env_var in key_map.items():
                if line.startswith(f"{env_var}="):
                    if provider in req.keys and req.keys[provider]:
                        new_lines.append(f"{env_var}={req.keys[provider]}\n")
                        updated_keys.add(provider)
                        found = True
                        break
            if not found:
                new_lines.append(line)
        
        # Add any keys that weren't already in the file
        for provider, env_var in key_map.items():
            if provider in req.keys and req.keys[provider] and provider not in updated_keys:
                new_lines.append(f"{env_var}={req.keys[provider]}\n")
        
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        # Update current process environment so sync works immediately
        for provider, env_var in key_map.items():
            if provider in req.keys and req.keys[provider]:
                os.environ[env_var] = req.keys[provider]
                
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vault Anchoring Failure: {str(e)}")

@router.get("/pulse")
async def boardroom_pulse_endpoint():
    """Real-Time Pulse: Streams expert handshake progress to all UI subscribers via Server-Sent Events."""
    async def event_generator():
        # [NEURAL TELEMETRY]: Real-time heartbeat of the specialist boardroom
        while True:
            # Calculate neural load based on CPU activity
            load = psutil.cpu_percent() if PSUTIL_AVAILABLE else 0
            yield f"data: {json.dumps({'pulse': 'active', 'neural_load': load, 'timestamp': time.time()})}\n\n"
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
    analytic_scope: Optional[str] = 'full'
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
    """[SUPER MUSE]: Smooths dictated prose into Ron's authorial style."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        # [SOVEREIGN INJECTION]: Force the Style Mirror DNA into the refinement prompt
        prefix = MIRROR.get_muse_prompt_prefix()
        prompt = f"{prefix}\n\nREWRITE THIS DICTATION FOR FLOW AND FIDELITY. MAINTAIN ALL CORE MEANING BUT SMOOTH THE TRANSCRIPTION ARTIFACTS:\n\n{req.text}"
        
        # [MASTER DIRECTIVE]: Mandating GPT-4o for refinement
        result = await ai_service.run_boardroom_parallel(
            prompt, 
            ["Editor-in-Chief"], 
            req.provider or "openai", 
            req.api_key, 
            model="gpt-4o",
            local_mode=False
        )
        # Extract refined text from the agent response
        refined = result.get("Editor-in-Chief", {}).get("feedback", req.text)
        return {"refined": refined}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/briefing")
async def get_briefing_endpoint(folder_path: str, provider: str = "openai", api_key: str = None):
    """[DIRECTORIAL BRIEFING]: Generates a session summary and priority audit."""
    try:
        from services import ledger
        # [SOVEREIGN AUDIT]: Pulling data from the ledger
        stats = ledger.get_stats(folder_path)
        
        # [INTEL SYNTHESIS]: Constructing the briefing prompt
        prompt = f"AUDIT THIS PROJECT DATA AND PROVIDE A 3-SENTENCE DIRECTORIAL BRIEFING FOR THE ARCHITECT. FOCUS ON RECENT PROGRESS AND THE TOP 2 NARRATIVE GAPS. DATA: {json.dumps(stats)}"
        
        result = await ai_service.run_boardroom_parallel(
            prompt, 
            ["Sovereign Liaison"], 
            provider, 
            api_key, 
            model="gpt-4o",
            local_mode=False
        )
        briefing = result.get("Sovereign Liaison", {}).get("feedback", "Operational link established. The boardroom is standing by.")
        return {"briefing": briefing}
    except Exception as e:
        return {"briefing": "Directorial link established. Standing by for manuscript resurrection."}

@router.post("/save-recording")
async def save_recording_endpoint(
    file: UploadFile = File(...),
    folder_path: str = Form(...)
):
    """[DIRECTORIAL CAPTURE]: Persists a demo recording to the project root."""
    try:
        # Ensure the directory exists
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            
        timestamp = int(time.time())
        filename = f"TomeMaster_Demo_{timestamp}.webm"
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"success": True, "path": file_path, "filename": filename}
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
        
        # Ensure the directory exists
        if not os.path.exists(req.folder_path):
            os.makedirs(req.folder_path, exist_ok=True)
            
        # Parse the data URL
        header, encoded = req.data_url.split(",", 1)
        data = base64.b64decode(encoded)
        
        timestamp = int(time.time())
        filename = f"TomeMaster_Snapshot_{timestamp}.png"
        file_path = os.path.join(req.folder_path, filename)
        
        with open(file_path, "wb") as f:
            f.write(data)
            
        return {"success": True, "path": file_path, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot Archival Failure: {str(e)}")

@router.post("/emotional-arc")
async def analyze_emotional_arc(req: TextRequest):
    """Analyzes the emotional arc of a manuscript chunk/full text."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        result = await ai_service.analyze_emotional_arc_async(req.text, req.provider, req.api_key, model=req.model, local_mode=req.local_mode)
        return result
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
    """
    [THE ARCHITECT]: Scans the unified manuscript to suggest chapter breaks 
    and calculate chapter-by-chapter emotional arcs.
    """
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")
    try:
        # [SOVEREIGN DISPATCH]: Using Gemini 3.1 Pro as the primary structural engine
        result = await ai_service.run_structural_analysis_async(
            req.content, req.provider, req.api_key, 
            model=req.model or "gemini-3.1-pro-preview", 
            local_mode=req.local_mode
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MoodboardRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None

@router.post("/moodboard")
async def generate_moodboard(req: MoodboardRequest):
    """Generates an atmospheric visual and auditory moodboard for a scene."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Scene text is required")
    try:
        result = await ai_service.generate_moodboard_async(
            req.text, req.provider, req.api_key, req.model
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EnhancementRequest(BaseModel):
    content: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None

@router.post("/sentinel")
async def run_continuity_sentinel(req: EnhancementRequest):
    """Audits manuscript for logical inconsistencies and character drift."""
    try:
        return await ai_service.run_sentinel_async(req.content, req.provider, req.api_key, req.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/heatmap")
async def run_pacing_heatmap(req: EnhancementRequest):
    """Calculates real-time pacing density and narrative tension heatmap."""
    try:
        return await ai_service.run_heatmap_async(req.content, req.provider, req.api_key, req.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dynamic-arc")
async def run_dynamic_arc(req: EnhancementRequest):
    """Interactive emotional arc adjustment with plot-point recommendations."""
    try:
        return await ai_service.run_dynamic_arc_async(req.content, req.provider, req.api_key, req.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DraftExpertRequest(BaseModel):
    content: str
    persona: str
    user_chapters: Optional[List[dict]] = None
    synthesis_mode: Optional[bool] = False

@router.post("/convene")
async def convene_boardroom(req: MultiAgentRequest):
    """Dispatches manuscript to requested AI specialists simultaneously."""
    if not req.content or not req.requested_personas:
        raise HTTPException(status_code=400, detail="Content and requested_personas are required")
    try:
        # COLLECT ALL ANCHORED BRAINS FOR BEST-USE ORCHESTRATION
        all_keys = {
            "gemini": req.api_key if req.provider == "gemini" else os.environ.get("GEMINI_API_KEY"),
            "anthropic": req.api_key if req.provider == "anthropic" else os.environ.get("ANTHROPIC_API_KEY"),
            "openai": req.api_key if req.provider == "openai" else os.environ.get("OPENAI_API_KEY"),
            "emergent": req.api_key if req.provider == "emergent" else os.environ.get("EMERGENT_API_KEY")
        }
        payload = await ai_service.run_boardroom_parallel(
            req.content, 
            req.requested_personas, 
            req.provider or "gemini", 
            req.api_key, 
            model=req.model,
            user_chapters=req.user_chapters,
            key_bundle=req.key_bundle,
            ledger=req.ledger,
            force_primary=req.force_primary,
            local_mode=req.local_mode,
            synthesis_mode=req.synthesis_mode,
            all_keys=all_keys,
            custom_prompt=req.custom_prompt,
            project_folder=req.project_folder
        )
        if not payload:
            raise ValueError("All requested Board Members failed to respond. Please check your credentials and model availability.")
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
        prompt, is_json = ai_service._build_prompt(req.content, req.persona, req.user_chapters, req.synthesis_mode)
        return {
            "prompt": prompt,
            "is_json": is_json,
            "persona": req.persona
        }
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
        return await ai_service.get_total_expenditure_async()
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
            headers={"Content-Disposition": 'attachment; filename="tome_master_Analysis_Report.docx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/moodboard")
async def get_moodboard(req: CreativeRequest):
    """Generates visual scene inspiration."""
    try:
        return await ai_service.analyze_moodboard_async(req.text, req.provider, req.api_key, model=req.model, local_mode=req.local_mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/world-bible")
async def get_world_bible(req: CreativeRequest):
    """Extracts characters and locations (World-Building Wiki)."""
    try:
        return await ai_service.analyze_world_bible_async(req.text, req.provider, req.api_key, model=req.model, local_mode=req.local_mode)
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
            ai_service.validate_key_async(req.provider, req.api_key, model=req.model, custom_url=req.custom_url),
            timeout=60.0
        )
        return result
    except asyncio.TimeoutError:
        return {"success": False, "message": "Local Resource Saturation: Engine Handshake Timed Out (30s). Please check CPU usage."}
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
    """Returns an AI-driven processing duration estimate."""
    try:
        estimate = await ai_service.forecast_boardroom_duration_async(
            req.word_count,
            req.persona_count,
            req.provider,
            req.api_key,
            req.model
        )
        return {"estimate": estimate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/list-models")
async def list_ai_models(req: ValidateKeyRequest):
    """Discovery Pulse: Returns the authorized portfolio of models for the given provider."""
    try:
        result = await asyncio.wait_for(
            ai_service.list_models_async(req.provider, req.api_key),
            timeout=10.0
        )
        return result
    except asyncio.TimeoutError:
        return {"success": False, "message": "Discovery Timeout (10s).", "models": []}
    except Exception as e:
        return {"success": False, "message": f"Discovery Failure: {str(e)}", "models": []}

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
                "warning": "Hardware Telemetry Unavailable: psutil sensor missing."
            }
            
        total_ram = psutil.virtual_memory().total / (1024**3) # GB
        available_ram = psutil.virtual_memory().available / (1024**3) # GB
        cpu_count = psutil.cpu_count(logical=False)
        cpu_logical = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percentage(interval=0.1)
        
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
            "warning": warning
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
        print("BOARDROOM: LOCAL MODE KILL SWITCH ACTIVATED. Deactivating Ollama pathways...")
        ai_service.KILL_LOCAL_MODE = True
        return {"status": "deactivated", "message": "Local Mode has been forcibly deactivated. The Boardroom will now rely on Cloud intelligence."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
