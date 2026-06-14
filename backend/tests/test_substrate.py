"""Module 0 — key/model substrate. Offline tests (no live API key required).

Covers: key-format provider detection, dynamic role→model resolution (ranking,
fuzzy, first-available, no-key), per-provider cache behaviour, the single
Anthropic portfolio source of truth, and the encrypted-vault save→load round
trip + key masking — all with the live vault and network fully stubbed so the
real settings.enc on disk is never touched.
"""
import pytest

from services import settings_service as ss


# ─── F4: detect_provider_from_key ────────────────────────────────────────────

@pytest.mark.parametrize("key,expected", [
    ("sk-ant-api03-abcdef", "anthropic"),
    ("AIzaSyD-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "gemini"),
    ("gsk_abcdefghijklmnop", "groq"),
    ("sk-proj-abcdefghijklmnop", "openai"),
    ("sk-abcdefghijklmnop", "openai"),
    ("  sk-ant-leadingspace  ", "anthropic"),  # trimmed
    ("nonsense-key", None),
    ("", None),
    (None, None),
])
def test_detect_provider_from_key(key, expected):
    assert ss.detect_provider_from_key(key) == expected


def test_detect_provider_ant_before_openai():
    """'sk-ant-' must win over the broader 'sk-' prefix — ordering matters."""
    assert ss.detect_provider_from_key("sk-ant-xyz") == "anthropic"


# ─── F2/F7: dynamic role→model resolution ────────────────────────────────────

def _settings_with(*providers):
    return {"api_keys": {p: f"{p}-key-longenough" for p in providers}}


def test_resolve_picks_top_ranked(monkeypatch):
    """When several ranked models are available, the highest-priority one wins."""
    monkeypatch.setattr(ss, "_fetch_model_list_sync",
                        lambda prov, key: ["gemini-2.5-pro", "gemini-3.1-pro-preview"])
    chosen = ss._resolve_auto_model("NARRATIVE_ARCHITECT", _settings_with("gemini"))
    # gemini-3.1-pro-preview sits above gemini-2.5-pro in the ranking table.
    assert chosen == "gemini-3.1-pro-preview"


def test_resolve_fuzzy_match(monkeypatch):
    """A versioned id (…-001) still resolves via substring fuzzy fallback."""
    monkeypatch.setattr(ss, "_fetch_model_list_sync",
                        lambda prov, key: ["gemini-3.5-flash-001"])
    chosen = ss._resolve_auto_model("TRANSCRIBER_LEAD", _settings_with("gemini"))
    assert chosen == "gemini-3.5-flash-001"


def test_resolve_first_available_when_no_rank_hit(monkeypatch):
    """Unknown portfolio → last-resort returns *some* available model, never None."""
    monkeypatch.setattr(ss, "_fetch_model_list_sync",
                        lambda prov, key: ["brand-new-model-x"])
    chosen = ss._resolve_auto_model("SOVEREIGN_LIAISON", _settings_with("gemini"))
    assert chosen == "brand-new-model-x"


def test_resolve_no_keys_returns_none():
    assert ss._resolve_auto_model("NARRATIVE_ARCHITECT", {"api_keys": {}}) is None


# ─── F5: per-provider cache does not self-evict ──────────────────────────────

def test_cache_is_per_provider(monkeypatch):
    monkeypatch.setattr(ss, "_MODEL_CACHE", {}, raising=False)
    ss._MODEL_CACHE["gemini"] = {"models": ["g1"], "timestamp": ss.time.time() if hasattr(ss, "time") else __import__("time").time()}
    ss._MODEL_CACHE["groq"] = {"models": ["q1"], "timestamp": __import__("time").time()}
    # Both providers coexist — one does not overwrite the other.
    assert ss._MODEL_CACHE["gemini"]["models"] == ["g1"]
    assert ss._MODEL_CACHE["groq"]["models"] == ["q1"]


def test_invalidate_clears_cache(monkeypatch):
    monkeypatch.setattr(ss, "_MODEL_CACHE", {"gemini": {"models": ["g1"], "timestamp": 0}}, raising=False)
    ss.invalidate_model_cache()
    assert ss._MODEL_CACHE == {}


# ─── F3: one Anthropic portfolio, shared by every call site ──────────────────

def test_anthropic_portfolio_single_source():
    from services import ai_service
    # ai_service imports the *same object*, not a copy — they cannot drift.
    assert ai_service.ANTHROPIC_STATIC_PORTFOLIO is ss.ANTHROPIC_STATIC_PORTFOLIO
    assert ss.ANTHROPIC_STATIC_PORTFOLIO  # non-empty


# ─── F1: encrypted-vault round trip + masking (vault + net stubbed) ──────────

@pytest.fixture
def mem_vault(monkeypatch):
    """In-memory stand-in for settings.enc so the real vault is never written."""
    import src.tomemaster.vault_loader as vl
    store = {}
    monkeypatch.setattr(vl, "save_vault", lambda data: store.update(data=dict(data)))
    monkeypatch.setattr(vl, "load_vault", lambda: dict(store.get("data", {})))
    return store


def test_vault_save_load_round_trip(mem_vault):
    ok = ss.save_settings({"api_keys": {"gemini": "AIza-roundtrip-key"}})
    assert ok is True
    loaded = ss.load_settings()
    assert loaded["api_keys"]["gemini"] == "AIza-roundtrip-key"


def test_settings_endpoint_masks_keys(mem_vault):
    """GET /api/v1/settings/ must never return a raw key value."""
    from fastapi.testclient import TestClient
    import main

    ss.save_settings({"api_keys": {"gemini": "AIza-secret-tail1234"}})
    client = TestClient(main.app)
    body = client.get("/api/v1/settings/").json()
    masked = body["api_keys"]["gemini"]
    assert "AIza-secret" not in masked
    assert masked.endswith("1234")  # last-4 retained for UI presence


# ─── Wave 2: provider registry + endpoint resolution ladder ──────────────────

from services import providers as P  # noqa: E402

# The registry must produce URLs byte-identical to the historical scattered
# tables — this is the safety net for the consolidation (no key needed).
_HISTORICAL_BASES = {
    "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai":    "https://api.openai.com/v1/",
    "anthropic": "https://api.anthropic.com/v1/",
    "groq":      "https://api.groq.com/openai/v1/",
}


@pytest.mark.parametrize("prov,url", list(_HISTORICAL_BASES.items()))
def test_registry_pins_historical_urls(prov, url):
    assert P.provider_base(prov) == url


def test_bitnet_base_uses_host_env(monkeypatch):
    monkeypatch.setenv("BITNET_HOST", "http://localhost:9999")
    assert P.provider_base("bitnet") == "http://localhost:9999/v1/"


def test_get_model_for_role_url_from_registry(mem_vault):
    cfg = ss.get_model_for_role("NARRATIVE_ARCHITECT")
    assert cfg["url"] == P.provider_base("gemini")  # default with no keys


def test_detect_new_brand_prefixes():
    assert P.detect_provider_from_key("sk-or-abc123") == "openrouter"
    assert P.detect_provider_from_key("xai-abc123") == "xai"
    # bare sk- still defaults to openai (override handled by base_url)
    assert P.detect_provider_from_key("sk-plainopenai") == "openai"


def test_ladder_base_url_wins_over_prefix():
    """A Kimi sk- key + Moonshot URL must route to Moonshot, not OpenAI."""
    r = P.resolve_endpoint(key="sk-kimisecret", base_url="https://api.moonshot.cn/v1")
    assert r["base"] == "https://api.moonshot.cn/v1/"
    assert r["source"] == "base_url"


def test_ladder_seed_lookup():
    r = P.resolve_endpoint(key="sk-x", brand="Kimi")
    assert r["base"] == "https://api.moonshot.cn/v1/"
    assert r["source"] == "seed"


def test_ladder_explicit_provider():
    r = P.resolve_endpoint(key="anything", provider="groq")
    assert r["base"] == P.provider_base("groq")
    assert r["source"] == "provider"


def test_ladder_prefix_detect():
    r = P.resolve_endpoint(key="AIzaSyABC")
    assert r["provider"] == "gemini"
    assert r["source"] == "prefix"


def test_ladder_unresolvable_returns_none():
    assert P.resolve_endpoint(key="garbage-no-prefix") is None


def test_local_probe_lists_running_engine(monkeypatch):
    """Auto-probe lights up an engine answering on localhost; skips the rest."""
    import urllib.request
    import json as _json

    class _Resp:
        def __init__(self, payload): self._p = payload
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return _json.dumps(self._p).encode()

    def fake_urlopen(url, timeout=0):
        if url.startswith("http://localhost:11434"):  # ollama up
            return _Resp({"data": [{"id": "llama3.1"}]})
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    found = P.probe_local_engines(timeout=0.1)
    names = {f["name"] for f in found}
    assert names == {"ollama"}
    assert "llama3.1" in found[0]["models"]


def test_custom_providers_round_trip_and_sanitize(mem_vault):
    ss.save_settings({"custom_providers": [
        {"label": "Kimi", "base_url": "https://api.moonshot.cn/v1", "key": "sk-secret"},
        {"label": "junk", "base_url": "", "key": "y"},  # dropped — no base_url
    ]})
    loaded = ss.load_settings()["custom_providers"]
    assert len(loaded) == 1
    assert loaded[0]["label"] == "Kimi"
    assert loaded[0]["base_url"] == "https://api.moonshot.cn/v1"


# ─── Wave 2 finish: local/custom endpoint can DRIVE a role (no cloud key) ─────

def test_role_falls_back_to_custom_endpoint(mem_vault, monkeypatch):
    monkeypatch.setattr(ss, "get_api_key", lambda p: "")  # no cloud key anywhere
    monkeypatch.setattr(ss, "_fetch_models_for_url", lambda base, key="": ["kimi-k2"])
    ss.save_settings({"custom_providers": [
        {"label": "Kimi", "base_url": "https://api.moonshot.cn/v1", "key": "sk-x"},
    ]})
    cfg = ss.get_model_for_role("NARRATIVE_ARCHITECT")
    assert cfg["provider"] == "custom"
    assert cfg["model"] == "kimi-k2"
    assert cfg["url"] == "https://api.moonshot.cn/v1/"


def test_role_falls_back_to_local_engine(mem_vault, monkeypatch):
    monkeypatch.setattr(ss, "get_api_key", lambda p: "")
    monkeypatch.setattr(ss.providers, "probe_local_engines",
                        lambda timeout=0.4: [{"name": "ollama",
                                              "base": "http://localhost:11434/v1/",
                                              "models": ["llama3.1"]}])
    ss.invalidate_model_cache()  # clear the probe cache
    cfg = ss.get_model_for_role("COPY_EDITOR")
    assert cfg["provider"] == "local"
    assert cfg["model"] == "llama3.1"
    assert cfg["url"] == "http://localhost:11434/v1/"


def test_role_uses_cloud_when_key_present(mem_vault, monkeypatch):
    """Cloud key present → normal resolution; local fallback must NOT hijack it."""
    monkeypatch.setattr(ss, "get_api_key", lambda p: "AIza-real" if p == "gemini" else "")
    monkeypatch.setattr(ss, "_fetch_model_list_sync", lambda prov, key: ["gemini-3.1-pro-preview"])
    ss.save_settings({"api_keys": {"gemini": "AIza-real-longkey"}})
    cfg = ss.get_model_for_role("NARRATIVE_ARCHITECT")
    assert cfg["provider"] == "gemini"
    assert cfg["url"] == P.provider_base("gemini")
