import os
import asyncio
import json
import httpx
from contextlib import asynccontextmanager
from .settings_service import get_model_for_role, ANTHROPIC_STATIC_PORTFOLIO
from . import providers
from .pii_scrubber import pii_scrubber
from .ai import json_steward, specialist_registry, prompt_orchestrator
from .logger_service import log_api_usage

# [CERTIFICATION GRADE]: Standardized Gateway-Agnostic Dispatcher
# This service no longer "knows" about specific brands like Gemini or OpenAI.
# It only knows about "Industrial Roles" and "Gateway Endpoints."

# [MIGRATED]: JSON parsing moved to ai.json_steward
_robust_parse_json = json_steward.robust_parse

# [LOCAL JOB POLICY]: serialize local-engine inference so only ONE local job runs
# at a time. On low-power hardware (e.g. an 8 GB laptop) concurrent local jobs
# compound CPU load + RAM pressure → thermal throttle + UI lag. Cloud calls are
# unaffected (still concurrent). Thread-cap / process-priority are bitnet.cpp
# launch-side, not settable over HTTP — see LOCAL_AI_POLICY.md.
_LOCAL_INFERENCE_LOCK = asyncio.Lock()

def _is_local_target(url: str, provider: str) -> bool:
    u = (url or "").lower()
    return provider == "bitnet" or "localhost" in u or "127.0.0.1" in u or "0.0.0.0" in u

@asynccontextmanager
async def _local_single_flight(is_local: bool):
    if is_local:
        async with _LOCAL_INFERENCE_LOCK:
            yield
    else:
        yield

def _resolve_gateway_config(role: str, override: dict = None) -> dict:
    """[CONFIG RESOLVER]: Per-request override > settings vault.

    `override` is a partial dict with optional keys: provider, api_key, model,
    url. Whatever is missing falls back to the role-based settings.
    """
    base = get_model_for_role(role) or {}
    if not override:
        return base

    out = dict(base)
    provider_override = override.get("provider")
    model_override    = override.get("model")
    key_override      = override.get("api_key") or override.get("key")
    url_override      = override.get("url")

    # If provider is overridden, rebase URL/key from the single provider registry.
    if provider_override and provider_override != base.get("provider"):
        from .settings_service import get_api_key
        out["provider"] = provider_override
        out["url"] = providers.provider_base(provider_override) or base.get("url")
        # If no per-request key supplied, look up the provider's key from vault.
        if not key_override:
            out["key"] = get_api_key(provider_override) or base.get("key", "")

    if model_override and model_override != "auto":
        out["model"] = model_override
    if key_override:
        out["key"] = key_override
    if url_override:
        out["url"] = url_override

    return out


