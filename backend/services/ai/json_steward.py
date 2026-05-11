import json
import re

def robust_parse(raw: str) -> dict:
    """
    [JSON STEWARD]: Industrial-grade parser that handles markdown fencing, 
    trailing commas, and common LLM hallucinations.
    """
    if not raw:
        return {"feedback": "Empty response from gateway."}
        
    clean = raw.strip()
    
    # 1. Strip Markdown Fencing
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
    clean = clean.strip()
    
    try:
        return json.loads(clean)
    except Exception:
        # 2. Aggressive Mitigation: Strip trailing commas before closing brackets/braces
        clean_no_comma = re.sub(r',\s*([\]}])', r'\1', clean)
        try:
            return json.loads(clean_no_comma)
        except Exception as e:
            # 3. Last Resort: Return as plain feedback if it's not structural JSON
            print(f"STEWARD WARNING: Structural JSON parse failed: {e}")
            return {"feedback": raw}
