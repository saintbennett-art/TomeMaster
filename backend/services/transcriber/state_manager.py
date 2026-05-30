"""
[STATE MANAGER]: Centralized state and lock management for TomeMaster.

Owns TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK, active agent tracking,
persistent ledger (save/load), and diary logging.
"""
import os
import copy
import json
import time
import threading


# ─── CORE SHARED STATE ────────────────────────────────────────────
TRANSCRIPTION_LOCK = threading.Lock()
TRANSCRIPTION_STATE = {
    "status": "idle",  # 'idle', 'running', 'complete', 'error'
    "total_images": 0,
    "processed_images": 0,
    "current_batch": 0,
    "total_batches": 0,
    "text": None,
    "error_message": None,
    "current_image_b64": None,
    "current_extracted_text": None,
    "is_new_chunk": False,
    "page_audits": [],
    "mode": "batch",  # 'live' or 'batch'
    "offset_delta": 0,
    "waiting_for_input": False,
    "last_processed_file": None,
    "stream_buffer": [],
    "folder": None,
    "missing_pages_count": 0,
    "diary": [],
    "active_agents": [],  # [{role, model, provider, status}]
}

TRANSCRIPTION_ARTIFACTS_DIR = "Archive"
TRANSCRIPTION_STATE_FILE = "project_ledger.json"

# Tracks whether a stitching thread is actually running in THIS process.
# Unlike the ledger status (which persists across restarts), this is always
# False at boot — prevents stale "stitching" ledger entries from blocking re-runs.
_stitching_active = threading.Event()


# ─── ACTIVE AGENT TRACKING (NERVE CENTER) ─────────────────────────

def _update_active_agent(role: str, model: str, provider: str, status: str):
    """[NERVE CENTER]: Updates or inserts an active agent entry in TRANSCRIPTION_STATE.

    Each entry is {role, model, provider, status}. If the role already exists,
    it gets updated in-place. Status: 'working', 'complete', 'error', 'idle'.
    Must be called inside TRANSCRIPTION_LOCK.
    """
    agents = TRANSCRIPTION_STATE.get("active_agents", [])
    for agent in agents:
        if agent.get("role") == role:
            agent["model"] = model
            agent["provider"] = provider
            agent["status"] = status
            return
    agents.append({"role": role, "model": model, "provider": provider, "status": status})
    TRANSCRIPTION_STATE["active_agents"] = agents


def _clear_active_agents():
    """Resets all agent entries to idle. Must be called inside TRANSCRIPTION_LOCK."""
    TRANSCRIPTION_STATE["active_agents"] = []


# ─── LEDGER PERSISTENCE ───────────────────────────────────────────

def log_to_diary(message: str):
    """[DIARY]: Records a milestone to the project ledger for contextual guidance."""
    global TRANSCRIPTION_STATE
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": timestamp, "message": message}

    if "diary" not in TRANSCRIPTION_STATE:
        TRANSCRIPTION_STATE["diary"] = []

    TRANSCRIPTION_STATE["diary"].append(entry)
    TRANSCRIPTION_STATE["error_message"] = message
    save_persistent_state()


def save_persistent_state():
    """[LEDGER]: Commits the current project state and diary to the local ledger.

    Thread-safe: deep-copies state inside the lock before writing to disk,
    preventing race conditions during fast async updates.
    """
    folder = TRANSCRIPTION_STATE.get("folder")
    if not folder or not os.path.exists(folder):
        return

    ledger_path = os.path.join(folder, TRANSCRIPTION_STATE_FILE)
    try:
        # Deep-copy inside lock to prevent mutation during write
        with TRANSCRIPTION_LOCK:
            data = copy.deepcopy({
                k: v for k, v in TRANSCRIPTION_STATE.items()
                if k not in ["current_image_b64", "stream_buffer"]
            })

        # [SOVEREIGN DNA FOUNDATION]: Preserve the author's voice in the physical ledger
        try:
            from services.style_mirror import MIRROR
            data["authorial_dna"] = MIRROR.dna
        except Exception:
            pass

        with open(ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"LEDGER ERROR: Failed to commit state: {e}")


