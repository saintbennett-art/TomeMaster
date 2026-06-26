"""[SINGLE SOURCE OF TRUTH]: AI provider connection metadata + the endpoint
resolution ladder.

Design law: *everything is an OpenAI-compatible endpoint + an optional key.*
The only thing that varies is HOW the app learns the endpoint. Model NAMES never
live here — they are always discovered live from ``<base>/models`` so nothing in
this file goes stale when models change.

The ladder (see ``resolve_endpoint``):
  1. explicit base_url        → exotic cloud / custom / non-default local (ALWAYS wins)
  2. brand-name seed          → popular OpenAI-compatible exotics (Kimi, DeepSeek…)
  3. explicit provider        → dropdown pick of a known brand
  4. key-prefix auto-detect   → the default guess for a pasted key

Zero forced developer maintenance: every rung degrades to user self-service, so a
brand-new or never-seen provider is reachable via the base-URL path with no release.
The known-brand table below is a *convenience accelerator*, not a dependency.
"""
import os

# ─── Auth styles ─────────────────────────────────────────────────────────────
BEARER = "bearer"        # Authorization: Bearer <key>   (OpenAI, Groq, Gemini-compat, xAI…)
X_API_KEY = "x-api-key"  # Anthropic messages API


def bitnet_host() -> str:
    return os.getenv("BITNET_HOST", "http://localhost:8080")


# ─── Known-brand registry (the only place these constants live) ──────────────
# `base` is the OpenAI-compatible chat base (string-identical to the historical
# scattered tables — guarded by pin tests). `messages_adapter` flags the one
# brand (Anthropic) that needs the /messages adapter instead of /chat/completions.
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "auth": BEARER,
        "key_prefixes": ("AIza",),
        "env_var": "GEMINI_API_KEY",
        "messages_adapter": False,
    },
    "openai": {
        "label": "OpenAI",
        "base": "https://api.openai.com/v1/",
        "auth": BEARER,
        "key_prefixes": ("sk-",),
        "env_var": "OPENAI_API_KEY",
        "messages_adapter": False,
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "base": "https://api.anthropic.com/v1/",
        "auth": X_API_KEY,
        "key_prefixes": ("sk-ant-",),
        "env_var": "ANTHROPIC_API_KEY",
        "messages_adapter": True,
    },
    "groq": {
        "label": "Groq",
        "base": "https://api.groq.com/openai/v1/",
        "auth": BEARER,
        "key_prefixes": ("gsk_",),
        "env_var": "GROQ_API_KEY",
        "messages_adapter": False,
    },
    "xai": {
        "label": "xAI Grok",
        "base": "https://api.x.ai/v1/",
        "auth": BEARER,
        "key_prefixes": ("xai-",),
        "env_var": "XAI_API_KEY",
        "messages_adapter": False,
    },
    "openrouter": {
        "label": "OpenRouter",
        "base": "https://openrouter.ai/api/v1/",
        "auth": BEARER,
        "key_prefixes": ("sk-or-",),
        "env_var": "OPENROUTER_API_KEY",
        "messages_adapter": False,
    },
}

# Most-specific prefix first, so 'sk-ant-' and 'sk-or-' win over bare 'sk-'.
_DETECT_ORDER = ("anthropic", "openrouter", "gemini", "groq", "xai", "openai")

# Local engines: well-known localhost defaults — keyless, OpenAI-compatible.
# Probing these is safe (localhost, no key leaves the box, instant).
LOCAL_ENGINES = (
    {"name": "ollama",   "base": "http://localhost:11434/v1/"},
    {"name": "lmstudio", "base": "http://localhost:1234/v1/"},
    {"name": "vllm",     "base": "http://localhost:8000/v1/"},
    {"name": "llamacpp", "base": "http://localhost:8080/v1/"},  # llama.cpp / bitnet.cpp default
)

# Optional convenience seeds: popular OpenAI-compatible exotics → base URL.
# ADDITIVE ONLY. If a seed goes stale the user just types the URL — never
# load-bearing, so this never becomes forced maintenance.
OPENAI_COMPATIBLE_SEEDS = {
    "kimi":       "https://api.moonshot.cn/v1/",
    "moonshot":   "https://api.moonshot.cn/v1/",
    "deepseek":   "https://api.deepseek.com/v1/",
    "together":   "https://api.together.xyz/v1/",
    "fireworks":  "https://api.fireworks.ai/inference/v1/",
    "mistral":    "https://api.mistral.ai/v1/",
    "perplexity": "https://api.perplexity.ai/",
}


def _norm(url: str) -> str:
    """Trailing-slash normalize so callers can safely append paths."""
    url = (url or "").strip()
    return url if url.endswith("/") else url + "/"


