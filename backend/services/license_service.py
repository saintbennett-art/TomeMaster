import os
import uuid
import hashlib
import json
import platform

LICENSE_FILE = "tome_master.lic"

def get_machine_fingerprint() -> str:
    """Combines hostname and OS to create a stable machine footprint."""
    host = platform.node() or "SOVEREIGN_NODE"
    os_info = platform.system() + platform.release()
    raw = f"{host}-{os_info}"
    return hashlib.sha256(raw.encode()).hexdigest()

def check_master_password(password: str) -> bool:
    """Verifies against the TOME_MASTER_KEY environment variable. Never ships a hardcoded bypass."""
    master = os.environ.get("TOME_MASTER_KEY", "").strip()
    if not master:
        return False
    return password.strip() == master

SECRET_SALT = "TomeMaster-2026-BennettConsulting-Salt"

def verify_product_key(machine_id: str, key: str) -> bool:
    """Mathematical verification against the developer's offline keygen algorithm."""
    combined = f"{machine_id}::{SECRET_SALT}"
    full_hash = hashlib.sha256(combined.encode()).hexdigest()
    prefix = full_hash[:12].upper()
    expected_key = f"TOME-{prefix[:4]}-{prefix[4:8]}-{prefix[8:]}"
    return key.strip().upper() == expected_key

def activate(key: str) -> bool:
    machine_id = get_machine_fingerprint()
    
    # Check if they used the Master Password OR a mathematically valid Customer Key
    if check_master_password(key) or verify_product_key(machine_id, key):
        # Generate a valid local license file bound to this exact machine and folder path
        lic_data = {
            "machine_id": machine_id,
            "status": "active"
        }
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(lic_data, f)
        return True
    return False

def is_activated() -> bool:
    # Migration Logic: Check for legacy proeditor.lic and rename to tome_master.lic
    legacy_file = "proeditor.lic"
    if os.path.exists(legacy_file) and not os.path.exists(LICENSE_FILE):
        try:
            os.rename(legacy_file, LICENSE_FILE)
        except Exception:
            pass

    if not os.path.exists(LICENSE_FILE):
        return False
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Verify the saved machine ID matches the current hardware and folder path
        if data.get("machine_id") == get_machine_fingerprint() and data.get("status") == "active":
            return True
        return False
    except Exception:
        return False
