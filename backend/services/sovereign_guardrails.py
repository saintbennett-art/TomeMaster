import re

# --- SOVEREIGN GUARDRAILS: ANTIGRAVITY AGENTIC PROTOCOL ---
SOVEREIGN_GUARDRAIL = """
DIRECTIVE: You are an elite, highly-specialized Sovereign Consultant and Narrative Architect.
1. ABSOLUTE AUTONOMY: Focus entirely on the manuscript. Do not preface, conclude, or apologize.
2. AGENTIC PRECISION: Use high-fidelity technical terminology appropriate for your specialty.
3. ZERO FANTASY: Do not speculate beyond the provided text. Adhere 100% to authorial intent.
4. STRUCTURAL INTEGRITY: If asked for JSON, your technical output must be mathematically valid and valid JSON.
5. NO META-NARRATIVE: No "Certainly!", "Based on the text...", or "I hope this helps".
6. CHAIN OF THOUGHT: If you are a reasoning model, maintain a deep, rigorous internal audit in <thought> tags before your final response.
"""

# --- INTELLIGENCE ERA GUARDRAIL: APRIL 2026 EDITION ---
# Mandatory anchors to prevent architectural regression
INTELLIGENCE_ERA_GUARDRAIL = {
    "GEMINI_MANDATE": "gemini-3.1-pro-preview",
    "CLAUDE_MANDATE": "claude-4.6-sonnet-thinking",
    "GPT_MANDATE": "gpt-4o",
    "FORBIDDEN_VERSIONS": ["1.0", "1.5", "2.0"]
}

def enforce_current_intelligence(model_id: str) -> str:
    """
    Programmatic Guardrail: Intercepts and upgrades legacy or experimental model IDs 
    to match the current production-grade standard. 
    Authorized Sovereign Eras: 3.1, 2.5, 2.1.
    """
    if not model_id: return INTELLIGENCE_ERA_GUARDRAIL["GEMINI_MANDATE"]
    
    mid = model_id.lower()
    
    # [PROTOCOL CHECK]: Resolve Sovereign Quota Tiers to API Identifiers
    if "gemini" in mid:
        # [SOVEREIGN MAPPING]: Map 3.1 / 2.5 / 2.1 series to Production Snapshots
        if "3.1-pro-high" in mid: return "gemini-3.1-pro-preview"
        if "3.1-pro-low" in mid: return "gemini-3.1-pro-preview" 
        if "3-flash" in mid: return "gemini-3-flash-preview"
        if "2.5-pro" in mid: return "gemini-2.5-pro"
        if "2.1-pro" in mid: return "gemini-2.1-pro"
        if "deep-research" in mid: return "deep-research-pro-preview-12-2025"
            
        # [ERA BLOCKADE]: Force upgrade for any forbidden legacy cores
        if any(v in mid for v in INTELLIGENCE_ERA_GUARDRAIL["FORBIDDEN_VERSIONS"]) and "flash" not in mid:
            return INTELLIGENCE_ERA_GUARDRAIL["GEMINI_MANDATE"]
            
    # [PROTOCOL CHECK]: Upgrade legacy Claude architectures
    if "claude" in mid:
        if "4.6-sonnet-thinking" in mid: return "claude-4.6-sonnet-thinking"
        if any(v in mid for v in ["instant", "2.0", "2.1", "3-haiku", "20240620"]):
            return INTELLIGENCE_ERA_GUARDRAIL["CLAUDE_MANDATE"]
            
    # [PROTOCOL CHECK]: Upgrade legacy GPT architectures
    if "gpt" in mid:
        if any(v in mid for v in ["3.5", "4-0613", "4-32k"]):
            return INTELLIGENCE_ERA_GUARDRAIL["GPT_MANDATE"]
            
    return model_id

def sanitize_expert_response(text: str) -> str:
    """Systemic Sanitization: Strips AI Meta-Commentary, Junk Talk, and handles thought blocks."""
    # Remove obvious AI junk talk
    junk_patterns = [
        r"^Certainly!.*?\n",
        r"^Here is the analysis.*?\n",
        r"^As an AI language model.*?\n",
        r"^I am happy to help.*?\n",
        r"Hopefully this helps!.*$",
        r"Let me know if you need more assistance.*$"
    ]
    cleaned = text
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    return cleaned.strip()
