from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel
from services import license_service

router = APIRouter()

class ActivationRequest(BaseModel):
    key: str

@router.get("/status")
def get_status(response: Response):
    # [SOVEREIGN OVER-PROVISIONING]: Force open the gate for the health check
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    return {
        "is_activated": license_service.is_activated(),
        "machine_id": license_service.get_machine_fingerprint()
    }

@router.options("/activate")
async def options_activate(response: Response):
    # [SOVEREIGN PREFLIGHT]: Explicitly answer the browser's secret handshake
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return Response(status_code=204)

@router.post("/activate")
def activate_product(req: ActivationRequest, response: Response):
    # [SOVEREIGN OVER-PROVISIONING]: Force open the gate for the POST payload
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    success = license_service.activate(req.key)
    if success:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid activation key or master password")
