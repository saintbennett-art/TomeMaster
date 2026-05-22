import os
import json
import threading

# [SOVEREIGN SETTINGS]: All persistent configuration is now routed through
# the hardware-encrypted vault (src/tomemaster/vault_loader.py -> settings.enc).
# The legacy plaintext settings.json has been permanently retired.
SETTINGS_LOCK = threading.Lock()

# Default empty schema for the TomeMaster Vault
DEFAULT_SETTINGS = {
    "api_keys": {
        "openai": "", "gemini": "", "groq": "", "anthropic": "",
        "slot_primary": "", "slot_specialist": "", "slot_velocity": ""
    },
    "preferred_models": {
        # "auto" means: query the live model list from the API key and pick
        # the best model for each role dynamically. No hardcoded model names.
        "vision": "auto",
        "logic": "auto",
        "analysis": "auto",
        "NARRATIVE_ARCHITECT": "auto",
        "COPY_EDITOR": "auto",
        "TRANSCRIBER_LEAD": "auto",
        "MARKETING_ANALYST": "auto",
        "SOVEREIGN_LIAISON": "auto",
    },
    "preferences": {"theme": "dark", "auto_stitch": True, "language": "en", "pii_scrub": False},
}



_PERMITTED_TOP_KEYS = set(DEFAULT_SETTINGS.keys())
_PERMITTED_API_KEYS = {"openai", "gemini", "groq", "anthropic", "slot_primary", "slot_specialist", "slot_velocity"}
_PERMITTED_MODEL_KEYS = {"vision", "logic", "analysis", "NARRATIVE_ARCHITECT", "COPY_EDITOR", "TRANSCRIBER_LEAD", "MARKETING_ANALYST", "SOVEREIGN_LIAISON"}
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
    """[VAULT HYDRATION]: Recovers settings securely from the hardware-locked vault."""
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    try:
        from src.tomemaster.vault_loader import load_vault
        raw = load_vault()
        if not raw:
            return DEFAULT_SETTINGS
        return _validate_settings(raw)
    except Exception as e:
        print(f"SETTINGS ERROR: Failed to hydrate from secure vault: {e}")
        return DEFAULT_SETTINGS


def save_settings(new_settings):
    """[VAULT SEALING]: Encrypts and commits new settings to the hardware-locked storage."""
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    try:
        from src.tomemaster.vault_loader import save_vault
        with SETTINGS_LOCK:
            current = load_settings()
            validated = _validate_settings(new_settings)
            for key in validated:
                if isinstance(validated[key], dict) and key in current:
                    current[key].update(validated[key])
                else:
                    current[key] = validated[key]

            save_vault(current)

            # [CACHE BUST]: If API keys changed, force model re-discovery
            if "api_keys" in validated:
                invalidate_model_cache()

            return True
    except Exception as e:
        print(f"SETTINGS ERROR: Failed to seal secure vault: {e}")
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


# ─── Dynamic Model Resolution Engine ─────────────────────────────────────────
# When preferred_models has "auto", the engine queries the provider's live model
# list and ranks candidates by role. This ensures the app never hardcodes model
# names — it adapts to whatever the user's API key has access to.

# [CACHE]: Avoid hammering the model list API on every request. Refresh every
# 5 minutes or when keys change.
_MODEL_CACHE = {"models": [], "provider": None, "timestamp": 0}
_MODEL_CACHE_TTL = 300  # seconds

