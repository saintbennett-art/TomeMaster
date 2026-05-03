import os
import json
import threading

# [SOVEREIGN SETTINGS]: Standard filename for persistent application configuration
SETTINGS_FILE = "settings.json"
SETTINGS_LOCK = threading.Lock()

# Default empty schema for the TomeMaster Vault
DEFAULT_SETTINGS = {
    "api_keys": {
        "openai": "",
        "gemini": "",
        "groq": "",
        "anthropic": ""
    },
    "preferred_models": {
        "vision": "gpt-4o",
        "logic": "gemini-3-flash-preview",
        "analysis": "claude-3-5-sonnet-20241022"
    },
    "preferences": {
        "theme": "dark",
        "auto_stitch": True,
        "language": "en"
    }
}

def get_settings_path():
    """Returns the absolute path to the settings vault in the backend root."""
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(backend_root, SETTINGS_FILE)

_PERMITTED_TOP_KEYS = set(DEFAULT_SETTINGS.keys())
_PERMITTED_API_KEYS = {"openai", "gemini", "groq", "anthropic"}
_PERMITTED_MODEL_KEYS = {"vision", "logic", "analysis"}
_PERMITTED_PREF_KEYS = {"theme", "auto_stitch", "language"}

def _validate_settings(data: dict) -> dict:
    """Returns a copy of data with only permitted keys — drops unknown fields."""
    clean = {}
    for key in _PERMITTED_TOP_KEYS:
        if key not in data:
            continue
        if key == "api_keys":
            clean[key] = {k: str(v) for k, v in data[key].items() if k in _PERMITTED_API_KEYS}
        elif key == "preferred_models":
            clean[key] = {k: str(v) for k, v in data[key].items() if k in _PERMITTED_MODEL_KEYS}
        elif key == "preferences":
            clean[key] = {k: data[key][k] for k in _PERMITTED_PREF_KEYS if k in data[key]}
        else:
            clean[key] = data[key]
    return clean

def load_settings():
    """[VAULT HYDRATION]: Recovers settings from disk or returns defaults if missing."""
    path = get_settings_path()
    if not os.path.exists(path):
        return DEFAULT_SETTINGS

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return _validate_settings(raw)
    except Exception as e:
        print(f"SETTINGS ERROR: Failed to hydrate vault: {e}")
        return DEFAULT_SETTINGS

def save_settings(new_settings):
    """[VAULT SEALING]: Commits new settings to the persistent backend storage."""
    path = get_settings_path()
    with SETTINGS_LOCK:
        try:
            current = load_settings()
            validated = _validate_settings(new_settings)
            for key in validated:
                if isinstance(validated[key], dict) and key in current:
                    current[key].update(validated[key])
                else:
                    current[key] = validated[key]

            with open(path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)

            backup_path = path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)

            return True
        except Exception as e:
            print(f"SETTINGS ERROR: Failed to seal vault: {e}")
            return False

def get_api_key(provider):
    """Retrieves a specific API key from the vault or environment fallback."""
    settings = load_settings()
    key = settings.get("api_keys", {}).get(provider.lower())
    
    # Fallback to .env if the vault is empty for this provider
    if not key:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        key = os.getenv(env_map.get(provider.lower(), ""))
        
    return key or ""
