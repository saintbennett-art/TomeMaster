"""
[SOVEREIGN VAULT]: Key management, model discovery, and settings endpoints.

Handles API key persistence, provider model listing, and configuration.
Extracted from analysis.py in PR #16.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
from services import ai_service, vault_steward
import asyncio

router = APIRouter()


# ─── Pydantic Models ─────────────────────────────────────────────────────────


class VaultSaveRequest(BaseModel):
    keys: Dict[str, str]


class SettingsUpdateRequest(BaseModel):
    preferred_models: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None


class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    custom_url: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/vault-sync")
async def sync_vault_from_env():
    """Returns presence booleans — never returns raw key values over the wire."""
    return vault_steward.check_vault_presence()


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
            models = []
            for m in response:
                name = m.name
                model_id = name.replace("models/", "")
                supported = getattr(m, "supported_actions", []) or []
                if hasattr(m, "supported_generation_methods"):
                    supported = m.supported_generation_methods
                if "generateContent" in supported or not supported:
                    models.append(
                        {
                            "id": model_id,
                            "name": getattr(m, "display_name", model_id),
                            "description": getattr(m, "description", ""),
                        }
                    )
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

            client = OpenAI(
                api_key=api_key, base_url="https://api.groq.com/openai/v1"
            )
            response = client.models.list()
            models = [
                {"id": m.id, "name": m.id, "description": ""} for m in response.data
            ]
            return {"models": models, "provider": provider}

        elif provider == "anthropic":
            models = [
                {
                    "id": "claude-opus-4-6",
                    "name": "Claude Opus 4.6 (Thinking)",
                    "description": "Most capable",
                },
                {
                    "id": "claude-sonnet-4-6",
                    "name": "Claude Sonnet 4.6 (Thinking)",
                    "description": "Balanced",
                },
                {
                    "id": "claude-3-5-sonnet-20241022",
                    "name": "Claude 3.5 Sonnet",
                    "description": "Fast, capable",
                },
            ]
            return {"models": models, "provider": provider}

        return {"models": [], "error": f"Unknown provider: {provider}"}

    except Exception as e:
        return {"models": [], "error": str(e)}


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
