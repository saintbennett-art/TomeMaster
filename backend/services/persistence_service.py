import json
import os
import tempfile
import threading

# [SOVEREIGN PERSISTENCE]: Atomic Seal Protocol
# Ensures manuscript state is never corrupted during a crash or power failure.

SESSION_FILENAME = ".tome_session.json"
_save_lock = threading.Lock()

def save_checkpoint(project_path: str, state_data: dict) -> bool:
    """Writes the current workspace state to disk using an atomic temp-swap."""
    if not os.path.isdir(project_path):
        return False

    state_path = os.path.join(project_path, SESSION_FILENAME)
    
    with _save_lock:
        # 1. Create a secure temporary file in the same directory
        fd, temp_path = tempfile.mkstemp(dir=project_path, prefix=".tome_tmp_", text=True)
        try:
            with os.fdopen(fd, 'w') as tmp:
                json.dump(state_data, tmp, indent=4)
                tmp.flush()
                os.fsync(tmp.fileno()) # Physical hardware flush
            
            # 2. Atomic swap (OS level)
            os.replace(temp_path, state_path)
            return True
        except Exception as e:
            print(f"PERSISTENCE FAILURE: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

def load_checkpoint(project_path: str) -> dict:
    """Retrieves the last verified state from the project root."""
    state_path = os.path.join(project_path, SESSION_FILENAME)
    if not os.path.exists(state_path):
        return {}

    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"RECOVERY FAILURE: {e}")
        return {}
