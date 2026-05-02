import os
import platform
import hashlib

def get_machine_fingerprint() -> str:
    host = platform.node() or "SOVEREIGN_NODE"
    os_info = platform.system() + platform.release()
    current_path = os.path.abspath(os.getcwd())
    raw = f"{host}-{os_info}-{current_path}"
    return hashlib.sha256(raw.encode()).hexdigest()

print(f"Current fingerprint: {get_machine_fingerprint()}")
print(f"CWD: {os.getcwd()}")
