import hashlib
import platform

def get_machine_fingerprint():
    host = platform.node() or "SOVEREIGN_NODE"
    os_info = platform.system() + platform.release()
    raw = f"{host}-{os_info}"
    return hashlib.sha256(raw.encode()).hexdigest()

machine_id = get_machine_fingerprint()
combined = f"{machine_id}::TomeMaster-2026-StandardConsulting-Salt"
full_hash = hashlib.sha256(combined.encode()).hexdigest()
prefix = full_hash[:12].upper()
key = f"TOME-{prefix[:4]}-{prefix[4:8]}-{prefix[8:]}"

print(f"Machine ID: {machine_id}")
print(f"License Key: {key}")
