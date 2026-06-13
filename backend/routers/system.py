"""
[SOVEREIGN TELEMETRY]: System monitoring, file operations, usage tracking, and diagnostics.

Handles pulse heartbeat, recording/snapshot saves, API usage ledger,
export, forecasting, hardware audit, and kill switch.
Extracted from analysis.py in PR #16.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Optional
from services import ai_service
from fastapi.responses import StreamingResponse
import json
import asyncio
import platform
import os
import shutil
import time

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

router = APIRouter()


# ─── Pydantic Models ─────────────────────────────────────────────────────────


class SnapshotRequest(BaseModel):
    data_url: str
    folder_path: str


class ExportMarkdownRequest(BaseModel):
    markdown: str


class ForecastRequest(BaseModel):
    word_count: int
    persona_count: int
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


# [SHARED GUARDRAIL]: One canonical path validator for every router.
from services.security import validate_project_path as _validate_project_path


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/pulse")
async def boardroom_pulse_endpoint():
    """Real-Time Pulse: Streams expert handshake progress to all UI subscribers via SSE.

    Includes active_agents telemetry from TRANSCRIPTION_STATE so the Nerve Center
    can display which model is currently active per role.
    """

    async def event_generator():
        while True:
            load = psutil.cpu_percent() if PSUTIL_AVAILABLE else 0

            active_agents = []
            try:
                from services.transcriber_service import (
                    TRANSCRIPTION_STATE,
                    TRANSCRIPTION_LOCK,
                )

                with TRANSCRIPTION_LOCK:
                    active_agents = list(
                        TRANSCRIPTION_STATE.get("active_agents", [])
                    )
            except Exception:
                pass

            yield f"data: {json.dumps({'pulse': 'active', 'neural_load': load, 'timestamp': time.time(), 'active_agents': active_agents})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    """Returns total TOKEN consumption per provider from the local ledger.

    These are token counts, not currency — the app does not have per-model
    pricing, so it cannot compute a dollar figure. The `unit` field makes that
    explicit for any UI rendering the values.
    """
    try:
        USAGE_LOG_PATH = "api_usage_log.jsonl"
        if not os.path.exists(USAGE_LOG_PATH):
            return {"totals": {}, "unit": "tokens"}
        totals: Dict[str, int] = {}
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    provider = entry.get("provider", "unknown")
                    tokens = entry.get("metrics", {}).get("total_tokens", 0)
                    totals[provider] = totals.get(provider, 0) + tokens
        return {"totals": totals, "unit": "tokens"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger")
async def get_project_ledger(folder_path: str):
    """Returns the line-by-line transaction ledger for a specific project folder."""
    if not folder_path:
        return {"ledger": []}
    safe_path = _validate_project_path(folder_path)
    if not os.path.isdir(safe_path):
        return {"ledger": []}

    ledger_path = os.path.join(safe_path, "ai_usage_ledger.jsonl")
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


@router.post("/forecast")
async def get_processing_forecast(req: ForecastRequest):
    """Returns a local processing duration estimate based on word and persona count."""
    try:
        words_per_second = 150
        persona_overhead = 1.5
        estimated_seconds = round(
            (req.word_count / words_per_second)
            * req.persona_count
            * persona_overhead,
            1,
        )
        return {
            "estimate": f"~{estimated_seconds}s ({req.persona_count} specialist(s), {req.word_count:,} words)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        total_ram = psutil.virtual_memory().total / (1024**3)
        available_ram = psutil.virtual_memory().available / (1024**3)
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
