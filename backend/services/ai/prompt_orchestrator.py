from .specialist_registry import get_specialist_config
from typing import Tuple, List, Dict

def build_industrial_prompt(text: str, persona: str, user_chapters: List[Dict] = None) -> Tuple[str, bool, str]:
    """
    [PROMPT ORCHESTRATOR]: The bridge between the registry and the gateway.
    Handles dynamic logic (like pacing branch) and returns (prompt, is_json, role).
    """
    config = get_specialist_config(persona)
    template = config["template"]
    
    # 1. Specialized Branching Logic (extracted from legacy)
    branch_instruction = ""
    if persona == "Developmental Editor":
        if not user_chapters or len(user_chapters) == 0:
            branch_instruction = """
            [MANUSCRIPT HAS NO EXISTING STRUCTURE - BLANK STATE] 
            You ARE the first architect. Identify natural narrative pauses and suggest a FULL, balanced Chapter structure from scratch.
            """
        else:
            chap_summary = "\n".join([f"- Chapter {c.get('chapter_number', i+1)}: '{c.get('suggested_title', 'Untitled')}'" for i, c in enumerate(user_chapters)])
            branch_instruction = f"""
            [DISRUPTIVE NARRATIVE AUDIT - EXISTING STRUCTURE DETECTED] 
            Current Chapter Pacing: {chap_summary}
            DIAGNOSTIC TASK: Identify all chapters exceeding 20 minutes as 'Rhythm Violations.'
            ARCHITECTURAL TASK: You are NOT bound by the author's current chapter breaks. If a chapter is too long, suggest new breaks.
            """
            
    # 2. Template Injection
    # Truncate text to stay within safe context limits for the specific specialist
    safe_text = text[:30000] if persona == "Developmental Editor" else text[:15000]
    
    prompt = template.format(
        text=safe_text, 
        branch_instruction=branch_instruction,
        persona=persona
    )
    
    return prompt, config["is_json"], config["role"]
