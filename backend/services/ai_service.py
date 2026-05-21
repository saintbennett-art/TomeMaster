import os
import asyncio
import json
import httpx
from .settings_service import get_model_for_role
from .pii_scrubber import pii_scrubber
from .ai import json_steward, specialist_registry, prompt_orchestrator

# [CERTIFICATION GRADE]: Standardized Gateway-Agnostic Dispatcher
# This service no longer "knows" about specific brands like Gemini or OpenAI.
# It only knows about "Industrial Roles" and "Gateway Endpoints."

# [MIGRATED]: JSON parsing moved to ai.json_steward
_robust_parse_json = json_steward.robust_parse

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

    # If provider is overridden, rebase URL/key from the provider table.
    if provider_override and provider_override != base.get("provider"):
        from .settings_service import get_api_key
        out["provider"] = provider_override
        provider_urls = {
            "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai/",
            "openai":    "https://api.openai.com/v1/",
            "anthropic": "https://api.anthropic.com/v1/",
            "groq":      "https://api.groq.com/openai/v1/",
        }
        out["url"] = provider_urls.get(provider_override, base.get("url"))
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
            if is_json:
                return _robust_parse_json(raw_content)
            return {"feedback": raw_content}
        except httpx.ConnectError:
            raise Exception(f"Anthropic Gateway Unreachable: {target_url}")


async def _call_standard_gateway(role: str, prompt: str, is_json: bool = True, override: dict = None):
    """[SOVEREIGN DISPATCH]: Universal handler for any OpenAI-compatible gateway."""
    config = _resolve_gateway_config(role, override)
    if not config:
        raise ValueError(f"Industrial Role '{role}' is not anchored to a gateway. Check Settings.")

    url      = config["url"]
    key      = config["key"]
    model    = config["model"]
    provider = config.get("provider")

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

    # [CERTIFICATION STANDARD]: Use standard httpx for gateway communication
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
            if response.status_code != 200:
                raise Exception(f"Gateway Refused Request (HTTP {response.status_code}): {response.text}")
                
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            
            if is_json:
                return _robust_parse_json(raw_content)
            return {"feedback": raw_content}
        except httpx.ConnectError:
            raise Exception(f"Gateway Unreachable: {target_url}. Ensure your local server or VPN is active.")

def rank_models_for_role(models: list[str], role: str) -> str:
    """
    [APEX DISCOVERY]: Ranks models based on role-specific narrative intelligence.
    """
    if not models: return None
    m_list = [m.lower() for m in models]
    
    if role == "TRANSCRIBER_LEAD":
        # Prioritize Vision Apex (Llama 3.2 90B > 11B > Gemini Flash)
        for target in ["90b-vision", "11b-vision", "vision", "flash"]:
            match = next((m for m in m_list if target in m), None)
            if match: return models[m_list.index(match)]
            
    if role == "NARRATIVE_ARCHITECT":
        # Prioritize Context/Reasoning Apex (3.1 Pro > 4o > 1.5 Pro)
        for target in ["3.1-pro", "gpt-4o", "1.5-pro", "pro"]:
            match = next((m for m in m_list if target in m), None)
            if match: return models[m_list.index(match)]

    if role == "COPY_EDITOR":
        # Prioritize Linguistic Fidelity (Sonnet > Opus > GPT-4o)
        for target in ["sonnet", "opus", "4o", "latest"]:
            match = next((m for m in m_list if target in m), None)
            if match: return models[m_list.index(match)]

    # Default to the first model if no apex match found
    return models[0]

