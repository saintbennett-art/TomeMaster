from .specialist_registry import get_specialist_config
from typing import Tuple, List, Dict

# [CRITIQUE INTENSITY]: one reusable tone directive applied across every persona.
# "balanced" is the prompt as authored (no directive) so default behavior is unchanged.
TONE_DIRECTIVES = {
    "soft": (
        "TONE DIRECTIVE - GENTLE: Be encouraging and diplomatic. Lead with genuine "
        "strengths, frame problems as opportunities, and use supportive language that "
        "protects the author's confidence. Stay honest, but soften the delivery."
    ),
    "hard": (
        "TONE DIRECTIVE - BLUNT: Be rigorous, direct, and exhaustive. Name every "
        "weakness plainly and hold the work to a top-tier professional standard. No "
        "flattery and no hedging - the author wants the unvarnished assessment."
    ),
}


def build_industrial_prompt(text: str, persona: str, user_chapters: List[Dict] = None,
                            intensity: str = "balanced") -> Tuple[str, bool, str]:
    """
    [PROMPT ORCHESTRATOR]: The bridge between the registry and the gateway.
    Handles dynamic logic (like pacing branch) and returns (prompt, is_json, role).
    `intensity` (soft|balanced|hard) prepends a tone directive that hardens or
    softens the critique without altering each persona's analytical job.
    """
    config = get_specialist_config(persona)
    template = config["template"]
    
    # 1. Specialized Branching Logic (extracted from legacy)
    # The chapter-pacing branch belongs to the Structural Architect (chapterization),
    # not the Developmental Editor critique.
    branch_instruction = ""
    if persona == "Structural Architect":
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
    safe_text = text[:30000] if persona in ("Developmental Editor", "Structural Architect") else text[:15000]
    
    prompt = template.format(
        text=safe_text,
        branch_instruction=branch_instruction,
        persona=persona
    )

    # 3. Tone shaping — prepend the harden/soften directive (no-op when balanced).
    directive = TONE_DIRECTIVES.get((intensity or "balanced").lower())
    if directive:
        prompt = f"{directive}\n\n{prompt}"

    return prompt, config["is_json"], config["role"]
