from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services import settings_service

router = APIRouter()

class SettingsUpdateRequest(BaseModel):
    api_keys: Optional[Dict[str, str]] = None
    preferred_models: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None
    # User-defined OpenAI-compatible endpoints: [{label, base_url, key}]
    custom_providers: Optional[list] = None

def _mask_key(value: str) -> str:
    """Last-4 mask — enough for the UI to show presence, useless to an attacker."""
    if not value:
        return ""
    return f"****{value[-4:]}" if len(value) > 8 else "****"


@router.get("/")
def get_all_settings():
    """[VAULT]: Delivers persistent settings to the UI with API keys masked.

    Raw key values never cross the wire — CORS allows any localhost origin,
    so any local web page could read this endpoint. Use /analysis/vault-sync
    for presence booleans; keys live only in the encrypted vault and env.
    """
    settings = settings_service.load_settings()
    masked = dict(settings)
    masked["api_keys"] = {
        provider: _mask_key(value)
        for provider, value in settings.get("api_keys", {}).items()
    }
    # Custom-provider keys are masked too — labels/URLs cross the wire, keys never do.
    masked["custom_providers"] = [
        {**cp, "key": _mask_key(cp.get("key", ""))}
        for cp in settings.get("custom_providers", [])
    ]
    return masked

@router.post("/update")
def update_settings(req: SettingsUpdateRequest):
    """[VAULT]: Updates and seals settings in the persistent storage."""
    # Convert Pydantic model to dict, filtering out None values
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    
    if settings_service.save_settings(update_data):
        return {"status": "success", "message": "Vault updated successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to update persistent settings.")

@router.get("/keys/{provider}")
def get_key(provider: str):
    """[VAULT]: Returns a last-4 masked preview so the UI can confirm WHICH key is
    sealed — never the prefix (a constant provider tag for cloud keys, real
    entropy for custom ones) and never the raw value."""
    key = settings_service.get_api_key(provider)
    if key:
        return {"provider": provider, "key_masked": _mask_key(key)}
    return {"provider": provider, "key_masked": "NOT_FOUND"}


@router.get("/resolved-models")
def get_resolved_models():
    """[DYNAMIC ROUTING]: Returns the actual models resolved for each role.
    
    When preferred_models is set to "auto", the backend queries the live API
    portfolio and picks the best model per role. This endpoint shows the result.
    """
    roles = [
        "TRANSCRIBER_LEAD", "NARRATIVE_ARCHITECT", "COPY_EDITOR",
        "MARKETING_ANALYST", "SOVEREIGN_LIAISON"
    ]
    models = {}
    for role in roles:
        config = settings_service.get_model_for_role(role)
        models[role] = {
            "model": config.get("model", "unknown"),
            "provider": config.get("provider", "unknown"),
        }
    return {"models": models}
