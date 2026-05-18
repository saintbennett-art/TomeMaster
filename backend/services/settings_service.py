import os
import json
import threading

# [SOVEREIGN SETTINGS]: Standard filename for persistent application configuration
SETTINGS_FILE = "settings.json"
SETTINGS_LOCK = threading.Lock()

# Default empty schema for the TomeMaster Vault
DEFAULT_SETTINGS = {
    "api_keys": {
        "openai": "", "gemini": "", "groq": "", "anthropic": "",
        "slot_primary": "", "slot_specialist": "", "slot_velocity": ""
    },
    "preferred_models": {
        "vision": "gemini-3-flash-preview",
        "logic": "gemini-3-flash-preview",
        "analysis": "gemini-3.1-pro-preview",
        "NARRATIVE_ARCHITECT": "gemini-3.1-pro-preview",
        "COPY_EDITOR": "claude-3-5-sonnet-20241022",
        "TRANSCRIBER_LEAD": "gemini-3-flash-preview",
    },
    "preferences": {"theme": "dark", "auto_stitch": True, "language": "en", "pii_scrub": False},
}


def get_settings_path():
    """Returns the absolute path to the settings vault in the backend root."""
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(backend_root, SETTINGS_FILE)


_PERMITTED_TOP_KEYS = set(DEFAULT_SETTINGS.keys())
_PERMITTED_API_KEYS = {"openai", "gemini", "groq", "anthropic", "slot_primary", "slot_specialist", "slot_velocity"}
_PERMITTED_MODEL_KEYS = {"vision", "logic", "analysis", "NARRATIVE_ARCHITECT", "COPY_EDITOR", "TRANSCRIBER_LEAD"}
_PERMITTED_PREF_KEYS = {"theme", "auto_stitch", "language", "pii_scrub"}


def _validate_settings(data: dict) -> dict:
    """Returns a copy of data with only permitted keys — drops unknown fields."""
    clean = {}
    for key in _PERMITTED_TOP_KEYS:
        if key not in data:
            continue
        if key == "api_keys":
            clean[key] = {
                k: str(v) for k, v in data[key].items() if k in _PERMITTED_API_KEYS
            }
        elif key == "preferred_models":
            clean[key] = {
                k: str(v) for k, v in data[key].items() if k in _PERMITTED_MODEL_KEYS
            }
        elif key == "preferences":
            clean[key] = {
                k: data[key][k] for k in _PERMITTED_PREF_KEYS if k in data[key]
            }
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

    # [UPGRADE]: Map slots to branded fallbacks if slot-specific key is missing
    if not key:
        slot_map = {
            "slot_primary": "gemini",
            "slot_specialist": "openai",
            "slot_velocity": "groq"
        }
        fallback_provider = slot_map.get(provider.lower())
        if fallback_provider:
            key = settings.get("api_keys", {}).get(fallback_provider)

    # Fallback to .env
    if not key:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "slot_primary": "GEMINI_API_KEY",
            "slot_specialist": "OPENAI_API_KEY",
            "slot_velocity": "GROQ_API_KEY"
        }
        key = os.getenv(env_map.get(provider.lower(), ""))

    return key or ""


def get_preferred_model(category: str, provider: str = None):
    """[SOVEREIGN DISCOVERY]: Returns the user's preferred model for a given category (vision, logic, analysis)."""
    settings = load_settings()
    models = settings.get("preferred_models", {})

    # If a specific provider is requested, we try to find a match, otherwise return the category default
    model = models.get(category.lower())

    # Fallback logic if the vault is corrupted or missing specific keys
    if not model:
        fallbacks = {
            "vision": "gemini-3-flash-preview",
            "logic": "gemini-3-flash-preview",
            "analysis": "gemini-3.1-pro-preview",
        }
        model = fallbacks.get(category.lower(), "gemini-3-flash-preview")

    return model


def _infer_provider_from_model(model: str) -> str:
    """[ROUTING HEURISTIC]: Maps a model id to its provider brand.

    Ordering matters — Groq's llama/mixtral/gemma families are checked
    explicitly so they don't fall through to the gemini default.
    """
    if not model:
        return "gemini"
    m = model.lower()
    if "gpt" in m or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if "claude" in m:
        return "anthropic"
    # Groq portfolio: llama-*, mixtral-*, gemma-*, meta-llama/*, etc.
    if "llama" in m or "mixtral" in m or m.startswith("gemma") or "meta-llama" in m:
        return "groq"
    if "gemini" in m:
        return "gemini"
    return "gemini"


def get_model_for_role(role: str) -> dict:
    """[SOVEREIGN MAPPING]: Maps an industrial role to its commissioned model and gateway key."""
    settings = load_settings()

    # 1. Map role to category. NARRATIVE_ARCHITECT is the structural editor —
    # it needs the analysis (Gemini 3.1 Pro) tier, not vision. Vision is for
    # OCR/transcription only.
    category_map = {
        "NARRATIVE_ARCHITECT": "analysis",
        "COPY_EDITOR":         "analysis",
        "MARKETING_ANALYST":   "logic",
        "SOVEREIGN_LIAISON":   "logic",
        "TRANSCRIBER_LEAD":    "vision",   # Vision required for manuscript OCR
        "OCR_ENGINE":          "vision",
        "Editor-in-Chief":     "analysis",
        "Sovereign Liaison":   "logic",
    }

    category = category_map.get(role, "logic")

    # 2. Prefer the user's explicit role-level pinning if set; otherwise category default.
    models_pref = settings.get("preferred_models", {})
    model = models_pref.get(role) or get_preferred_model(category)

    # 3. Determine provider from the model id (handles Groq llama/mixtral/gemma).
    provider = _infer_provider_from_model(model)
    key = get_api_key(provider)

    # 4. Construct gateway config. URL is derived from the provider so the
    # dispatcher stays brand-agnostic.
    urls = {
        "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai/",
        "openai":    "https://api.openai.com/v1/",
        "anthropic": "https://api.anthropic.com/v1/",  # adapter switches to /messages
        "groq":      "https://api.groq.com/openai/v1/",
    }

    return {
        "url":      urls.get(provider, urls["gemini"]),
        "key":      key,
        "model":    model,
        "provider": provider,
    }