async def _call_anthropic_gateway(model: str, key: str, prompt: str, is_json: bool):
    """[ANTHROPIC ADAPTER]: Routes to /v1/messages with the messages-API auth
    headers and parses the messages-API response shape."""
    headers = {
        "x-api-key":         key,
        "anthropic-version": "2023-06-01",
        "Content-Type":      "application/json",
    }
    payload = {
        "model":      model,
        "max_tokens": 4096,
        "messages":   [{"role": "user", "content": prompt}],
    }
    target_url = "https://api.anthropic.com/v1/messages"
    print(f"GATEWAY PULSE: ANTHROPIC -> {target_url} (Model: {model})")

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(target_url, json=payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Anthropic Refused Request (HTTP {response.status_code}): {response.text}")
            data = response.json()
            blocks = data.get("content") or []
            raw_content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            # [LEDGER]: Anthropic usage is input_tokens + output_tokens.
            usage = data.get("usage") or {}
            total_tokens = (usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0)
            log_api_usage("Boardroom", "anthropic", model, {"total_tokens": total_tokens})
            if is_json:
                return _robust_parse_json(raw_content)
            return {"feedback": raw_content}
        except httpx.ConnectError:
            raise Exception(f"Anthropic Gateway Unreachable: {target_url}")


# Configurable Gemini safety categories — set permissive so the editor can analyze
# fiction with mature/violent themes (the OpenAI-compat endpoint can't relax these;
# the native SDK can). NOTE: this does NOT affect Gemini's core PROHIBITED_CONTENT
# policy, which is non-configurable — that content must go to another provider.
_GEMINI_SAFE_CATS = (
    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT",
    "HARM_CATEGORY_CIVIC_INTEGRITY",
)


async def _call_gemini_gateway(role: str, model: str, key: str, prompt: str, is_json: bool):
    """[GEMINI ADAPTER]: native google-genai SDK so we can set permissive safety
    thresholds (a manuscript editor must analyze mature fiction). Falls over to a
    free-tier-safe model on quota, and surfaces a clear, provider-switch message
    when Gemini's non-configurable core policy refuses the content."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    safety = [types.SafetySetting(category=c, threshold="BLOCK_NONE") for c in _GEMINI_SAFE_CATS]

    def _gen(m):
        kwargs = {"safety_settings": safety}
        if is_json:
            kwargs["response_mime_type"] = "application/json"
        return client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(**kwargs))

    print(f"GATEWAY PULSE: GEMINI(native) -> {model}")
    try:
        resp = await asyncio.to_thread(_gen, model)
    except Exception as e:
        msg = str(e)
        fb = _QUOTA_FALLBACK_MODEL.get("gemini")
        # Free keys can't use pro models (limit 0) -> quota error -> drop to flash.
        if fb and fb != model and ("429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()):
            print(f"GATEWAY FAILOVER: gemini:{model} -> quota; retrying with {fb}")
            model = fb
            resp = await asyncio.to_thread(_gen, model)
        else:
            raise

    text = None
    try:
        text = resp.text
    except Exception:
        text = None

    if not text:
        reason = None
        try:
            if getattr(resp, "candidates", None):
                reason = str(getattr(resp.candidates[0], "finish_reason", "") or "")
            if not reason and getattr(resp, "prompt_feedback", None):
                reason = str(getattr(resp.prompt_feedback, "block_reason", "") or "")
        except Exception:
            pass
        raise Exception(
            f"Gemini returned no content for model '{model}'"
            + (f" (blocked: {reason})" if reason else "")
            + ". Gemini's core content policy can refuse fiction with mature or violent "
              "themes and this cannot be disabled. Route this specialist to another "
              "provider (OpenAI / Anthropic) or a local model, which have no such policy."
        )

    usage = getattr(resp, "usage_metadata", None)
    total = getattr(usage, "total_token_count", 0) if usage else 0
    log_api_usage(role, "gemini", model, {"total_tokens": total or 0})
    if is_json:
        return _robust_parse_json(text)
    return {"feedback": text}


# [QUOTA SAFETY NET]: tier-safe fallback model per provider, used ONLY when the
# resolved model returns 429/503 at runtime. Not the primary selection.
_QUOTA_FALLBACK_MODEL = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "groq":   "llama-3.3-70b-versatile",
}


async def _call_standard_gateway(role: str, prompt: str, is_json: bool = True, override: dict = None):
    """[SOVEREIGN DISPATCH]: Universal handler for any OpenAI-compatible gateway."""
    config = _resolve_gateway_config(role, override)
    if not config:
        raise ValueError(f"Industrial Role '{role}' is not anchored to a gateway. Check Settings.")

    url      = config["url"]
    key      = config["key"]
    model    = config["model"]
    provider = config.get("provider")

    # [SOVEREIGN LOCK]: get_model_for_role marked this role un-servable locally.
    if provider == "sovereign_blocked":
        raise Exception(
            f"Sovereign Lock is ON and no local engine can perform '{role}' "
            f"(needs a {config.get('modality', 'capable')} model). "
            "Install a local model or turn off Sovereign Lock."
        )

    # [PII GATE]: Off by default — the editor needs real character names to
    # reach the model. Set preferences.pii_scrub=true in the encrypted vault to enable
    # for compliance-sensitive deployments.
    from .settings_service import load_settings
    if load_settings().get("preferences", {}).get("pii_scrub", False):
        prompt = pii_scrubber.anonymize_text(prompt)

    # [BRAND ADAPTERS]: Anthropic doesn't speak chat-completions. Branch to the
    # messages-API adapter; all OpenAI-compatible providers (gemini compat,
    # openai, groq, ollama) continue through the standard path.
    if provider == "anthropic":
        return await _call_anthropic_gateway(model, key, prompt, is_json)

    # [GEMINI NATIVE]: route Gemini through the SDK so we can relax safety filters
    # for fiction (the OpenAI-compat endpoint rejects safety_settings). Local/custom
    # OpenAI-compatible engines continue through the standard path below.
    if provider == "gemini":
        return await _call_gemini_gateway(role, model, key, prompt, is_json)

    # [CERTIFICATION STANDARD]: Use standard httpx for gateway communication.
    # [LOCAL JOB POLICY]: serialize local inference (one at a time); cloud is unaffected.
    async with _local_single_flight(_is_local_target(url, provider)):
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            if is_json:
                # Note: Some local gateways (Ollama) prefer 'json' in the prompt rather than a flag
                payload["response_format"] = {"type": "json_object"}

            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            # Resolve target endpoint
            base_url = url.rstrip('/')
            target_url = base_url if base_url.endswith('/chat/completions') else f"{base_url}/chat/completions"

            print(f"GATEWAY PULSE: {role} -> {target_url} (Model: {model})")

            try:
                response = await client.post(target_url, json=payload, headers=headers)
                # [QUOTA FAILOVER]: a 429 (quota/tier limit) or 503 (overloaded) on the
                # resolved model → retry ONCE with a tier-safe fallback for this provider.
                # The tier limit is only revealed by the 429 (e.g. a free Gemini key cannot
                # use gemini-*-pro), so this is a runtime safety net — paid users still get
                # the top-ranked model; free keys auto-drop to flash instead of failing.
                if response.status_code in (429, 503):
                    fb = _QUOTA_FALLBACK_MODEL.get(provider)
                    if fb and fb != model:
                        print(f"GATEWAY FAILOVER: {provider}:{model} -> HTTP {response.status_code}; retrying with {fb}")
                        payload["model"] = fb
                        response = await client.post(target_url, json=payload, headers=headers)
                        if response.status_code == 200:
                            model = fb  # so the ledger records the model that actually ran
                if response.status_code != 200:
                    raise Exception(
                        f"{(provider or 'gateway').title()} refused the request for model "
                        f"'{model}' (HTTP {response.status_code}). Most likely a bad or missing "
                        f"{provider or 'provider'} API key — re-check it in Settings. "
                        f"Provider said: {response.text.strip()[:200]}"
                    )

                data = response.json()
                # [ROBUST EXTRACT]: a 200 can still carry no usable content — a safety
                # block, an agentic/non-chat model (e.g. deep-research), or an error body
                # returned as 200. Surface the REAL reason instead of a bare KeyError.
                raw_content = None
                if isinstance(data, dict):
                    choices = data.get("choices") or []
                    if choices and isinstance(choices[0], dict):
                        raw_content = (choices[0].get("message") or {}).get("content")
                if not raw_content:
                    finish = None
                    detail = None
                    if isinstance(data, dict):
                        ch = data.get("choices") or []
                        if ch and isinstance(ch[0], dict):
                            finish = ch[0].get("finish_reason")
                        err = data.get("error")
                        detail = err.get("message") if isinstance(err, dict) else None
                    raise Exception(
                        f"{(provider or 'gateway').title()} returned no usable content for model '{model}'"
                        + (f" (finish_reason: {finish})" if finish else "")
                        + (f": {detail}" if detail else ". This model may not support standard chat completions — choose a different model.")
                    )
                # [LEDGER]: OpenAI-compatible gateways (incl. Gemini-compat, Groq)
                # return token usage here — log it so the boardroom shows up in the
                # cost ledger, not just PDF OCR.
                usage = data.get("usage") or {}
                log_api_usage(role, provider or "unknown", model,
                              {"total_tokens": usage.get("total_tokens", 0) or 0})

                if is_json:
                    return _robust_parse_json(raw_content)
                return {"feedback": raw_content}
            except httpx.ConnectError:
                raise Exception(f"Gateway Unreachable: {target_url}. Ensure your local server or VPN is active.")

# [REMOVED]: rank_models_for_role() + auto_configure_gateway_async() were dead and
# broken — no callers in the app, and auto_configure imported the nonexistent
# settings_service.detect_gateway_from_key (instant ImportError if ever invoked).
# Live model ranking is settings_service._resolve_auto_model + _ROLE_RANKING.

# [ROUTING TABLE]: Default discovery endpoints come from the single provider
# registry (services.providers) — no duplicate URL table lives here anymore.


async def list_models_async(provider_type: str, api_key: str, url: str = None):
    """Universal Discovery Pulse for any gateway URL.

    `url` is optional — when omitted, falls back to the default endpoint for
    `provider_type`. Anthropic gets a static portfolio because it has no public
    /models endpoint.
    """
    if provider_type == "anthropic":
        # Real GET /v1/models — kept HONEST: a non-200 (bad/expired key) must
        # surface as failure, never a silent static fallback, because
        # validate_key_async treats success here as "key is live."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )
            if res.status_code == 200:
                ids = [m["id"] for m in res.json().get("data", []) if m.get("id")]
                return {"success": True, "models": ids or list(ANTHROPIC_STATIC_PORTFOLIO)}
            return {"success": False, "message": f"Discovery failed with code {res.status_code}", "models": []}
        except Exception as e:
            return {"success": False, "message": str(e), "models": []}

    if not url:
        url = providers.provider_base(provider_type)
    if not url:
        return {"success": False, "message": f"Unknown provider '{provider_type}' and no URL provided.", "models": []}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            target_url = url.rstrip('/') + "/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            res = await client.get(target_url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                # Handle varying /models responses (OpenAI vs Gemini vs Ollama)
                if "data" in data: # OpenAI-style
                    return {"success": True, "models": [m["id"] for m in data["data"]]}
                if "models" in data: # Ollama-style
                    return {"success": True, "models": [m["name"] for m in data["models"]]}
            return {"success": False, "message": f"Discovery failed with code {res.status_code}", "models": []}
        except Exception as e:
            return {"success": False, "message": str(e), "models": []}


async def validate_key_async(provider: str, api_key: str, model: str = None, custom_url: str = None):
    """[HANDSHAKE GATE]: Lightweight key validation. Performs a portfolio fetch
    against the provider's discovery endpoint; a 200 means the key is live."""
    if not api_key:
        return {"success": False, "message": "No API key provided."}

    url = custom_url or providers.provider_base(provider)
    result = await list_models_async(provider, api_key, url)

    if result.get("success"):
        portfolio = result.get("models", [])
        return {
            "success": True,
            "message": f"Handshake confirmed. {len(portfolio)} model(s) authorized.",
            "models": portfolio,
        }
    return {"success": False, "message": result.get("message", "Handshake refused.")}


async def discover_gateway_async(brand_name: str, provider: str, api_key: str) -> str:
    """[SCOUT MISSION]: Resolves an unknown brand's gateway URL.

    Currently maps to the known provider table; raises if the brand is unknown.
    Future expansion can probe candidate URLs with the supplied key.
    """
    url = providers.provider_base(provider)
    if not url:
        raise ValueError(f"No known gateway for brand '{brand_name}' (provider hint: '{provider}').")
    return url


def _build_prompt(content: str, persona: str, user_chapters: list = None, synthesis_mode: bool = False):
    """[LEGACY-COMPAT WRAPPER]: Returns (prompt, is_json) to match the
    /draft-expert router's destructuring. Synthesis mode currently has no
    branching effect — reserved for future multi-persona consolidation."""
    prompt, is_json, _role = prompt_orchestrator.build_industrial_prompt(content, persona, user_chapters)
    return prompt, is_json

# [SAFETY]: Emergency flag to bypass local gateways if hardware saturation occurs
KILL_LOCAL_MODE = False

# ─── Industrial Pipeline Specialists ──────────────────────────────────────────
# [P0 RESTORED]: The CrewAI BoardroomCrew migration (PR #15) shipped without its
# dependency — `crewai` was never added to requirements.txt or the venv, leaving
# the backend unbootable. These direct-gateway specialist functions are restored
# from the pre-PR#15 tree and are the canonical dispatch path. CrewAI remains
# available only behind the optional /transcribe/start-pipeline experiment.

def _build_override(provider: str = None, api_key: str = None, model: str = None) -> dict:
    """Collects per-request overrides into the dict shape _call_standard_gateway expects."""
    o = {}
    if provider: o["provider"] = provider
    if api_key:  o["api_key"]  = api_key
    if model:    o["model"]    = model
    return o or None


def _is_content_block(msg: str) -> bool:
    """True when an error indicates the model refused the content on policy grounds
    (a safety/PROHIBITED block), as opposed to a key/quota/network failure."""
    m = (msg or "").lower()
    return any(k in m for k in (
        "prohibited_content", "content_filter", "no usable content",
        "no content for model", "blocked:", "safety",
    ))


def _is_quota_error(msg: str) -> bool:
    """True when an error is a rate-limit / quota exhaustion (free-tier RPM/RPD)."""
    m = (msg or "").lower()
    return any(k in m for k in (
        "429", "resource_exhausted", "quota", "rate limit", "too many requests", "exhausted",
    ))


async def _analyze_persona_by_chapter(persona, user_chapters, override, intensity):
    """[GRACEFUL DEGRADATION]: the model refused the whole manuscript on content
    policy — analyze it CHAPTER BY CHAPTER so the analyzable chapters still get a
    report. QUOTA-AWARE: uses the tier-safe model directly (no wasted pro calls) and
    STOPS the moment a rate/quota limit is hit instead of hammering the key — then
    shows everything analyzed so far with a clear next step."""
    # Use the free-tier-safe model directly so we don't burn a 429 pro call per chapter.
    ov = dict(override or {})
    if ov.get("provider") in _QUOTA_FALLBACK_MODEL:
        ov["model"] = _QUOTA_FALLBACK_MODEL[ov["provider"]]

    parts, suggestions, blocked, analyzed = [], [], [], 0
    quota_stop = None
    for i, ch in enumerate(user_chapters or []):
        ch = ch or {}
        ch_text = (ch.get("content") or "").strip()
        title = ch.get("suggested_title") or ch.get("title") or f"Chapter {i + 1}"
        if not ch_text:
            continue
        try:
            prompt, is_json, role = prompt_orchestrator.build_industrial_prompt(ch_text, persona, None, intensity=intensity)
            res = await _call_standard_gateway(role, prompt, is_json, override=ov)
            fb = res.get("feedback", "") if isinstance(res, dict) else str(res)
            if isinstance(res, dict):
                suggestions.extend(res.get("suggestions", []) or [])
            parts.append(f"## {title}\n\n{fb}")
            analyzed += 1
        except Exception as ce:
            cm = str(ce)
            if _is_quota_error(cm):
                quota_stop = title          # quota won't recover this run — STOP, don't hammer.
                break
            if _is_content_block(cm):
                blocked.append(title)
                parts.append(f"## {title}\n\n*Skipped — the model's content policy refused this chapter.*")
            else:
                parts.append(f"## {title}\n\n*Could not analyze: {cm[:140]}*")

    # Nothing usable AND we stopped on quota: raise a clear quota error (the caller's
    # handler appends the billing/usage link). Otherwise, always show partial results.
    if analyzed == 0 and not blocked:
        raise Exception(
            "Rate limit / quota reached before any chapter could be analyzed. Free API "
            "tiers are very limited — for a full manuscript, use a LOCAL model (Sovereign "
            "mode: unlimited, free, no content policy) or add a paid key."
        )

    note = ("> **Note:** the model refused the full manuscript, so it was analyzed chapter "
            "by chapter.")
    if blocked:
        note += f" Skipped on content policy: {', '.join(blocked)}."
    if quota_stop:
        note += (f" **Stopped at {quota_stop} — the provider's free-tier rate/quota limit "
                 f"was reached after {analyzed} chapter(s).** To finish the rest, switch this "
                 f"specialist to a LOCAL model (Sovereign mode: unlimited & free) or a paid key.")
    return {"feedback": note + "\n\n" + "\n\n".join(parts), "suggestions": suggestions}


async def run_boardroom_parallel(
    text: str,
    personas: list,
    provider: str = None,
    api_key: str = None,
    *,
    model: str = None,
    user_chapters: list = None,
    intensity: str = "balanced",
    **kwargs,
):
    """
    [HIGH VELOCITY]: Dispatches manuscript to multiple specialist roles simultaneously.
    Uses true concurrency to ensure minimal directorial latency.

    Per-request `provider`/`api_key`/`model` override the role-based gateway
    resolved from the encrypted vault, so the UI's slot and key choices take effect.
    `intensity` (soft|balanced|hard) hardens or softens the critique tone.
    """
    override = _build_override(provider, api_key, model)

    async def _execute_expert(persona: str):
        try:
            # [MODULAR ORCHESTRATION]: Delegate prompt building to the orchestrator
            prompt, is_json, role = prompt_orchestrator.build_industrial_prompt(
                text, persona, user_chapters, intensity=intensity
            )
            response = await _call_standard_gateway(role, prompt, is_json, override=override)
            return persona, response
        except Exception as e:
            msg = str(e)
            # [GRACEFUL DEGRADATION]: if the model refused the WHOLE submission on
            # content policy, retry chapter-by-chapter so the analyzable chapters still
            # get a report instead of the user losing the entire pass.
            if _is_content_block(msg) and user_chapters and any((c or {}).get("content") for c in user_chapters):
                try:
                    return persona, await _analyze_persona_by_chapter(persona, user_chapters, override, intensity)
                except Exception:
                    pass  # fall through to the honest error below
            # Surface the raw provider error (governance: never swallow), then append a
            # self-service resolution link (billing/keys). Tagged error=True so the UI
            # shows it as in-situ status, NOT as a report.
            link = providers.provider_help_link(msg, (override or {}).get("provider"))
            return persona, {"feedback": f"Expert {persona} Offline: {msg}{link}", "error": True}

    # DISPATCH ALL SPECIALISTS CONCURRENTLY
    tasks = [_execute_expert(p) for p in personas]
    completed = await asyncio.gather(*tasks)

    return {persona: response for persona, response in completed}


async def run_structural_analysis_async(text: str, provider: str = None, api_key: str = None, *, model: str = None, local_mode: bool = False):
    """Routes the 'Architect' audit to the NARRATIVE_ARCHITECT slot."""
    prompt, _is_json = _build_prompt(text, "Structural Architect")
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", prompt, is_json=True,
                                        override=_build_override(provider, api_key, model))


