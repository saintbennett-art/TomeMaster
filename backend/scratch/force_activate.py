import json
import os
import platform
import hashlib

LICENSE_FILE = "tome_master.lic"

def get_machine_fingerprint() -> str:
    host = platform.node() or "SOVEREIGN_NODE"
    os_info = platform.system() + platform.release()
    current_path = os.path.abspath(os.getcwd())
    raw = f"{host}-{os_info}-{current_path}"
    return hashlib.sha256(raw.encode()).hexdigest()

def force_activate():
    machine_id = get_machine_fingerprint()
    lic_data = {
        "machine_id": machine_id,
        "status": "active"
    }
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(lic_data, f)
    print(f"Force activated for machine: {machine_id}")

if __name__ == "__main__":
    force_activate()
