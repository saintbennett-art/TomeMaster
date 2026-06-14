import os
import json
import time
import threading

from . import providers

# [SOVEREIGN SETTINGS]: All persistent configuration is now routed through
# the hardware-encrypted vault (src/tomemaster/vault_loader.py -> settings.enc).
# The legacy plaintext settings.json has been permanently retired.
SETTINGS_LOCK = threading.Lock()

# Default empty schema for the TomeMaster Vault
DEFAULT_SETTINGS = {
    "api_keys": {
        "openai": "", "gemini": "", "groq": "", "anthropic": "",
        "bitnet": "",
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
    # sovereign_lock=True → force LOCAL engines for every role, ignoring cloud
    # keys ("Think Sovereign in all cases"). The UI asks before any cloud fallback.
    "preferences": {"theme": "dark", "auto_stitch": True, "language": "en", "pii_scrub": False, "sovereign_lock": False},
    # User-defined OpenAI-compatible endpoints (exotic cloud or non-default local).
    # Each entry: {"label": str, "base_url": str, "key": str}. Self-service — lets
    # the user reach any provider with zero developer involvement.
    "custom_providers": [],
}



_PERMITTED_TOP_KEYS = set(DEFAULT_SETTINGS.keys())
_PERMITTED_API_KEYS = {"openai", "gemini", "groq", "anthropic", "bitnet", "slot_primary", "slot_specialist", "slot_velocity"}
_PERMITTED_MODEL_KEYS = {"vision", "logic", "analysis", "NARRATIVE_ARCHITECT", "COPY_EDITOR", "TRANSCRIBER_LEAD", "MARKETING_ANALYST", "SOVEREIGN_LIAISON"}
_PERMITTED_PREF_KEYS = {"theme", "auto_stitch", "language", "pii_scrub", "sovereign_lock"}


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
        elif key == "custom_providers":
            # Keep only well-formed {label, base_url, key} entries.
            entries = data[key] if isinstance(data[key], list) else []
            clean[key] = [
                {
                    "label":    str(e.get("label", "")).strip(),
                    "base_url": str(e.get("base_url", "")).strip(),
                    "key":      str(e.get("key", "")),
                }
                for e in entries
                if isinstance(e, dict) and str(e.get("base_url", "")).strip()
            ]
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

    # [BITNET]: No API key needed — local CPU inference. Return a sentinel
    # so the gateway dispatch treats it as "established."
    if provider.lower() == "bitnet":
        return key or "local-bitnet-cpu"

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


def detect_provider_from_key(key: str):
    """[KEY FORENSICS]: Infer the provider brand from an API key's format.

    Thin re-export of the single source of truth in `providers` so every call
    site shares one prefix table (sk-ant-/sk-or- tested before bare sk-).
    """
    return providers.detect_provider_from_key(key)


# ─── Dynamic Model Resolution Engine ─────────────────────────────────────────
# When preferred_models has "auto", the engine queries the provider's live model
# list and ranks candidates by role. This ensures the app never hardcodes model
# names — it adapts to whatever the user's API key has access to.

# [CACHE]: Avoid hammering the model list API on every request. Keyed PER
# PROVIDER so a multi-provider resolution (gemini + groq + …) doesn't evict
# itself on every call. Refresh every 5 minutes or when keys change.
_MODEL_CACHE = {}  # provider -> {"models": [...], "timestamp": float}
_MODEL_CACHE_TTL = 300  # seconds

# [SINGLE SOURCE OF TRUTH]: Anthropic portfolio fallback. Anthropic *does* expose
# GET /v1/models (x-api-key + anthropic-version headers); this static list is only
# used when that endpoint is unreachable. Referenced by every discovery path so
# the three call sites can never drift apart again.
ANTHROPIC_STATIC_PORTFOLIO = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-3-5-sonnet-20241022",
]

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
        "claude-opus-4-8", "claude-sonnet-4-6", "claude-3-5-sonnet-20241022",
    ],
    "COPY_EDITOR": [
        # Grammar, spelling, style — needs precision and linguistic fidelity
        "gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3.5-flash",
        "gemini-2.5-pro", "gemini-3-flash-preview",
        # Anthropic (excellent at editing)
        "claude-sonnet-4-6", "claude-opus-4-8", "claude-3-5-sonnet-20241022",
        # OpenAI
        "gpt-4o", "gpt-4o-mini",
    ],
    "MARKETING_ANALYST": [
        # Creative + fast: blurbs, genre analysis, marketing copy
        "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.1-pro-preview",
        "gemini-2.5-flash", "gemini-2.5-pro",
        "gpt-4o", "gpt-4o-mini",
        "claude-sonnet-4-6",
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

    # Check cache first (per-provider)
    now = time.time()
    cached = _MODEL_CACHE.get(provider)
    if cached and cached["models"] and now - cached["timestamp"] < _MODEL_CACHE_TTL:
        return cached["models"]

    urls = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models?key=",
        "openai": "https://api.openai.com/v1/models",
        "groq": "https://api.groq.com/openai/v1/models",
    }

    try:
        import urllib.request, json as _json

        # [BITNET]: Local CPU inference — no API key needed, just a running server
        if provider == "bitnet":
            bitnet_host = os.getenv("BITNET_HOST", "http://localhost:8080")
            req = urllib.request.Request(f"{bitnet_host}/v1/models")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
            models = [m["id"] for m in data.get("data", [])]
            _MODEL_CACHE[provider] = {"models": models, "timestamp": time.time()}
            print(f"[MODEL DISCOVERY]: bitnet → {len(models)} model(s) available")
            return models

        # [ANTHROPIC]: Real GET /v1/models (x-api-key + version headers). Falls
        # back to the static portfolio in the except block if unreachable.
        if provider == "anthropic":
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = _json.loads(resp.read())
            models = [m["id"] for m in data.get("data", []) if m.get("id")]
            models = models or list(ANTHROPIC_STATIC_PORTFOLIO)
            _MODEL_CACHE[provider] = {"models": models, "timestamp": now}
            print(f"[MODEL DISCOVERY]: anthropic → {len(models)} model(s) available")
            return models

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

        _MODEL_CACHE[provider] = {"models": models, "timestamp": now}
        print(f"[MODEL DISCOVERY]: {provider} → {len(models)} model(s) available")
        return models
    except Exception as e:
        print(f"[MODEL DISCOVERY WARNING]: Failed to query {provider}: {e}")
        # [ANTHROPIC FALLBACK]: no public-key-free endpoint guarantee — serve the
        # static portfolio so role resolution still works when the key is valid
        # but the /models probe failed (network blip, header quirk).
        if provider == "anthropic":
            return list(ANTHROPIC_STATIC_PORTFOLIO)
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
    for prov in ["gemini", "openai", "anthropic", "groq", "bitnet"]:
        key = api_keys.get(prov, "")
        if key and len(key) > 5:
            providers_with_keys.append((prov, key))

    if not providers_with_keys:
        return None

    ranking = _ROLE_RANKING.get(role_or_category, _ROLE_RANKING.get("SOVEREIGN_LIAISON", []))
    if not ranking:
        ranking = _ROLE_RANKING.get("SOVEREIGN_LIAISON", [])

    # Collect all available models across all providers with keys. Discovery is
    # unified — _fetch_model_list_sync handles every provider (incl. anthropic),
    # so there is no per-provider special-casing here anymore.
    all_available = set()
    for prov, key in providers_with_keys:
        all_available.update(_fetch_model_list_sync(prov, key))

    if not all_available:
        return None

    # [MODALITY GATE]: Hard-filter to models that support the modality this role
    # requires (e.g. an OCR role keeps only vision-capable models). Capability,
    # not a name list, decides eligibility. Cloud models infer modality by rule.
    req_mod = providers.required_modality(role_or_category)
    eligible = {m for m in all_available if providers.model_supports(m, req_mod)}
    if not eligible:
        return None
    all_available = eligible

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
    global _MODEL_CACHE, _LOCAL_PROBE_CACHE
    _MODEL_CACHE = {}
    _LOCAL_PROBE_CACHE = {"engines": None, "timestamp": 0}