def provider_base(provider: str):
    """Chat/discovery base URL for a known provider (bitnet resolves live)."""
    if provider == "bitnet":
        return f"{bitnet_host()}/v1/"
    p = PROVIDERS.get(provider)
    return p["base"] if p else None


def provider_auth(provider: str) -> str:
    return PROVIDERS.get(provider, {}).get("auth", BEARER)


def detect_provider_from_key(key: str):
    """Infer the provider brand from an API key's prefix. Returns a provider
    name or None.

    NOTE: a bare ``sk-`` defaults to ``openai`` (the common case), but an
    explicit ``base_url`` ALWAYS overrides this in ``resolve_endpoint`` — so an
    OpenAI-format clone (Kimi/DeepSeek) plus its URL routes to the right server.
    """
    if not key:
        return None
    k = key.strip()
    for name in _DETECT_ORDER:
        for prefix in PROVIDERS[name]["key_prefixes"]:
            if k.startswith(prefix):
                return name
    return None


def seed_lookup(brand: str):
    """Resolve a popular exotic brand name → base URL (convenience only)."""
    if not brand:
        return None
    return OPENAI_COMPATIBLE_SEEDS.get(brand.strip().lower())


def resolve_endpoint(key: str = None, provider: str = None,
                     base_url: str = None, brand: str = None):
    """[THE LADDER]: Resolve where to send requests + how to authenticate.

    Returns a dict ``{provider, base, auth, key, source, messages_adapter}`` or
    None when nothing can be determined. Precedence is strict (1 wins over 4):

      1. explicit ``base_url``   — exotic/custom/local, ALWAYS wins over a prefix guess
      2. ``brand`` seed          — Kimi/DeepSeek/… name → URL
      3. explicit ``provider``   — dropdown pick of a known brand
      4. key-prefix detection    — default guess from a pasted key
    """
    # 1. explicit URL wins outright
    if base_url:
        prov = provider or detect_provider_from_key(key) or "openai-compatible"
        return {
            "provider": prov,
            "base": _norm(base_url),
            "auth": provider_auth(prov),
            "key": key or "",
            "source": "base_url",
            "messages_adapter": PROVIDERS.get(prov, {}).get("messages_adapter", False),
        }

    # 2. brand-name convenience seed
    seed = seed_lookup(brand)
    if seed:
        return {
            "provider": "openai-compatible",
            "base": _norm(seed),
            "auth": BEARER,
            "key": key or "",
            "source": "seed",
            "messages_adapter": False,
        }

    # 3/4. explicit provider, else key-prefix detection
    prov = provider or detect_provider_from_key(key)
    base = provider_base(prov) if prov else None
    if prov and base:
        return {
            "provider": prov,
            "base": base,
            "auth": provider_auth(prov),
            "key": key or "",
            "source": "provider" if provider else "prefix",
            "messages_adapter": PROVIDERS.get(prov, {}).get("messages_adapter", False),
        }
    return None


# ─── Modality (the selection axis — NO model-name preference lists) ───────────
# A model is chosen by whether it supports the MODALITY a role requires, not by
# a hand-curated ranked list of model names. Local engines REPORT their modality
# (authoritative); cloud APIs usually don't, so cloud falls back to a small set
# of general modality RULES (patterns, not versioned names).

# Role → required modality. Semantic + stable: it describes ROLES we own (OCR
# will always need to see an image), not models that churn. The only hand map.
ROLE_REQUIRED_MODALITY = {
    "TRANSCRIBER_LEAD": "image",
    "OCR_ENGINE":       "image",
    "vision":           "image",
}


def required_modality(role: str) -> str:
    """The modality a role's model MUST support. Defaults to 'text'."""
    return ROLE_REQUIRED_MODALITY.get(role, "text")


# General modality RULES — used ONLY where the engine/API doesn't report
# capabilities (cloud, non-Ollama). Broad patterns that survive new versions,
# not a list of specific model names.
_VISION_HINTS = (
    "vision", "-vl", "gpt-4o", "gpt-4.1", "o4-", "gemini", "claude-3", "claude-4",
    "claude-opus", "claude-sonnet", "llava", "moondream", "minicpm-v",
    "gemma3", "gemma4", "pixtral", "llama-3.2-11b", "llama-3.2-90b", "llama-4",
)
_TEXT_ONLY_HINTS = ("versatile", "instant", "-text", "embed", "whisper", "tts")


def infer_modalities(model_id: str) -> set:
    """Best-effort modality set from a model id, when nothing authoritative is
    available. Always includes 'text'; adds 'image' on a vision pattern."""
    m = (model_id or "").lower()
    if any(k in m for k in _TEXT_ONLY_HINTS):
        return {"text"}
    mods = {"text"}
    if any(h in m for h in _VISION_HINTS):
        mods.add("image")
    return mods


