from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services import settings_service

router = APIRouter()

class SettingsUpdateRequest(BaseModel):
    api_keys: Optional[Dict[str, str]] = None
    preferred_models: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None

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
    """[VAULT]: Retrieves a masked or full key for a specific provider."""
    key = settings_service.get_api_key(provider)
    if key and len(key) > 8:
        # Return masked key for UI security
        return {"provider": provider, "key_masked": f"{key[:4]}...{key[-4:]}"}
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
