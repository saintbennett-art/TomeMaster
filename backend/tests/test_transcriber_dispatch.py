"""Sovereign OCR dispatch: the local/custom client factory and the failover
protocol that threads engine base URLs on BOTH the primary and fallback tiers.

No network — the OpenAI client is constructed (not called) and the factory is
monkeypatched, so these run offline.
"""
import asyncio

from PIL import Image

from services.transcriber import ai_engine


# ─── Client factory: local engines get an OpenAI-compatible client ───────────

def test_local_provider_builds_openai_client_with_base_url():
    client = ai_engine._get_ai_client("local", "", base_url="http://localhost:11434/v1/")
    assert client is not None
    assert "localhost:11434" in str(client.base_url)


def test_local_provider_without_base_url_returns_none():
    # No endpoint → cannot guess the engine → honest None (never a silent skip).
    assert ai_engine._get_ai_client("ollama", "", base_url=None) is None


def test_bitnet_self_heals_base_url(monkeypatch):
    monkeypatch.setenv("BITNET_HOST", "http://localhost:8080")
    client = ai_engine._get_ai_client("bitnet", "", base_url=None)
    assert client is not None
    assert "8080" in str(client.base_url)


def test_unknown_provider_returns_none():
    assert ai_engine._get_ai_client("acme-mystery", "k") is None


# ─── Failover: base_url is threaded to the factory on both tiers ─────────────

class _FakeMsg:
    content = "<page><text>ok</text></page>"


class _FakeChoice:
    message = _FakeMsg()


class _FakeRes:
    choices = [_FakeChoice()]


class _FakeCompletions:
    def create(self, **kwargs):
        return _FakeRes()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeClient:
    chat = _FakeChat()


def test_failover_threads_base_url_to_both_tiers(monkeypatch):
    """Primary local engine is unreachable → gear down to the fallback local
    engine, and prove EACH tier's base_url reached the client factory."""
    seen = []

    def fake_get_client(provider, key, base_url=None):
        seen.append((provider, base_url))
        if provider == "primary-engine":
            return None            # primary "down" → forces fallback
        return _FakeClient()       # fallback answers via OpenAI-compat chat path

    monkeypatch.setattr(ai_engine, "_get_ai_client", fake_get_client)

    img = Image.new("RGB", (8, 8))
    text, used_prov, used_mod = asyncio.run(
        ai_engine._call_ai_with_failover(
            img,
            "primary-engine", "vision-a", "",
            fallback_provider="fallback-engine", fallback_model="vision-b",
            primary_base_url="http://prim:11434/v1/",
            fallback_base_url="http://fall:8080/v1/",
        )
    )

    assert used_prov == "fallback-engine"
    assert used_mod == "vision-b"
    assert "ok" in text
    # The key assertion: the fix — both endpoints were handed to the factory.
    assert ("primary-engine", "http://prim:11434/v1/") in seen
    assert ("fallback-engine", "http://fall:8080/v1/") in seen
