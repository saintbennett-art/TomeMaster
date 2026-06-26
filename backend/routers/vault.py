"""
[SOVEREIGN VAULT]: Key management, model discovery, and settings endpoints.

Handles API key persistence, provider model listing, and configuration.
Extracted from analysis.py in PR #16.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
from services import ai_service
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


ALLOWED_VAULT_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


@router.get("/vault-sync")
async def sync_vault_from_env():
    """Returns presence booleans — never returns raw key values over the wire.

    Reads the encrypted vault (canonical store) and falls back to the hydrated
    process env, so presence is correct whether or not keys were saved this session.
    """
    from services import settings_service

    api_keys = settings_service.load_settings().get("api_keys", {}) or {}
    return {
        provider: bool((api_keys.get(provider) or "").strip())
        or bool(os.environ.get(env_var, "").strip())
        for provider, env_var in ALLOWED_VAULT_KEYS.items()
    }


@router.post("/vault-save")
async def save_vault_to_env(req: VaultSaveRequest):
    """[VAULT SEAL]: Persists keys to the encrypted vault (settings.enc) ONLY —
    no plaintext .env is written. Propagates to the live process env so the
    running gateway sees new keys without a restart, and invalidates the model
    cache (handled inside save_settings) so resolution re-queries the portfolio.
    """
    from services import settings_service

    incoming = {
        provider: str(val).strip()
        for provider, val in (req.keys or {}).items()
        if provider in ALLOWED_VAULT_KEYS and str(val).strip()
    }
    if not incoming:
        raise HTTPException(status_code=400, detail="No valid API keys supplied.")

    existing = settings_service.load_settings().get("api_keys", {}) or {}
    existing.update(incoming)
    if not settings_service.save_settings({"api_keys": existing}):
        raise HTTPException(status_code=500, detail="Vault seal failed.")

    # Propagate to live env (whitelisted providers only) for immediate effect.
    for provider, val in incoming.items():
        os.environ[ALLOWED_VAULT_KEYS[provider]] = val

    return {"success": True}


class VaultClearRequest(BaseModel):
    provider: str


@router.post("/vault-clear")
async def clear_vault_key(req: VaultClearRequest):
    """[VAULT PURGE]: Blanks ONE provider's stored key so the user can recover from
    a wrong value (e.g. a password pasted into the key field). Sets the slot to ""
    — save_settings merges, so "" overwrites the bad value and the presence check
    then reports the slot empty. Also clears the hydrated process env var.
    """
    from services import settings_service

    provider = (req.provider or "").strip().lower()
    if provider not in ALLOWED_VAULT_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    if not settings_service.save_settings({"api_keys": {provider: ""}}):
        raise HTTPException(status_code=500, detail="Vault clear failed.")

    os.environ.pop(ALLOWED_VAULT_KEYS[provider], None)
    return {"success": True}


@router.post("/vault-validate")
async def validate_and_prune_vault():
    """[STALE GUARD]: Live-validate each stored key so the UI's SEALED indicator
    reflects real, working keys. Clears (prunes) a key ONLY when the provider
    DEFINITIVELY rejects it (auth error 400/401/403) — never on a network/timeout
    failure, so a valid key is never lost to a transient blip.

    Returns {"validity": {provider: bool}, "pruned": [providers cleared]}.
    """
    import re
    from services import settings_service

    provs = list(ALLOWED_VAULT_KEYS.keys())  # gemini, openai, anthropic, groq
    stored = {p: settings_service.get_api_key(p) for p in provs}

    async def _check(p):
        k = stored[p]
        if not k:
            return p, "absent", ""
        try:
            res = await asyncio.wait_for(ai_service.validate_key_async(p, k), timeout=12.0)
            return (p, "valid", "") if res.get("success") else (p, "invalid", str(res.get("message", "")))
        except Exception as e:
            return p, "unreachable", str(e)

    checks = await asyncio.gather(*[_check(p) for p in provs])

    validity = {p: (state == "valid") for p, state, _ in checks}
    # [SAFETY]: report-only. NEVER delete keys here — the /models validation
    # false-negatives on some valid keys (it deleted a working Gemini key once).
    # Key removal is a deliberate user action, not an automatic side effect.
    return {"validity": validity, "pruned": []}


def _attach_traits(models):
    """Curate the discovered list to chat-only, dedupe snapshot families, sort
    best-first, then tag each with a short primary-trait label for the UI. Keeps
    the picker clean (no embeddings/whisper/dated dupes) — pattern-based, no name tables."""
    from services import providers

    curated = providers.curate_models(models)
    for m in curated:
        m["trait"] = providers.model_trait(m.get("id", ""))
    return curated


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
            return {"models": _attach_traits(models), "provider": provider}

        elif provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.models.list()
            models = [
                {"id": m.id, "name": m.id, "description": ""}
                for m in response.data
                if "gpt" in m.id or "o1" in m.id or "o3" in m.id
            ]
            return {"models": _attach_traits(models), "provider": provider}

        elif provider == "groq":
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key, base_url="https://api.groq.com/openai/v1"
            )
            response = client.models.list()
            models = [
                {"id": m.id, "name": m.id, "description": ""} for m in response.data
            ]
            return {"models": _attach_traits(models), "provider": provider}

        elif provider == "anthropic":
            # Single source of truth — same portfolio the resolver/validator use.
            from services.settings_service import ANTHROPIC_STATIC_PORTFOLIO

            models = [
                {"id": mid, "name": mid, "description": ""}
                for mid in ANTHROPIC_STATIC_PORTFOLIO
            ]
            return {"models": _attach_traits(models), "provider": provider}

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


_VALIDATE_TIMEOUT_S = 60.0


@router.post("/validate-key")
async def validate_ai_key(req: ValidateKeyRequest):
    """Performs a lightweight handshake (live model-list probe) against the provider."""
    try:
        result = await asyncio.wait_for(
            ai_service.validate_key_async(
                req.provider, req.api_key, model=req.model, custom_url=req.custom_url
            ),
            timeout=_VALIDATE_TIMEOUT_S,
        )
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": (
                f"Handshake timed out after {int(_VALIDATE_TIMEOUT_S)}s — the {req.provider} "
                "model endpoint did not respond. Check the key and your network connection."
            ),
        }
    except Exception as e:
        return {"success": False, "message": f"Critical Handshake Failure: {str(e)}"}


@router.get("/local-engines")
def detect_local_engines():
    """[LOCAL DISCOVERY]: Auto-detect OpenAI-compatible engines running on
    localhost (Ollama / LM Studio / vLLM / llama.cpp / BitNet). Keyless,
    localhost-only, sub-second. Sync def → FastAPI runs it off the event loop.
    """
    from services import providers

    return {"engines": providers.probe_local_engines()}


@router.post("/list-models")
async def list_ai_models(req: ValidateKeyRequest):
    """Discovery Pulse: Returns the authorized portfolio of models for the given
    provider — honoring `custom_url` so exotic/local OpenAI-compatible endpoints
    (Kimi, DeepSeek, a non-default Ollama) resolve their own model list."""
    try:
        result = await asyncio.wait_for(
            ai_service.list_models_async(req.provider, req.api_key, req.custom_url),
            timeout=10.0,
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
