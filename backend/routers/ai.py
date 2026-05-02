import os
import httpx
import time
from fastapi import APIRouter, HTTPException, Query
from services import ai_service
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

@router.get("/ollama-status")
async def get_ollama_status(api_key: Optional[str] = Query(None)):
    """Checks if a local or remote Ollama instance is reachable."""
    try:
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        url = f"{host}/api/tags"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "active", "models": models}
            return {"status": "reachable", "models": []}
    except Exception:
        return {"status": "not_found", "models": []}

@router.get("/models")
async def get_cloud_models(provider: str, api_key: str):
    """Discovery Pulse: Fetches the live list of commissioned models from a cloud provider."""
    try:
        return await ai_service.list_models_async(provider, api_key)
    except Exception as e:
        return {"success": False, "message": str(e), "models": []}

class DiscoverRequest(BaseModel):
    brand_name: str
    provider: str
    api_key: str

@router.post("/discover")
async def discover_ai_gateway(req: DiscoverRequest):
    """Dispatches a Sovereign Scout Mission to identify an unknown provider's gateway URL."""
    try:
        url = await ai_service.discover_gateway_async(req.brand_name, req.provider, req.api_key)
        return {"brand": req.brand_name, "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_ai_status():
    """System Heartbeat: Confirms the AI orchestration engine is online."""
    return {"status": "active", "timestamp": time.time()}