# [RANKING TABLE]: Priority order per role. First match wins.
# Higher-versioned models rank first; "pro" models for reasoning,
# "flash" for speed/vision. Works across Gemini, OpenAI, Anthropic, Groq.
_ROLE_RANKING = {
    "TRANSCRIBER_LEAD": [
        # Vision/OCR: needs multimodal. Flash models are fastest + cheapest per page.
        "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash",
        "gemini-3.1-flash-lite", "gemini-2.0-flash",
        # OpenAI vision fallback
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        # Groq vision
        "llama-3.2-90b-vision", "llama-3.2-11b-vision",
    ],
    "NARRATIVE_ARCHITECT": [
        # Deep reasoning for chapterization + structural analysis
        "gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-2.5-pro",
        "gemini-3.5-flash", "gemini-3-flash-preview",
        # OpenAI reasoning
        "gpt-4o", "o3", "o1",
        # Anthropic
        "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
    ],
    "COPY_EDITOR": [
        # Grammar, spelling, style — needs precision and linguistic fidelity
        "gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3.5-flash",
        "gemini-2.5-pro", "gemini-3-flash-preview",
        # Anthropic (excellent at editing)
        "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
        # OpenAI
        "gpt-4o", "gpt-4o-mini",
    ],
    "MARKETING_ANALYST": [
        # Creative + fast: blurbs, genre analysis, marketing copy
        "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.1-pro-preview",
        "gemini-2.5-flash", "gemini-2.5-pro",
        "gpt-4o", "gpt-4o-mini",
        "claude-sonnet-4-20250514",
    ],
    "SOVEREIGN_LIAISON": [
        # General coordination — fast model
        "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash",
        "gemini-2.0-flash", "gpt-4o-mini",
    ],
    # Category aliases
    "vision": None,   # → same as TRANSCRIBER_LEAD
    "analysis": None,  # → same as NARRATIVE_ARCHITECT
    "logic": None,     # → same as SOVEREIGN_LIAISON
}
_ROLE_RANKING["vision"] = _ROLE_RANKING["TRANSCRIBER_LEAD"]
_ROLE_RANKING["analysis"] = _ROLE_RANKING["NARRATIVE_ARCHITECT"]
_ROLE_RANKING["logic"] = _ROLE_RANKING["SOVEREIGN_LIAISON"]


def _fetch_model_list_sync(provider: str, api_key: str) -> list:
    """[DISCOVERY PULSE]: Queries the provider's /models endpoint synchronously.
    Returns a list of model ID strings, or [] on failure."""
    import time
    global _MODEL_CACHE

    # Check cache first
    now = time.time()
    if (_MODEL_CACHE["provider"] == provider and
            _MODEL_CACHE["models"] and
            now - _MODEL_CACHE["timestamp"] < _MODEL_CACHE_TTL):
        return _MODEL_CACHE["models"]

    urls = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models?key=",
        "openai": "https://api.openai.com/v1/models",
        "groq": "https://api.groq.com/openai/v1/models",
    }

    try:
        import urllib.request, json as _json
        if provider == "gemini":
            url = urls["gemini"] + api_key
            req = urllib.request.Request(url)
        elif provider in urls:
            url = urls[provider]
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        else:
            return []

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read())

        models = []
        if "models" in data:
            # Gemini native format: {"models": [{"name": "models/gemini-3-flash-preview", ...}]}
            for m in data["models"]:
                name = m.get("name", "")
                # Strip "models/" prefix
                if name.startswith("models/"):
                    name = name[len("models/"):]
                # Only include text-generation models (skip embedding, imagen, veo, lyria, etc.)
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    models.append(name)
        elif "data" in data:
            # OpenAI/Groq format: {"data": [{"id": "gpt-4o", ...}]}
            models = [m["id"] for m in data["data"]]

        _MODEL_CACHE = {"models": models, "provider": provider, "timestamp": now}
        print(f"[MODEL DISCOVERY]: {provider} → {len(models)} model(s) available")
        return models
    except Exception as e:
        print(f"[MODEL DISCOVERY WARNING]: Failed to query {provider}: {e}")
        return []


