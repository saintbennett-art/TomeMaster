"""
[AI BOARDROOM]: CrewAI specialist endpoints.

All narrative analysis, prose refinement, and multi-agent dispatch routes.
Extracted from analysis.py in PR #16.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services import ai_service
from services.style_mirror import MIRROR
from fastapi.responses import StreamingResponse
import json
import asyncio
import sys
import os

# ─── BoardroomCrew (CrewAI) ──────────────────────────────────────────────────
_crew_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "tomemaster")
)
if _crew_dir not in sys.path:
    sys.path.insert(0, _crew_dir)

from crews.boardroom_crew import BoardroomCrew

_boardroom = BoardroomCrew()

router = APIRouter()


# ─── Pydantic Models ─────────────────────────────────────────────────────────


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


class StructuralRequest(BaseModel):
    content: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    local_mode: Optional[bool] = False


class MoodboardRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


class EnhancementRequest(BaseModel):
    content: str
    provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None


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


class BriefingRequest(BaseModel):
    folder_path: str
    provider: Optional[str] = "openai"
    api_key: Optional[str] = None


class DnaUpdateRequest(BaseModel):
    text: str


class DraftExpertRequest(BaseModel):
    content: str
    persona: str
    user_chapters: Optional[List[dict]] = None
    synthesis_mode: Optional[bool] = False


# ─── Endpoints ────────────────────────────────────────────────────────────────


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
        refined = result.get("refined") or result.get("feedback", req.text)
        return {"refined": refined}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/expert-stream")
async def expert_stream(req: MultiAgentRequest):
    """Specialist Handshake: Streams the expert's thought process directly into the UI."""

    async def expert_generator():
        agent = req.requested_personas[0]
        yield f"data: {json.dumps({'agent': agent, 'thought': 'Calibrating Style Mirror...', 'type': 'neural'})}\n\n"
        await asyncio.sleep(1)
        complexity = MIRROR.dna["vocabulary_complexity"]
        yield f"data: {json.dumps({'agent': agent, 'thought': f'DNA Analysis: {complexity} complexity detected.', 'type': 'neural'})}\n\n"
        yield f"data: {json.dumps({'agent': agent, 'thought': 'Auditing narrative rhythms...', 'type': 'neural'})}\n\n"
        await asyncio.sleep(1)

    return StreamingResponse(expert_generator(), media_type="text/event-stream")


@router.post("/update-dna")
async def update_authorial_dna(req: DnaUpdateRequest):
    """[SOVEREIGN DNA INJECTION]: Re-learns the author's voice from new resurrected text."""
    if not req.text:
        return {"success": False}
    dna = MIRROR.extract_authorial_dna(req.text)
    return {"success": True, "dna": dna}


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