def ollama_capabilities(base: str, model_id: str, timeout: float = 2.0):
    """[AUTHORITATIVE]: Query Ollama's native /api/show for real capabilities.
    Returns a modality set, or None when unavailable (non-Ollama engine)."""
    import urllib.request
    import json as _json

    host = base.split("/v1")[0].rstrip("/")
    try:
        req = urllib.request.Request(
            host + "/api/show",
            data=_json.dumps({"model": model_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = _json.loads(resp.read())
        caps = [str(c).lower() for c in data.get("capabilities", [])]
        if not caps:
            return None
        mods = {"text"}
        if "vision" in caps:
            mods.add("image")
        if "audio" in caps:
            mods.add("audio")
        return mods
    except Exception:
        return None


def model_modalities(model_id: str, base: str = None) -> set:
    """Modalities a model supports: engine-reported (authoritative, local only)
    where possible, else inferred from general rules. /api/show is Ollama-native
    so it's only attempted for localhost bases."""
    if base and ("localhost" in base or "127.0.0.1" in base):
        reported = ollama_capabilities(base, model_id)
        if reported:
            return reported
    return infer_modalities(model_id)


def model_supports(model_id: str, modality: str, base: str = None) -> bool:
    return modality in model_modalities(model_id, base)


# ─── Primary trait (display label — pattern-based, NOT a model-name table) ─────
# A short, human label for "what this model is mainly for", inferred from broad id
# patterns that survive new versions (same philosophy as the modality rules). Used
# only for UI hinting, never for selection. Priority order is deliberate so a
# flagship reasoning/analysis model reads as such even though it's also multimodal:
# Thinking > Analysis > Fast > Visual > General. (e.g. o3-mini=Thinking, claude-opus=
# Analysis, gemini-flash=Fast, gpt-4o=Visual.)
_THINKING_HINTS = ("o1", "o3", "o4-", "-r1", "r1-", "reasoning", "think", "qwq", "deepseek-r")
_ANALYSIS_HINTS = ("pro", "opus", "-large", "405b", "70b", "72b", "65b", "ultra", "-max")
_FAST_HINTS = ("flash", "mini", "nano", "haiku", "instant", "lite", "-8b", "-7b", "small", "-fast")


def model_trait(model_id: str, base: str = None) -> str:
    """A short primary-trait label for the UI: Thinking / Analysis / Fast / Visual /
    General. Heuristic from id patterns; 'Visual' uses the authoritative modality."""
    m = (model_id or "").lower()
    if any(h in m for h in _THINKING_HINTS):
        return "Thinking"
    if any(h in m for h in _ANALYSIS_HINTS):
        return "Analysis"
    if any(h in m for h in _FAST_HINTS):
        return "Fast"
    if "image" in model_modalities(model_id, base):
        return "Visual"
    return "General"


# ─── Curation (chat-only, ranked best-first — pattern-based, no name tables) ───
import re as _re

# Non-text-generation families that should never appear in a chat/critique picker.
_NON_CHAT_HINTS = (
    "embed", "embedding", "whisper", "tts", "text-to-speech", "moderation", "guard",
    "rerank", "realtime", "audio", "transcribe", "dall-e", "dalle", "imagen",
    "image", "stable-diffusion", "diffusion", "sora", "clip", "-search",
    # media-generation / speech models that aren't text-chat (per-provider offenders)
    "lyria", "orpheus", "veo", "music", "speech", "voice", "playai", "canopy",
    # agentic / non-chat-completions models (don't return a standard message)
    "deep-research", "computer-use", "-tts", "gemma-3n-e2b-it-litert",
)


def is_chat_model(model_id: str) -> bool:
    """True for text-generation models suitable for analysis/critique; filters out
    embeddings, audio, image, moderation and other non-chat endpoints."""
    m = (model_id or "").lower()
    return not any(h in m for h in _NON_CHAT_HINTS)


def model_quality(model_id: str) -> int:
    """A coarse, pattern-based quality score so the BEST models sort first. Not a
    name table — broad family/tier patterns that survive new versions."""
    m = (model_id or "").lower()
    s = 0
    if any(h in m for h in ("o3", "o1", "-r1", "r1-", "reasoning", "qwq", "deepseek-r")):
        s += 60
    if any(h in m for h in ("opus", "ultra", "-max")):
        s += 55
    if "pro" in m:
        s += 50
    if any(h in m for h in ("sonnet", "405b", "-70b", "-72b", "gpt-4.5")):
        s += 35
    if any(h in m for h in ("gpt-4o", "gpt-4.1")):
        s += 30
    elif "gpt-4" in m:
        s += 22
    for ver, pts in (("4.5", 16), ("3.1", 16), ("4.1", 12), ("4o", 10), ("3.0", 12),
                     ("2.5", 12), ("2.0", 8), ("1.5", 4), ("3.5", -40)):
        if ver in m:
            s += pts
    if any(h in m for h in ("flash", "mini", "haiku", "instant", "lite", "nano", "-8b", "small")):
        s -= 6
    if any(h in m for h in ("0301", "0314", "0613", "davinci", "babbage", "curie", "-ada", "turbo-instruct")):
        s -= 50
    # Prefer the canonical undated id over a dated snapshot of the same family.
    if _re.search(r"\d{4}-\d{2}-\d{2}|-\d{6,8}$|-\d{3,4}$", m):
        s -= 8
    return s


def _family_key(model_id: str) -> str:
    """Collapse dated/numbered snapshots to their family so duplicates dedupe
    (e.g. gpt-4o-2024-05-13 and gpt-4o-2024-08-06 -> gpt-4o)."""
    m = (model_id or "").lower()
    m = _re.sub(r"[-_]\d{4}-\d{2}-\d{2}", "", m)        # -2024-05-13
    m = _re.sub(r"[-_]\d{6,8}", "", m)                   # -20241022
    for tok in ("preview", "customtools", "exp", "latest", "tuning"):
        m = m.replace("-" + tok, "").replace("_" + tok, "")
    m = _re.sub(r"[-_](001|002)$", "", m)
    return m


# ─── Self-service help links (turn a provider error into an actionable link) ──
_PROVIDER_HELP = {
    "anthropic": {"billing": "https://console.anthropic.com/settings/billing", "keys": "https://console.anthropic.com/settings/keys"},
    "openai":    {"billing": "https://platform.openai.com/account/billing/overview", "keys": "https://platform.openai.com/api-keys"},
    "gemini":    {"billing": "https://aistudio.google.com/app/billing", "keys": "https://aistudio.google.com/app/apikey"},
    "google":    {"billing": "https://aistudio.google.com/app/billing", "keys": "https://aistudio.google.com/app/apikey"},
    "groq":      {"billing": "https://console.groq.com/settings/billing", "keys": "https://console.groq.com/keys"},
    "xai":       {"billing": "https://console.x.ai", "keys": "https://console.x.ai"},
    "openrouter": {"billing": "https://openrouter.ai/credits", "keys": "https://openrouter.ai/keys"},
}


def provider_help_link(error_text: str, provider: str = None) -> str:
    """Given a provider error, return a markdown 'Action' link to the page that
    resolves it (billing for credit/quota issues, keys for auth issues). Returns ''
    when no provider can be inferred. The raw error is never hidden — this is appended."""
    text = (error_text or "").lower()
    prov = (provider or "").lower()
    if prov not in _PROVIDER_HELP:
        prov = next((p for p in _PROVIDER_HELP if p in text), "")
    if prov not in _PROVIDER_HELP:
        return ""

    if any(k in text for k in ("credit", "billing", "balance", "quota", "payment", "upgrade", "purchase", "insufficient")):
        kind, label = "billing", "billing & credits"
    elif any(k in text for k in ("rate limit", "429", "too many requests")):
        kind, label = "billing", "usage & limits"
    elif any(k in text for k in ("api key", "invalid", "unauthor", "401", "403", "authentication", "permission")):
        kind, label = "keys", "API keys"
    else:
        kind, label = "keys", "account"

    url = _PROVIDER_HELP[prov].get(kind) or _PROVIDER_HELP[prov].get("keys")
    return f"\n\n**Action:** [Open {prov.title()} {label}]({url})"


def curate_models(models: list) -> list:
    """Filter to chat models, dedupe snapshot families (keep the best representative),
    and sort best-first. Input/return: list of dicts with an 'id' key."""
    best = {}
    for m in models:
        mid = m.get("id", "")
        if not is_chat_model(mid):
            continue
        fam = _family_key(mid)
        if fam not in best or model_quality(mid) > model_quality(best[fam].get("id", "")):
            best[fam] = m
    return sorted(best.values(), key=lambda x: model_quality(x.get("id", "")), reverse=True)


def probe_local_engines(timeout: float = 0.4) -> list:
    """[LOCAL DISCOVERY]: Ping the known localhost engine ports and return those
    that answer ``/models``. Safe by construction — localhost only, keyless,
    sub-second. Returns ``[{name, base, models:[...]}, …]`` for live engines.
    """
    import urllib.request
    import json as _json

    found = []
    for eng in LOCAL_ENGINES:
        url = eng["base"].rstrip("/") + "/models"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = _json.loads(resp.read())
            raw = data.get("data") or data.get("models") or []
            models = [m.get("id") or m.get("name") for m in raw if isinstance(m, dict)]
            found.append({
                "name": eng["name"],
                "base": eng["base"],
                "models": [m for m in models if m],
            })
        except Exception:
            continue  # not running — silently skip
    return found