def _resolve_auto_model(role_or_category: str, settings: dict = None) -> str:
    """[DYNAMIC ROUTING]: Given a role name, queries the live model portfolio
    from the best available API key and returns the top-ranked model.

    The ranking table is role-specific. First match in the priority list wins.
    If no ranked model is found, returns the first generateContent-capable model.
    """
    if settings is None:
        settings = load_settings()

    api_keys = settings.get("api_keys", {})

    # Determine which providers have keys
    providers_with_keys = []
    for prov in ["gemini", "openai", "anthropic", "groq"]:
        key = api_keys.get(prov, "")
        if key and len(key) > 5:
            providers_with_keys.append((prov, key))

    if not providers_with_keys:
        return None

    ranking = _ROLE_RANKING.get(role_or_category, _ROLE_RANKING.get("SOVEREIGN_LIAISON", []))
    if not ranking:
        ranking = _ROLE_RANKING.get("SOVEREIGN_LIAISON", [])

    # Collect all available models across all providers with keys
    all_available = set()
    for prov, key in providers_with_keys:
        if prov == "anthropic":
            # Anthropic has no public /models endpoint — use static portfolio
            all_available.update([
                "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-latest", "claude-3-opus-20240229",
            ])
        else:
            models = _fetch_model_list_sync(prov, key)
            all_available.update(models)

    if not all_available:
        return None

    # [PRIORITY MATCH]: Walk the ranking list; first hit wins
    for candidate in ranking:
        if candidate in all_available:
            return candidate

    # [FUZZY FALLBACK]: If no exact match, try substring matching
    # (handles cases like "gemini-3.5-flash-001" matching "gemini-3.5-flash")
    for candidate in ranking:
        for available in all_available:
            if candidate in available or available.startswith(candidate):
                return available

    # [LAST RESORT]: Return the first available text model
    return next(iter(all_available), None)


def invalidate_model_cache():
    """Call when API keys change so the next model resolution re-queries."""
    global _MODEL_CACHE
    _MODEL_CACHE = {"models": [], "provider": None, "timestamp": 0}


def get_preferred_model(category: str, provider: str = None):
    """[SOVEREIGN DISCOVERY]: Returns the user's preferred model for a given category (vision, logic, analysis).
    
    If the stored value is "auto", delegates to the dynamic model resolver which
    queries the live API key portfolio and picks the best model for the role.
    """
    settings = load_settings()
    models = settings.get("preferred_models", {})
    model = models.get(category.lower()) or models.get(category)  # try both cases

    if model and model != "auto":
        return model

    # [DYNAMIC ROUTING]: "auto" or missing — resolve from live portfolio
    resolved = _resolve_auto_model(category, settings)
    if resolved:
        return resolved

    # [LAST RESORT]: If no API key is configured at all, return a safe default
    # so the app doesn't crash before the user enters keys.
    fallbacks = {
        "vision": "gemini-2.5-flash",
        "logic": "gemini-2.5-flash",
        "analysis": "gemini-2.5-pro",
        "TRANSCRIBER_LEAD": "gemini-2.5-flash",
        "NARRATIVE_ARCHITECT": "gemini-2.5-pro",
        "COPY_EDITOR": "gemini-2.5-pro",
        "MARKETING_ANALYST": "gemini-2.5-flash",
        "SOVEREIGN_LIAISON": "gemini-2.5-flash",
    }
    return fallbacks.get(category, fallbacks.get(category.lower(), "gemini-2.5-flash"))


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
    """[SOVEREIGN MAPPING]: Maps an industrial role to its commissioned model and gateway key.
    
    Model resolution is fully dynamic — "auto" in preferred_models triggers a
    live query of the API key's portfolio and ranks candidates by role.
    Explicit model pinning (user chose a specific model in Settings) is honored.
    """
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

    # 2. Prefer the user's explicit role-level pinning if set and not "auto";
    #    otherwise resolve dynamically.
    models_pref = settings.get("preferred_models", {})
    pinned = models_pref.get(role)
    if pinned and pinned != "auto":
        model = pinned
    else:
        model = get_preferred_model(role) or get_preferred_model(category)

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
