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

async def _call_standard_gateway(role: str, prompt: str, is_json: bool = True):
    """[SOVEREIGN DISPATCH]: Universal handler for any OpenAI-compatible gateway."""
    config = get_model_for_role(role)
    if not config:
        raise ValueError(f"Industrial Role '{role}' is not anchored to a gateway. Check Settings.")

    url = config["url"]
    key = config["key"]
    model = config["model"]

    # [FERPA COMPLIANCE]: Scrub all PII before the prompt leaves the boundary
    prompt = pii_scrubber.anonymize_text(prompt)

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

async def list_models_async(provider_type: str, api_key: str, url: str):
    """Universal Discovery Pulse for any gateway URL."""
    # Simplified standard list logic
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
            return {"success": False, "message": f"Discovery failed with code {res.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

# [SAFETY]: Emergency flag to bypass local gateways if hardware saturation occurs
KILL_LOCAL_MODE = False

# ─── Industrial Pipeline Specialists ──────────────────────────────────────────

async def run_boardroom_parallel(text: str, personas: list[str], **kwargs):
    """
    [HIGH VELOCITY]: Dispatches manuscript to multiple specialist roles simultaneously.
    Uses true concurrency to ensure minimal directorial latency.
    """
    async def _execute_expert(persona: str):
        try:
            # [MODULAR ORCHESTRATION]: Delegate prompt building to the orchestrator
            prompt, is_json, role = prompt_orchestrator.build_industrial_prompt(
                text, persona, kwargs.get('user_chapters')
            )
            
            # [KILL SWITCH]: Redirect to cloud if local mode is bricking the system
            if KILL_LOCAL_MODE and role == "TRANSCRIBER_LEAD":
                pass

            response = await _call_standard_gateway(role, prompt, is_json)
            return persona, response
        except Exception as e:
            return persona, {"feedback": f"Expert {persona} Offline: {str(e)}"}

    # DISPATCH ALL SPECIALISTS CONCURRENTLY
    tasks = [_execute_expert(p) for p in personas]
    completed = await asyncio.gather(*tasks)
    
    return {persona: response for persona, response in completed}

async def run_structural_analysis_async(text: str, **kwargs):
    """Routes the 'Architect' audit to the NARRATIVE_ARCHITECT slot."""
    from .ai_service_legacy import _build_prompt
    prompt, _ = _build_prompt(text, "Developmental Editor")
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", prompt, is_json=True)

async def run_sentinel_async(content: str, **kwargs):
    return await _call_standard_gateway("SOVEREIGN_LIAISON", f"CONTINUITY AUDIT: {content[:10000]}", is_json=True)

async def run_heatmap_async(content: str, **kwargs):
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", f"PACING HEATMAP: {content[:10000]}", is_json=True)

async def analyze_emotional_arc_async(text: str, **kwargs):
    return await _call_standard_gateway("NARRATIVE_ARCHITECT", f"EMOTIONAL ARC: {text[:10000]}", is_json=True)

async def generate_moodboard_async(text: str, **kwargs):
    return await _call_standard_gateway("MARKETING_ANALYST", f"MOODBOARD SYNTHESIS: {text[:5000]}", is_json=True)

async def analyze_world_bible_async(text: str, **kwargs):
    return await _call_standard_gateway("SOVEREIGN_LIAISON", f"WORLD BIBLE EXTRACTION: {text[:10000]}", is_json=True)
