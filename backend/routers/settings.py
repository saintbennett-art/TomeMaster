from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services import settings_service

router = APIRouter()

class SettingsUpdateRequest(BaseModel):
    api_keys: Optional[Dict[str, str]] = None
    preferred_models: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None

@router.get("/")
def get_all_settings():
    """[VAULT]: Delivers all persistent settings to the UI."""
    return settings_service.load_settings()

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