async def auto_configure_gateway_async(api_key: str):
    """
    [SELF-HEALING HANDSHAKE]: 
    1. Detects Gateway via Heuristic Signature.
    2. Handshakes to retrieve live Portfolio.
    3. Auto-assigns Apex models to Industrial Roles.
    """
    from .settings_service import detect_gateway_from_key, save_settings, load_settings
    
    discovery = detect_gateway_from_key(api_key)
    if not discovery:
        return {"success": False, "message": "Signature Mismatch: Key format unknown."}
    
    # 1. Register the Gateway
    settings = load_settings()
    gw_name = discovery["name"]
    settings["gateways"][gw_name] = {
        "url": discovery["url"],
        "key": api_key,
        "provider_type": discovery["provider_type"]
    }
    
    # 2. Discovery Pulse (Retrieve Portfolio)
    try:
        portfolio = await list_models_async(discovery["provider_type"], api_key, discovery["url"])
        if not portfolio.get("success"):
            raise Exception(portfolio.get("message", "Discovery Pulse failed."))
            
        models = portfolio["models"]
        settings["gateways"][gw_name]["default_model"] = rank_models_for_role(models, "NARRATIVE_ARCHITECT")
        
        # 3. Auto-Assign Apex Models to Roles
        roles = ["TRANSCRIBER_LEAD", "NARRATIVE_ARCHITECT", "COPY_EDITOR", "MARKETING_ANALYST", "SOVEREIGN_LIAISON"]
        for role in roles:
            # If this gateway has an "Apex" for this role, promote it
            apex = rank_models_for_role(models, role)
            if apex:
                settings["role_mappings"][role] = gw_name
                
        save_settings(settings)
        return {"success": True, "message": f"Gateway '{gw_name}' Established. Portfolio Auto-Assigned.", "portfolio": models}
        
    except Exception as e:
        return {"success": False, "message": f"Handshake Failure: {str(e)}"}

# [ROUTING TABLE]: Default discovery endpoints per provider. Used when callers
# don't pass an explicit gateway URL.
_PROVIDER_DISCOVERY_URLS = {
    "openai":    "https://api.openai.com/v1/",
    "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq":      "https://api.groq.com/openai/v1/",
    "anthropic": "https://api.anthropic.com/v1/",
}


async def list_models_async(provider_type: str, api_key: str, url: str = None):
    """Universal Discovery Pulse for any gateway URL.

    `url` is optional — when omitted, falls back to the default endpoint for
    `provider_type`. Anthropic gets a static portfolio because it has no public
    /models endpoint.
    """
    if provider_type == "anthropic":
        return {"success": True, "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-latest",
            "claude-3-opus-20240229",
        ]}

    if not url:
        url = _PROVIDER_DISCOVERY_URLS.get(provider_type)
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

    url = custom_url or _PROVIDER_DISCOVERY_URLS.get(provider)
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
    url = _PROVIDER_DISCOVERY_URLS.get(provider)
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

def _build_override(provider: str = None, api_key: str = None, model: str = None) -> dict:
    """Collects per-request overrides into the dict shape _call_standard_gateway expects."""
    o = {}
    if provider: o["provider"] = provider
    if api_key:  o["api_key"]  = api_key
    if model:    o["model"]    = model
    return o or None


async def run_boardroom_parallel(
    text: str,
    personas: list,
    provider: str = None,
    api_key: str = None,
    *,
    model: str = None,
    user_chapters: list = None,
    **kwargs,
):
    """
    [HIGH VELOCITY]: Dispatches manuscript to multiple specialist roles simultaneously.
    Uses true concurrency to ensure minimal directorial latency.

    Per-request `provider`/`api_key`/`model` override the role-based gateway
    resolved from the encrypted vault, so the UI's slot and key choices take effect.
    """
    override = _build_override(provider, api_key, model)

    async def _execute_expert(persona: str):
        try:
            # [MODULAR ORCHESTRATION]: Delegate prompt building to the orchestrator
            prompt, is_json, role = prompt_orchestrator.build_industrial_prompt(
                text, persona, user_chapters
            )

            # [KILL SWITCH]: Redirect to cloud if local mode is bricking the system
            if KILL_LOCAL_MODE and role == "TRANSCRIBER_LEAD":
                pass

            response = await _call_standard_gateway(role, prompt, is_json, override=override)
            return persona, response
        except Exception as e:
            return persona, {"feedback": f"Expert {persona} Offline: {str(e)}"}

    # DISPATCH ALL SPECIALISTS CONCURRENTLY
    tasks = [_execute_expert(p) for p in personas]
    completed = await asyncio.gather(*tasks)

    return {persona: response for persona, response in completed}


async def run_structural_analysis_async(text: str, provider: str = None, api_key: str = None, *, model: str = None, local_mode: bool = False):
    """Routes the 'Architect' audit to the NARRATIVE_ARCHITECT slot."""
    prompt, _is_json = _build_prompt(text, "Developmental Editor")
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