async def run_sentinel_async(content: str, provider: str = None, api_key: str = None, model: str = None):
    return await _call_standard_gateway("SOVEREIGN_LIAISON", f"CONTINUITY AUDIT: {content[:10000]}", is_json=True,
                                        override=_build_override(provider, api_key, model))


async def run_heatmap_async(content: str, provider: str = None, api_key: str = None, model: str = None):
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", f"PACING HEATMAP: {content[:10000]}", is_json=True,
                                        override=_build_override(provider, api_key, model))


async def run_dynamic_arc_async(content: str, provider: str = None, api_key: str = None, model: str = None):
    """[DYNAMIC ARC]: Interactive emotional arc adjustment with plot recommendations."""
    return await _call_standard_gateway(
        "NARRATIVE_ARCHITECT",
        f"DYNAMIC EMOTIONAL ARC ADJUSTMENT — return JSON with plot_points[] and arc_curve[]:\n{content[:10000]}",
        is_json=True,
        override=_build_override(provider, api_key, model),
    )


async def analyze_emotional_arc_async(text: str, provider: str = None, api_key: str = None, *, model: str = None, local_mode: bool = False):
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", f"EMOTIONAL ARC: {text[:10000]}", is_json=True,
                                        override=_build_override(provider, api_key, model))


async def generate_moodboard_async(text: str, provider: str = None, api_key: str = None, model: str = None):
    return await _call_standard_gateway("MARKETING_ANALYST", f"MOODBOARD SYNTHESIS: {text[:5000]}", is_json=True,
                                        override=_build_override(provider, api_key, model))


async def analyze_world_bible_async(text: str, provider: str = None, api_key: str = None, *, model: str = None, local_mode: bool = False):
    return await _call_standard_gateway("SOVEREIGN_LIAISON", f"WORLD BIBLE EXTRACTION: {text[:10000]}", is_json=True,
                                        override=_build_override(provider, api_key, model))
