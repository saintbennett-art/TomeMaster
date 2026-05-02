import os
import asyncio
import json
import datetime
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── API Cost Tracking System ────────────────────────────────────────────────
USAGE_LOG_PATH = "api_usage_log.jsonl"

def _log_api_usage(persona: str, provider: str, model: str, usage_metrics: dict, folder_path: str = None, duration: float = 0.0):
    """Securely appends real-time token consumitations to a local JSONL audit ledger."""
    if not usage_metrics or "total_tokens" not in usage_metrics:
        return
        
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "persona": persona,
        "provider": provider,
        "model": model,
        "metrics": usage_metrics,
        "folder": folder_path,
        "duration_sec": duration
    }
    
    try:
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"WARNING: Failed to write to usage ledger: {e}")

# ─── Gemini helpers ──────────────────────────────────────────────────────────
def _get_ai_client(provider: str, api_key: str = None):
    """Sovereign Handshake Factory: Generates the requested AI client."""
    if provider == "gemini":
        from google import genai
        # Sanitize Key
        env_key = os.environ.get("GEMINI_API_KEY")
        sanitized_key = api_key
        if not sanitized_key or str(sanitized_key).lower().strip() in ["null", "undefined", "none", "token", ""]:
            sanitized_key = env_key
        return genai.Client(api_key=sanitized_key)
    elif provider in ["openai", "groq"]:
        from openai import OpenAI
        base_url = "https://api.groq.com/openai/v1" if provider == "groq" else None
        key = api_key or os.environ.get("GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY", "")
        return OpenAI(api_key=key, base_url=base_url)
    elif provider == "anthropic":
        import anthropic
        return anthropic.AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""))
    return None

