"""
[AI BOARDROOM]: Direct-gateway specialist endpoints.

All narrative analysis, prose refinement, and multi-agent dispatch routes.
Extracted from analysis.py in PR #16.

[P0 DIRECT GATEWAY]: The CrewAI BoardroomCrew path (PR #15) shipped without
its `crewai` dependency and made the backend unbootable at import time.
All endpoints now dispatch through ai_service's brand-agnostic gateway
(_call_standard_gateway), which resolves models dynamically from the vault
and honors per-request provider/api_key/model overrides.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services import ai_service
from services.style_mirror import MIRROR
import json
import os

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
    """[SUPER MUSE]: Smooths dictated prose into the author's authorial style."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        # [SOVEREIGN INJECTION]: Force the Style Mirror DNA into the refinement prompt
        prefix = MIRROR.get_muse_prompt_prefix()
        prompt = (
            f"{prefix}\n\nREWRITE THIS DICTATION FOR FLOW AND FIDELITY. MAINTAIN ALL "
            f"CORE MEANING BUT SMOOTH THE TRANSCRIPTION ARTIFACTS:\n\n{req.text}"
        )
        result = await ai_service.run_boardroom_parallel(
            prompt,
            ["Editor-in-Chief"],
            req.provider,
            req.api_key,
            model=req.model,
        )
        refined = result.get("Editor-in-Chief", {}).get("feedback")
        if not refined:
            raise ValueError("Refinement engine returned an empty response.")
        return {"refined": refined}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emotional-arc")
async def analyze_emotional_arc(req: TextRequest):
    """Analyzes the emotional arc of a manuscript chunk/full text via the Narrative Architect role."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        return await ai_service.analyze_emotional_arc_async(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/structural-analysis")
async def perform_structural_analysis(req: StructuralRequest):
    """[THE ARCHITECT]: Chapter breaks and emotional arcs via the Narrative Architect role."""
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")
    try:
        return await ai_service.run_structural_analysis_async(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moodboard")
async def generate_moodboard(req: MoodboardRequest):
    """Generates an atmospheric moodboard for a scene via the Marketing Analyst role."""
    if not req.text:
        raise HTTPException(status_code=400, detail="Scene text is required")
    try:
        return await ai_service.generate_moodboard_async(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentinel")
async def run_continuity_sentinel(req: EnhancementRequest):
    """Audits manuscript for inconsistencies via the Continuity Sentinel role."""
    try:
        return await ai_service.run_sentinel_async(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heatmap")
async def run_pacing_heatmap(req: EnhancementRequest):
    """Pacing density and tension heatmap via the Narrative Architect role."""
    try:
        return await ai_service.run_heatmap_async(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dynamic-arc")
async def run_dynamic_arc(req: EnhancementRequest):
    """Interactive emotional arc adjustment via the Narrative Architect role."""
    try:
        return await ai_service.run_dynamic_arc_async(
            req.content,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convene")
async def convene_boardroom(req: MultiAgentRequest):
    """Dispatches manuscript to all requested specialist roles simultaneously."""
    if not req.content or not req.requested_personas:
        raise HTTPException(
            status_code=400, detail="Content and requested_personas are required"
        )
    try:
        # [DIRECTORIAL OVERRIDE]: A reviewed/edited custom prompt replaces the
        # orchestrator template for this dispatch.
        content = req.custom_prompt or req.content
        payload = await ai_service.run_boardroom_parallel(
            content,
            req.requested_personas,
            req.provider or "gemini",
            req.api_key,
            model=req.model,
            user_chapters=req.user_chapters,
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
    """Extracts characters and locations via the Sovereign Liaison role."""
    try:
        return await ai_service.analyze_world_bible_async(
            req.text,
            provider=req.provider,
            api_key=req.api_key,
            model=req.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/briefing")
async def get_briefing_endpoint(req: BriefingRequest):
    """[DIRECTORIAL BRIEFING]: Generates a session summary and priority audit."""
    try:
        # [LEDGER STATS]: Summarize the project's ai_usage_ledger.jsonl directly.
        # (The former `services.ledger` module never existed — this endpoint
        # silently returned the fallback string for its entire life.)
        ledger_path = os.path.join(req.folder_path, "ai_usage_ledger.jsonl")
        entries = []
        if os.path.isfile(ledger_path):
            with open(ledger_path, "r", encoding="utf-8") as f:
                entries = [json.loads(line) for line in f if line.strip()]
        if not entries:
            return {
                "briefing": "No project activity ledger found yet. "
                "The boardroom is standing by for your first session."
            }
        stats = {
            "total_calls": len(entries),
            "recent_activity": entries[-10:],
        }
        prompt = (
            "AUDIT THIS PROJECT DATA AND PROVIDE A 3-SENTENCE DIRECTORIAL BRIEFING "
            "FOR THE ARCHITECT. FOCUS ON RECENT PROGRESS AND THE TOP 2 NARRATIVE GAPS. "
            f"DATA: {json.dumps(stats)}"
        )
        result = await ai_service.run_boardroom_parallel(
            prompt,
            ["Sovereign Liaison"],
            req.provider,
            req.api_key,
        )
        briefing = result.get("Sovereign Liaison", {}).get(
            "feedback", "Operational link established. The boardroom is standing by."
        )
        return {"briefing": briefing}
    except Exception as e:
        # [ZERO-FLUFF]: Surface the real failure instead of a canned success line.
        import traceback
        traceback.print_exc()
        return {"briefing": f"Briefing unavailable: {str(e)}"}


# [REMOVED]: /expert-stream streamed hardcoded fake "thoughts" on asyncio.sleep
# timers — pure theater, no real telemetry, and no frontend caller. Dropped.


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