def load_persistent_state(folder_path: str):
    """[LEDGER]: Instant Hydration — Recovers the absolute truth from the local ledger."""
    global TRANSCRIPTION_STATE
    ledger_path = os.path.join(folder_path, TRANSCRIPTION_STATE_FILE)
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                TRANSCRIPTION_STATE.update(saved)
                TRANSCRIPTION_STATE["folder"] = folder_path

                # [SOVEREIGN DNA RECOVERY]: Hydrate the Style Mirror with persistent voice
                if "authorial_dna" in saved:
                    try:
                        from services.style_mirror import MIRROR
                        MIRROR.load_dna(saved["authorial_dna"])
                    except Exception:
                        pass

                # [EFFICIENCY]: If the ledger says we are done, skip the re-scan
                if TRANSCRIPTION_STATE.get("status") == "complete" and TRANSCRIPTION_STATE.get("text"):
                    print("LEDGER: Instant Hydration Complete. Manuscript delivered.")
                    return True
            return True
        except Exception as e:
            print(f"LEDGER ERROR: Could not read ledger: {e}")
    return False


# ─── STATE RESET ──────────────────────────────────────────────────

def clear_transcription_state():
    """Wipes the global state and disk artifacts to allow for a fresh project start."""
    global TRANSCRIPTION_STATE
    folder = None
    with TRANSCRIPTION_LOCK:
        folder = TRANSCRIPTION_STATE.get("folder")
        TRANSCRIPTION_STATE.update({
            "status": "idle",
            "folder": None,
            "total_images": 0,
            "processed_images": 0,
            "current_batch": 0,
            "total_batches": 0,
            "text": None,
            "error_message": None,
            "current_image_b64": None,
            "current_extracted_text": None,
            "is_new_chunk": False,
            "pages": [],
            "page_audits": [],
            "stream_buffer": [],
            "mode": "batch",
            "offset_delta": 0,
            "waiting_for_input": False,
            "last_processed_file": None,
        })

    # [EDITORIAL CLEANSE]: Remove disk artifacts
    if folder:
        manuscript_path = os.path.join(folder, "Unified_Manuscript.md")
        clean_path = os.path.join(folder, "Clean_Manuscript.md")
        lock_path = manuscript_path + ".STITCH_LOCK"
        for path in [manuscript_path, clean_path, lock_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"[DIRECTORIAL CLEANSE]: Removed {os.path.basename(path)}")
            except Exception as e:
                print(f"[DIRECTORIAL CLEANSE WARNING]: Could not remove {path}: {e}")

    print("[DIRECTORIAL CLEANSE]: Application memory and disk state cleared for new project.")
    return True


# ─── AUDIT HELPERS ────────────────────────────────────────────────

def resolve_audit_input(page_number: str, apply_offset: bool = False):
    """Called by the frontend to resolve an 'UNKNOWN' or 'COLLISION' event."""
    global TRANSCRIPTION_STATE

    from .artifact_steward import to_rtf

    with TRANSCRIPTION_LOCK:
        if not TRANSCRIPTION_STATE.get("waiting_for_input"):
            return False

        folder = TRANSCRIPTION_STATE.get("folder")
        old_filename = TRANSCRIPTION_STATE.get("last_processed_file")

        if folder and old_filename:
            artifacts_dir = os.path.join(folder, TRANSCRIPTION_ARTIFACTS_DIR)
            target_dir = artifacts_dir if os.path.exists(artifacts_dir) else folder

            file_basename = os.path.splitext(old_filename)[0]
            temp_rtf = os.path.join(target_dir, f"UNKNOWN_{file_basename}.rtf")
            if os.path.exists(temp_rtf):
                try:
                    os.remove(temp_rtf)
                except Exception:
                    pass

            pages = TRANSCRIPTION_STATE.get("pages", [])
            if pages:
                last_page = pages[-1]
                last_page["extracted_page_number"] = page_number
                new_rtf_path = os.path.join(target_dir, f"page_{page_number}.rtf")
                with open(new_rtf_path, "w", encoding="utf-8") as f:
                    f.write(to_rtf(last_page.get("text", "")))

        if apply_offset and page_number.isdigit():
            raw_ai_num = TRANSCRIPTION_STATE["pages"][-1].get("raw_extracted_number", "0")
            if raw_ai_num.isdigit():
                TRANSCRIPTION_STATE["offset_delta"] = int(page_number) - int(raw_ai_num)

        TRANSCRIPTION_STATE["waiting_for_input"] = False
        return True


def set_transcription_offset(delta: int):
    """Manually set the page number offset for the remainder of the project."""
    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["offset_delta"] = delta
    return True
