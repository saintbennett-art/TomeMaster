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
