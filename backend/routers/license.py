from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import license_service

router = APIRouter()

class ActivationRequest(BaseModel):
    key: str

@router.get("/status")
def get_status():
    return {
        "is_activated": license_service.is_activated(),
        "machine_id": license_service.get_machine_fingerprint()
    }

@router.post("/activate")
def activate_product(req: ActivationRequest):
    success = license_service.activate(req.key)
    if success:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid activation key or master password")