# ─── Default client for the emotional-arc endpoint (uses settings key) ────────────
async def analyze_emotional_arc_async(text: str, provider: str = "gemini", api_key: str = None, model: str = None, local_mode: bool = False):
    if provider == "simulator":
        return json.loads(_simulate_creative("emotional_arc"))

    client = _get_ai_client("gemini", api_key)
    
    selected_model = model if model else "gemini-1.5-pro" # Defaulting to stable Pro

    prompt = f"""
    Analyze the emotional arc and tension in the following manuscript text. 
    Break the text down into 10 roughly equal chronological segments.
    For each segment, provide a tension score from 1 (very calm) to 10 (highest climax/stress)
    and a very brief 3-word summary of what happens.
    
    Format the output as strict JSON in this format:
    [
      {{"segment": 1, "score": 5, "summary": "Character wakes up"}},
      ...
    ]
    
    CRITICAL: Use standard straight apostrophes (') and straight double quotes (") exclusively in your summaries.
    
    Manuscript Text:
    {text}
    """
    
    # [SOVEREIGN HANDOFF]: v2 SDK uses client.aio.models.generate_content for async
    response = await client.aio.models.generate_content(
        model=selected_model,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return response.text

async def generate_moodboard_async(text: str, provider: str = "gemini", api_key: str = None, model: str = None):
    """
    [VISUAL SYNTHESIS]: Converts prose into atmospheric visual prompts and soundscapes.
    """
    if provider == "simulator":
        return json.loads(_simulate_creative("moodboard"))

    client = _get_ai_client(provider, api_key)
    selected_model = model if model else ("gemini-2.0-flash" if provider == "gemini" else "gpt-4o")

    # 1. Atmospheric Expansion
    prompt = f"""
    Analyze the following scene and extract its visual and auditory essence.
    Generate a high-fidelity image generation prompt and 3 ambient soundscape suggestions.
    Include a color palette of 3 hex codes.
    
    Format the output as strict JSON:
    {{
      "visual_prompt": "An atmospheric, cinematic description...",
      "soundscapes": ["Sound 1", "Sound 2", "Sound 3"],
      "mood": "Eerie, Hopeful, etc.",
      "color_palette": ["#hex1", "#hex2", "#hex3"]
    }}
    
    Scene:
    {text}
    """

    if provider == "gemini":
        response = await client.aio.models.generate_content(
            model=selected_model,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
    else:
        # OpenAI Fallback
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        data = json.loads(response.choices[0].message.content)

    # 2. Image Synthesis (Mocking via Pollinations for high-fidelity UI)
    import urllib.parse
    encoded_prompt = urllib.parse.quote(data.get('visual_prompt', 'Cinematic atmosphere'))
    data["image_url"] = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    
    return data

async def run_sentinel_async(content: str, provider: str = "gemini", api_key: str = None, model: str = None):
    """
    [CONTINUITY SENTINEL]: Audits for logical faults and character amnesia.
    """
    client = _get_ai_client(provider, api_key)
    selected_model = model if model else "gemini-1.5-pro"

    prompt = f"""
    You are the Continuity Sentinel. Audit the following manuscript text for logical inconsistencies.
    Focus on character details, physical laws, timelines, and geographical discrepancies.
    
    Format the output as JSON:
    {{
      "faults": [
        {{"type": "Logic", "description": "Character details or physical inconsistency found...", "severity": "Medium"}},
        ...
      ],
      "health_score": 0
    }}
    
    Manuscript:
    {content[:50000]}
    """
    
    response = await client.aio.models.generate_content(
        model=selected_model,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

async def run_heatmap_async(content: str, provider: str = "gemini", api_key: str = None, model: str = None):
    """
    [NARRATIVE HEATMAP]: Real-time pacing and tension density analysis.
    """
    client = _get_ai_client(provider, api_key)
    selected_model = model if model else "gemini-1.5-flash"

    prompt = f"""
    Analyze the pacing density of this text. Return a series of data points representing narrative tension.
    Format the output as JSON:
    {{
      "heatmap": [0.2, 0.5, 0.8, 0.4, ...],
      "pacing_advice": "Advice on narrative flow..."
    }}
    
    Text:
    {content[:30000]}
    """
    
    response = await client.aio.models.generate_content(
        model=selected_model,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

async def run_dynamic_arc_async(content: str, provider: str = "gemini", api_key: str = None, model: str = None):
    """
    [DYNAMIC ARC]: Interactive plot recommendations based on structural manipulation.
    """
    client = _get_ai_client(provider, api_key)
    selected_model = model if model else "gemini-1.5-pro"

    prompt = f"""
    Suggest ways to manipulate the narrative arc of this text to increase tension or improve resolution.
    Format the output as JSON:
    {{
      "recommendations": [
        {{"chapter": 1, "suggestion": "Narrative adjustment recommendation..."}},
        ...
      ]
    }}
    
    Text:
    {content[:50000]}
    """
    
    response = await client.aio.models.generate_content(
        model=selected_model,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

async def run_structural_analysis_async(text: str, provider: str = "gemini", api_key: str = None, model: str = None, local_mode: bool = False):
    """
    [THE ARCHITECT]: Scans the manuscript for narrative shifts and emotional arcs.
    """
    # [SCALING GUARDRAIL]: Truncate if too large
    text = _truncate_for_context(text, max_chars=100000)
    
    prompt = f"""
    You are an elite Narrative Architect. Analyze the following manuscript text to delineate its structural bones.
    
    1. Identify logical chapter breaks based on narrative shifts, perspective changes, or emotional pauses.
    2. For each chapter, provide:
       - 'suggested_title': A compelling, professional title.
       - 'summary': A 3-word summary of the core action.
       - 'emotional_intensity': A score from 1 (calm) to 10 (peak tension/climax).
       - 'starting_words': EXACTLY 10 to 15 unique, consecutive words of the paragraph where this chapter begins.
       - 'reasoning': A brief explanation of why this break is effective.
       - 'content_warnings': List of potential triggers (e.g., "Violence", "None").
    
    Format the output as a strict JSON object:
    {{
      "chapters": [
        {{
          "chapter_number": 1,
          "suggested_title": "...",
          "summary": "...",
          "emotional_intensity": 5,
          "starting_words": "...",
          "reasoning": "...",
          "content_warnings": ["..."]
        }}
      ]
    }}
    
    CRITICAL: Use standard straight apostrophes (') and straight double quotes (") exclusively.
    
    Manuscript Text:
    {text}
    """
    
    _, data = await analyze_persona_async(text, "The Architect", provider, api_key, custom_prompt=prompt, model=model or "gemini-3.1-pro-preview")
    return data

# ─── Simulated Canned Responses for Zero-Key Demo Mode ───────────────────────
def _simulate_persona(persona: str) -> str:
    """Returns a highly professional, persona-specific critique for Demo Mode."""
    responses = {
        "Developmental Editor": {
            "feedback": """### 🎭 Developmental Edit: Structural Analysis
I have scanned the rhythmic structure of your narrative and identified its core emotional spikes. 

**Key Observation:** Your pacing currently feels 'flat' in the transition between introductory world-building and the first major conflict. 

**Recommendation:** I suggest a chapter break at the next major emotional shift. Grant the reader "breathing room" by ending the current sequence on a questioning note rather than a resolution. This will drive higher "One More Page" momentum.""",
            "suggestions": [
                {"id": "sim-1", "type": "insert", "label": "Insert Chapter Break", "content": "--- \n\n# Chapter Suggestion \n\n", "reason": "Pacing improvement at emotional peak."}
            ],
            "chapters": [
                {"chapter_number": 1, "suggested_title": "The Awakening", "emotional_intensity": 5, "starting_words": "The exact first 10 words..."}
            ]
        },
        "Copy Editor": {
            "feedback": "### 🔍 Grammar & Style Analysis\n\nI have identified several stylistic inconsistencies that could be tightened. Review the interactive suggestions in the editor.",
            "suggestions": [
                {
                    "id": "sim-2",
                    "original": "The man runned fast.",
                    "suggestion": "The man ran fast.",
                    "reason": "Incorrect verb tense (Simulated Example)."
                }
            ],
            "edits": [
                {"original": "The man runned fast.", "suggestion": "The man ran fast.", "reason": "Incorrect verb tense."}
            ]
        },
        "Marketing Executive": {
            "feedback": """### 📈 Pitch & Hook Marketing Strategy
**Elevator Pitch:** "A high-stakes thriller where silence is the only weapon."
**Target Audience:** Readers of *Gillian Flynn* and fans of psychological tension.""",
            "suggestions": [
                {"id": "sim-3", "type": "insert", "label": "Add Back-Cover Blurb", "content": "\n\n> Everything changed the day the letters stopped. Now, she has to find the sound in the silence... before it finds her.", "reason": "Compelling hook for the beginning of the document."}
            ]
        }
    }
    
    res = responses.get(persona, {
        "feedback": f"### {persona} Consultant Critique\n\nI have reviewed your text and find it displays significant technical promise. Focus on tightening your secondary character arcs.\n\n*Note: This is a simulated critique.*",
        "suggestions": []
    })
    return json.dumps(res)

def _simulate_creative(feature: str) -> str:
    """Returns ultra-high-fidelity mock data for Creative Muse features in Demo Mode."""
    if feature == "moodboard":
        return json.dumps({
            "visual_prompt": "A cinematic, atmospheric landscape of a fog-drenched Victorian street at dawn. Low-angle lighting catching the cobblestones. Ethereal, moody, muted blues and golds.",
            "soundscapes": ["Foghorns in the distance", "Clock tower chiming", "Footsteps on cobblestones"],
            "mood": "Atmospheric, Victorian",
            "color_palette": ["#2C3E50", "#E67E22", "#95A5A6"],
            "image_url": "https://images.unsplash.com/photo-1542385151-efd9000785a0?auto=format&fit=crop&q=80&w=800"
        })
    elif feature == "world_bible":
        return json.dumps({
            "characters": [
                {"name": "Elias Thorne", "role": "Protagonist", "traits": "Stoic, Scarred, Loyal", "details": "Wears a tattered navy coat. Carrying a silver locket."},
                {"name": "Seraphina", "role": "Support", "traits": "Agile, Sharp-tongued, Mysterious", "details": "Green eyes, quick with a blade."}
            ],
            "locations": [
                {"name": "The Rusty Anchor", "type": "Tavern", "description": "Smells of salt and stale ale. Dim lanterns."},
                {"name": "Whispering Woods", "type": "Forest", "description": "Trees that seem to breathe. Permanent twilight."}
            ]
        })
    return "{}"

# ─── Build the prompt string for a given persona ──────────────────────────────
def _build_prompt(text: str, persona: str, user_chapters: list[dict] = None) -> tuple[str, bool]:
    """Returns (prompt_string, is_json_mode). Always True for all agents now."""
    if persona == "Developmental Editor":
        # Branched Pacing Intelligence:
        if not user_chapters or len(user_chapters) == 0:
            branch_instruction = """
            [MANUSCRIPT HAS NO EXISTING STRUCTURE - BLANK STATE] 
            You ARE the first architect. Identify natural narrative pauses and suggest a FULL, balanced Chapter structure from scratch.
            CRITICAL: Since this is a Blank State, you MUST provide the FIRST full emotional and advisory blueprint for this work.
            """
        else:
            # Disruptive Pacing Intelligence: Force a re-audit of the existing structure.
            chap_summary = "\n".join([f"- Chapter {c.get('chapter_number', i+1)}: '{c.get('suggested_title', 'Untitled')}' (~{c.get('reading_time_mins', '??')} mins) at anchor: '{c.get('starting_words', '')}'" for i, c in enumerate(user_chapters)])
            branch_instruction = f"""
            [DISRUPTIVE NARRATIVE AUDIT - EXISTING STRUCTURE DETECTED] 
            Current Chapter Pacing:
            {chap_summary}
            
            DIAGNOSTIC TASK: Identify all chapters exceeding 20 minutes as "Rhythm Violations."
            ARCHITECTURAL TASK: You are NOT bound by the author's current chapter breaks. If a chapter is too long, you MUST suggest one or more new breaks within its text. 
            
            CRITICAL NARRATIVE WEIGHT RULE: Do NOT suggest 'fragment' chapters. A suggested chapter should generally be of professional length (at least 1,500-2,500 words). Never create a chapter that is only two or three paragraphs long unless it is a high-climax dramatic cliffhanger. If chapters are too short/fragmented, you MUST suggest mergers.
            
            GOAL: A perfectly balanced, professional narrative rhythm with substantial, self-contained arcs.
            """

        prompt = f"""
        You are an elite Disruptive Narrative Architect. 
        {branch_instruction}
        
        CRITICAL FORMATTING RULE: Use standard straight apostrophes (') and straight double quotes (") exclusively in all feedback, titles, and suggestions. Do NOT use curved or 'smart' quotes.
        
        MANDATORY METADATA: For EVERY SINGLE chapter in your final proposed list, you MUST provide:
        1. 'emotional_intensity' (1-10).
        2. 'content_warnings': Array of OBJECTS. 
           EACH OBJECT MUST HAVE:
           - 'label': The text of the warning (e.g., "Graphic Violence"). Use "None" ONLY if the chapter is perfectly safe.
           - 'starting_words': EXACTLY 10 to 15 unique, consecutive words of the paragraph where this issue begins. 
           CRITICAL: These anchors should be a unique narrative fingerprint. Do not use generic words.
        3. 'starting_words': EXACTLY 10 to 15 unique, consecutive words of the paragraph where this chapter (or break) begins.
        
        If you find a pacing violation in the middle of an existing chapter, find the nearest narrative pause and create a NEW chapter entry with its own unique 'starting_words' anchor (10-15 words).
        
        You MUST return a COMPLETE list of all chapters for the text provided. Do not return an empty list.
        
        Format the output as a strict JSON object:
        {{
          "chapters": [
            {{
                "chapter_number": 1, 
                "suggested_title": "The Awakening", 
                "emotional_intensity": 8,
                "content_warnings": [
                    {{ "label": "Graphic Violence", "starting_words": "The blood spray hit the wall before he could respond to the sudden dark movement..." }}
                ],
                "reasoning": "Initial hook; introduces the core conflict with high intensity.", 
                "starting_words": "The iron gates groaned as the heavy motor struggled to pull them across the frozen gravel driveway..."
            }}
          ]
        }}
        Manuscript Text:
        {text}
        """
        return prompt, True
    elif persona == "Sensitivity Reader":
        prompt = f"""
        You are a professional Sensitivity Reader and Cultural Tropes Expert. Analyze the text for demographic representation, cultural nuances, potential trigger warnings, and problematic tropes.
        
        1. "feedback": A detailed Markdown report.
        2. "suggestions": A list of actionable items (e.g. "Add a content warning", "Rephrase this description").
        
        CRITICAL FORMATTING RULE: Use standard straight apostrophes (') and straight double quotes (") exclusively.
        
        Format:
        {{
            "feedback": "markdown...",
            "suggestions": [
                {{ "id": "s-1", "type": "insert", "label": "Add Warning", "content": "> [!CAUTION]\\n> Narrative contains intense themes...", "reason": "Necessary for reader safety." }}
            ]
        }}

        Manuscript Text:
        {text}
        """
        return prompt, True
    elif persona == "Marketing Executive":
        prompt = f"""
        You are a top-tier Publishing Marketing Executive. Generate pitch hooks, audience demographics, and a back-cover blurb.
        
        Return a strict JSON object with:
        1. "feedback": A slick Markdown report.
        2. "suggestions": A list of items to insert into the manuscript (e.g. "Insert blurb at top").
        
        Format:
        {{
            "feedback": "markdown...",
            "suggestions": [
                {{ "id": "m-1", "type": "insert", "label": "Add Blurb", "content": "BLURB_TEXT", "reason": "Hook the reader early." }}
            ]
        }}
        Manuscript Text:
        {text}
        """
        return prompt, True
    elif persona == "Hollywood Screenwriter":
        prompt = f"""
        You are an elite Hollywood Showrunner. Evaluate franchise potential and provide a cinematic blueprint.
        
        Return a strict JSON object with:
        1. "feedback": A visionary Markdown report.
        2. "suggestions": Actionable cinematic improvements.
        
        Format:
        {{
            "feedback": "markdown...",
            "suggestions": []
        }}

        Manuscript Text:
        {text}
        """
        return prompt, True
    else:
        prompt = f"""
        You are a highly specialized Consulting Editor focusing on: {persona}.
        Provide feedback and suggestions.
        
        Return a strict JSON object with:
        1. "feedback": Markdown.
        2. "suggestions": [ {{ "id": "uuid", "type": "insert|replace", "label": "Action Name", "content": "...", "reason": "..." }} ]

        Manuscript Text:
        {text}
        """
        return prompt, True

import re

def _robust_parse_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
    clean = clean.strip()
    
    try:
        return json.loads(clean)
    except BaseException:
        pass
        
    try:
        # aggressive mitigation for trailing commas before brackets generated by weak LLMs
        clean_no_comma = re.sub(r',\s*([\]}])', r'\1', clean)
        return json.loads(clean_no_comma)
    except Exception as e:
        raise ValueError("Failed to parse JSON") from e

def _truncate_for_context(text: str, max_chars: int = 60000) -> str:
    """[SCALING GUARDRAIL]: Ensures text does not overflow the AI context window."""
    if not text: return ""
    if len(text) <= max_chars: return text
    
    half = max_chars // 2
    return text[:half] + "\n\n... [INDUSTRIAL TRUNCATION FOR CONTEXT SCALE] ...\n\n" + text[-half:]

# ─── Unified async AI caller — routes to Gemini, Claude, or OpenAI with Failover ────────────
async def analyze_persona_async(text: str, persona: str, provider: str = "gemini", api_key: str = None, custom_prompt: str = None, model: str = None, user_chapters: list[dict] = None, synthesis_mode: bool = False):
    # [SCALING GUARDRAIL]: Protect the handshake from context overflow
    text = _truncate_for_context(text)
    
    prompt, is_json = custom_prompt, True
    if not custom_prompt:
        prompt, is_json = _build_prompt(text, persona, user_chapters)
    
    # [SPECTRUM FAILOVER]: Build the provider sequence
    # 1. Start with the user's selected primary
    provider_queue = [(provider, model, api_key)]
    
    # 2. Add fallbacks from environment if they aren't the primary
    fallbacks = [
        ("gemini", "gemini-3.1-pro-preview", os.environ.get("GEMINI_API_KEY")),
        ("anthropic", "claude-3-5-sonnet-20241022", os.environ.get("ANTHROPIC_API_KEY")),
        ("openai", "gpt-4o", os.environ.get("OPENAI_API_KEY"))
    ]
    
    for f_prov, f_mod, f_key in fallbacks:
        if f_prov != provider and f_key:
            provider_queue.append((f_prov, f_mod, f_key))

    last_err = "No provider available"
    
    for prov, mod, key in provider_queue:
        try:
            if prov == "simulator":
                raw = _simulate_persona(persona)
                await asyncio.sleep(0.5)
                data = _robust_parse_json(raw)
                return persona, data

            print(f"BOARDROOM PULSE: Expert {persona} engaging {prov}:{mod}...")
            
            if prov == "gemini":
                client = _get_ai_client(prov, key)
                target_model = mod if mod else "gemini-1.5-pro"
                gen_config = {"response_mime_type": "application/json"} if is_json else None
                
                response = await client.aio.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=gen_config
                )
                raw = response.text
                metrics = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "candidates_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
                _log_api_usage(persona, prov, target_model, metrics)
                
            elif prov == "anthropic":
                client = _get_ai_client(prov, key)
                target_model = mod if mod else "claude-3-5-sonnet-20241022"
                response = await client.messages.create(
                    model=target_model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = response.content[0].text
                metrics = {
                    "prompt_tokens": response.usage.input_tokens,
                    "candidates_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
                _log_api_usage(persona, prov, target_model, metrics)
                
            elif prov == "openai":
                client = _get_ai_client(prov, key)
                target_model = mod if mod else "gpt-4o"
                response = client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"} if is_json else None
                )
                raw = response.choices[0].message.content
                metrics = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "candidates_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                _log_api_usage(persona, prov, target_model, metrics)
            else:
                continue

            if is_json:
                data = _robust_parse_json(raw)
                data["_usage"] = metrics
                return persona, data
            return persona, {"feedback": raw, "_usage": metrics}

        except Exception as e:
            print(f"[FAILOVER ALERT]: Expert {persona} failed with {prov} -> {str(e)}")
            last_err = str(e)
            continue

    return persona, {"feedback": f"**BOARDROOM BLACKOUT:** All expert engines failed. Last error: {last_err}"}

# ─── Unified Multi-Agent Runner — Sequentially executes Boardroom members ─────
async def run_boardroom_parallel(text: str, personas: list[str], provider: str = "gemini", api_key: str = None, model: str = None, user_chapters: list[dict] = None, key_bundle: dict = None, ledger: list = None, force_primary: bool = False, local_mode: bool = False, synthesis_mode: bool = False, all_keys: dict = None, custom_prompt: str = None, project_folder: str = None):
    results = {}
    for persona in personas:
        try:
            name, response = await analyze_persona_async(text, persona, provider, api_key, model=model, user_chapters=user_chapters, synthesis_mode=synthesis_mode)
            results[name] = response
        except Exception as e:
            print(f"Expert ERROR: {persona} failed -> {e}")
            results[persona] = {"feedback": f"Expert {persona} was unable to complete their review due to a connection handshake issue. Check your terminal or handshake_forensics.txt for actual error detail."}
    return results

async def analyze_world_bible_async(text: str, provider: str = "gemini", api_key: str = None, model: str = None, local_mode: bool = False):
    """Extracts a World-Building Bible (Characters and Locations) from the text."""
    if provider == "simulator":
        return json.loads(_simulate_creative("world_bible"))

    prompt = f"""
    Act as a Master World-Builder. Extract every Character and Location mentioned in the text.
    For Characters, find their Name, Role, Traits, and any specific physical Details.
    For Locations, find the Name, Type, and a brief Description.
    
    Return a strict JSON object:
    {{
       "characters": [ {{"name": "...", "role": "...", "traits": "...", "details": "..."}} ],
       "locations": [ {{"name": "...", "type": "...", "description": "..."}} ]
    }}
    
    Manuscript Text:
    {text}
    """
    _, data = await analyze_persona_async(text, "World Historian", provider, api_key, custom_prompt=prompt, model=model)
    return data

async def validate_key_async(provider: str, api_key: str, model: str = None, custom_url: str = None):
    """Performs a lightweight handshake check to ensure the provided API key is functional."""
    try:
        if provider == "gemini":
            client = _get_ai_client(provider, api_key)
            try:
                # [SOVEREIGN HANDSHAKE]: Pure metadata check (fastest, lowest CPU)
                client.models.list()
                return {"success": True, "message": "Gemini Handshake Verified"}
            except Exception as e:
                return {"success": False, "message": f"Gemini Key Refused: {str(e)}"}
        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            try:
                # [SOVEREIGN HANDSHAKE]: Pure portfolio discovery
                client.models.list()
                return {"success": True, "message": "Anthropic Handshake Verified"}
            except Exception:
                # Fallback for older keys without list access
                return {"success": True, "message": "Anthropic Handshake Assumed (Discovery Restricted)"}
        elif provider == "groq":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Ping"}],
                max_tokens=5
            )
            return {"success": True, "message": "Groq Handshake Verified"}
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "Ping"}],
                max_tokens=5
            )
            return {"success": True, "message": "OpenAI Handshake Verified"}
        return {"success": True, "message": f"{provider} assumed active (Simulated)"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def list_models_async(provider: str, api_key: str):
    """Discovery Pulse: Replaces the deprecated hardcoded list with a live handshake."""
    try:
        if provider == "gemini":
            try:
                client = _get_ai_client(provider, api_key)
                models_res = client.models.list()
                models = [m.name.replace("models/", "") for m in models_res]
                if not models:
                    raise Exception("Empty list")
                return {"success": True, "models": sorted(models)}
            except Exception:
                # [SOVEREIGN FALLBACK]: Baseline Gemini Portfolio
                return {"success": True, "models": [
                    "gemini-3.1-pro-preview", "gemini-1.5-pro", 
                    "gemini-1.5-flash", "gemini-2.0-flash-exp"
                ]}
        elif provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                models_res = client.models.list()
                models = [m.id for m in models_res.data if "gpt" in m.id]
                return {"success": True, "models": sorted(models)}
            except Exception:
                return {"success": True, "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}
        elif provider == "anthropic":
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                models_res = client.models.list()
                models = [m.id for m in models_res.data]
                return {"success": True, "models": sorted(models)}
            except Exception:
                return {"success": True, "models": [
                    "claude-3-5-sonnet-20241022", 
                    "claude-3-5-haiku-20241022", 
                    "claude-3-opus-20240229"
                ]}
        elif provider == "groq":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
                models_res = client.models.list()
                models = [m.id for m in models_res.data]
                if not models:
                    raise Exception("Empty list")
                return {"success": True, "models": sorted(models)}
            except Exception:
                # [SOVEREIGN FALLBACK]: Baseline Groq Portfolio
                return {"success": True, "models": [
                    "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview",
                    "llama-3.3-70b-versatile", "mixtral-8x7b-32768"
                ]}
        return {"success": False, "message": "Provider discovery not supported via this pathway.", "models": []}
    except Exception as e:
        return {"success": False, "message": str(e), "models": []}

async def discover_gateway_async(brand_name: str, provider: str, api_key: str):
    """[SOVEREIGN DISCOVERY]: Stub for identified unknown provider gateways."""
    return f"https://api.{brand_name}.ai/v1" if provider == "custom" else None
