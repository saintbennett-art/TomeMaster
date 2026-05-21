import asyncio
import os
import json
from services.ai_service import analyze_persona_async
from services.sovereign_guardrails import enforce_current_intelligence
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── NARRATIVE PROMPT ────────────────────────────────────────────────────────
SAMPLE_TEXT = "The rain didn't just fall in Sector 9; it dissolved things. Elias stood under a rusted awning, his cybernetic eye clicking."

GEMINI_TIERS = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.1-pro",
    "gemini-1.5-pro-002"
]

async def audit_geminis():
    print(f"\n[INITIATING GEMINI PORTFOLIO AUDIT]")
    print(f"Key detected: {os.getenv('GEMINI_API_KEY')[:10]}...")
    
    for model_id in GEMINI_TIERS:
        print(f"\n--- TESTING: {model_id} ---")
        try:
            name, report = await analyze_persona_async(
                text=SAMPLE_TEXT,
                persona="Copy Editor",
                provider="gemini",
                model=model_id,
                api_key=os.getenv("GEMINI_API_KEY")
            )
            
            # Print the actual feedback so the user can verify
            print(f"STATUS: SUCCESS")
            print(f"FEEDBACK PREVIEW:\n{report.get('feedback', 'EMPTY')[:500]}...")
            print(f"SUGGESTIONS: {len(report.get('suggestions', []))} found.")
            
            # Save the full JSON for detailed inspection
            with open(f"audit_{model_id}.json", "w") as f:
                json.dump(report, f, indent=2)
                
        except Exception as e:
            print(f"STATUS: FAILED - {str(e)}")

if __name__ == "__main__":
    asyncio.run(audit_geminis())
