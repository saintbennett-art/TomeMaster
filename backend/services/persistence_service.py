import json
import os
import tempfile
import threading

# [SOVEREIGN PERSISTENCE]: Atomic Seal Protocol
# Ensures manuscript state is never corrupted during a crash or power failure.

SESSION_FILENAME = ".tome_session.json"
# Richer per-manuscript document (draft html/text, TOC, analysis artifacts, metadata).
# Kept separate from the transcription session file so the two never collide.
PROJECT_FILENAME = "tome_master_project.json"
_save_lock = threading.Lock()


def default_workspace_dir() -> str:
    """Fallback folder for drafts with no active project yet (pasted text, pre-open).
    Mirrors the existing ~/TomeMaster/Uploads convention. Created if absent."""
    base = os.path.join(os.path.expanduser("~"), "TomeMaster", "Workspace")
    os.makedirs(base, exist_ok=True)
    return base


def _atomic_write_json(project_path: str, filename: str, state_data: dict) -> bool:
    """Shared atomic temp-swap writer (crash/power-failure safe)."""
    if not os.path.isdir(project_path):
        return False

    state_path = os.path.join(project_path, filename)
    with _save_lock:
        fd, temp_path = tempfile.mkstemp(dir=project_path, prefix=".tome_tmp_", text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                json.dump(state_data, tmp, indent=4)
                tmp.flush()
                os.fsync(tmp.fileno())  # Physical hardware flush
            os.replace(temp_path, state_path)
            return True
        except Exception as e:
            print(f"PERSISTENCE FAILURE: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False


def save_project_state(project_path: str, state_data: dict) -> bool:
    """Persists the manuscript document to tome_master_project.json via atomic
    temp-swap. **Shallow-merges** the incoming keys into any existing file so the
    editor context (draft/toc/analysis) and workstation context (title/author/cover)
    can each save their own slice without clobbering the other's."""
    merged = load_project_state(project_path)
    merged.update(state_data or {})
    return _atomic_write_json(project_path, PROJECT_FILENAME, merged)


def load_project_state(project_path: str) -> dict:
    """Retrieves the manuscript document from the project folder ({} if none)."""
    state_path = os.path.join(project_path, PROJECT_FILENAME)
    if not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"RECOVERY FAILURE: {e}")
        return {}

def save_checkpoint(project_path: str, state_data: dict) -> bool:
    """Writes the current transcription/workspace session to disk (atomic temp-swap)."""
    return _atomic_write_json(project_path, SESSION_FILENAME, state_data)

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