# Cached localhost probe so resolving 5 roles doesn't re-scan ports 5×.
_LOCAL_PROBE_CACHE = {"engines": None, "timestamp": 0}


def _fetch_models_for_url(base_url: str, api_key: str = "") -> list:
    """[GENERIC DISCOVERY]: Sync /models fetch for an arbitrary OpenAI-compatible
    base URL (custom exotic cloud or non-default local). Cached per URL."""
    import urllib.request
    import json as _json

    now = time.time()
    cached = _MODEL_CACHE.get(base_url)
    if cached and cached["models"] and now - cached["timestamp"] < _MODEL_CACHE_TTL:
        return cached["models"]
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        req = urllib.request.Request(base_url.rstrip("/") + "/models", headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = _json.loads(resp.read())
        raw = data.get("data") or data.get("models") or []
        models = [m.get("id") or m.get("name") for m in raw if isinstance(m, dict)]
        models = [m for m in models if m]
        _MODEL_CACHE[base_url] = {"models": models, "timestamp": now}
        return models
    except Exception as e:
        print(f"[CUSTOM DISCOVERY WARNING]: {base_url}: {e}")
        return []


def _resolve_local_or_custom_endpoint(settings: dict, required_modality: str = "text"):
    """[SOVEREIGN-LOCAL]: When no cloud key is present, route a role to a user
    custom endpoint or a running local engine (Ollama/BitNet/…) so analysis works
    fully offline. The model is chosen by MODALITY — a vision role (OCR) will skip
    text-only local models and pick one that can actually see. Returns a gateway
    config or None when no local model satisfies the required modality.
    """
    # 1. user-defined custom endpoints (explicit > implicit)
    for cp in settings.get("custom_providers", []) or []:
        base = (cp.get("base_url") or "").strip()
        if not base:
            continue
        for mdl in _fetch_models_for_url(base, cp.get("key", "")):
            if providers.model_supports(mdl, required_modality, base):
                return {"url": providers._norm(base), "key": cp.get("key", ""),
                        "model": mdl, "provider": "custom"}

    # 2. auto-detected local engines (cached probe)
    global _LOCAL_PROBE_CACHE
    now = time.time()
    if _LOCAL_PROBE_CACHE["engines"] is None or now - _LOCAL_PROBE_CACHE["timestamp"] > _MODEL_CACHE_TTL:
        _LOCAL_PROBE_CACHE = {"engines": providers.probe_local_engines(), "timestamp": now}
    for eng in _LOCAL_PROBE_CACHE["engines"]:
        for mdl in eng.get("models", []):
            if providers.model_supports(mdl, required_modality, eng["base"]):
                return {"url": providers._norm(eng["base"]), "key": "",
                        "model": mdl, "provider": "local"}
    return None


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
    # [BITNET]: 1.58-bit local CPU models (BitNet b1.58, Falcon-E, etc.)
    if "bitnet" in m or "1.58bit" in m or "1_58" in m:
        return "bitnet"
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

    # 0. [SOVEREIGN LOCK]: force LOCAL resolution, ignoring cloud keys entirely.
    # If no local engine can serve the role's modality, return a 'sovereign_blocked'
    # marker — the gateway raises an honest error and the UI asks before any cloud
    # use. An explicit per-call override (user-confirmed cloud) still wins downstream.
    if settings.get("preferences", {}).get("sovereign_lock"):
        req_mod = providers.required_modality(role)
        local = _resolve_local_or_custom_endpoint(settings, req_mod)
        if local:
            return local
        return {"url": "", "key": "", "model": "", "provider": "sovereign_blocked", "modality": req_mod}

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

    # 3b. [SOVEREIGN-LOCAL FALLBACK]: the resolved cloud provider has no key —
    # route to a user custom endpoint or a running local engine if one exists,
    # so a keyless local model can drive analysis instead of guaranteeing a 401.
    if not key and provider != "bitnet":
        local = _resolve_local_or_custom_endpoint(settings, providers.required_modality(role))
        if local:
            return local

    # 4. Construct gateway config. URL comes from the single provider registry
    # so the dispatcher stays brand-agnostic and endpoints live in one place.
    url = providers.provider_base(provider) or providers.provider_base("gemini")

    return {
        "url":      url,
        "key":      key,
        "model":    model,
        "provider": provider,
    }
