import asyncio
import os
import json
import time
from datetime import datetime
from services.ai_service import run_boardroom_parallel
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── THE BENCHMARK MANUSCRIPT: NARRATIVE ANCHOR ──────────────────────────────
SAMPLE_TEXT = """
The rain didn't just fall in Sector 9; it dissolved things. It ate the chrome off the hover-cabs and turned the neon signs into bleeding watercolors. Elias stood under a rusted awning, his cybernetic eye clicking as it tried to compensate for the interference. 

"You're late," a voice rasped from the shadows. 

Elias didn't look. He knew that voice—the sound of gravel in a blender. It was Kaelen, the only man in the sprawl who still used a physical heart. 

"The atmospheric scrubbers are down again," Elias replied, his voice flat. "The air is 40% lead. I had to take the long way through the tunnels."

Kaelen stepped into the dim light. His coat was stained with ozone and old regrets. He handed Elias a data-chip. "The Boardroom wants this analyzed. Every character, every location, every hidden tremor in the plot. If we miss a single detail, the whole sector sinks."
"""

# ─── BOARDROOM CANDIDATES ────────────────────────────────────────────────────
TEST_MATRIX = [
    {"provider": "gemini", "model": "gemini-3.1-pro-preview", "label": "GEMINI_3.1_PRO"},
    {"provider": "gemini", "model": "gemini-2.5-pro", "label": "GEMINI_2.5_PRO"},
    {"provider": "gemini", "model": "gemini-2.1-pro", "label": "GEMINI_2.1_PRO"},
    {"provider": "gemini", "model": "gemini-3-flash-preview", "label": "GEMINI_3_FLASH"},
    {"provider": "openai", "model": "gpt-4o", "label": "GPT_4O"},
    # Local Mode candidates (Assumes Ollama is running)
    {"provider": "ollama", "model": "deepseek-r1:8b", "label": "LOCAL_DEEPSEEK_R1_8B"},
    {"provider": "ollama", "model": "gemma:2b", "label": "LOCAL_GEMMA_2B"}
]

AUDIT_DIR = f"./boardroom_audits_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

async def run_audit_bench():
    """
    Automated Boardroom First-Pass: 
    Dispatches a consistent narrative audit to every authorized model in the portfolio.
    Evaluates JSON fidelity, response time, and narrative depth.
    """
    print("\n[INITIATING BOARDROOM STRESS TEST...]")
    print(f"Targeting {len(TEST_MATRIX)} models. Results will be saved to: {AUDIT_DIR}")
    
    if not os.path.exists(AUDIT_DIR):
        os.makedirs(AUDIT_DIR)
        
    master_summary = []

    for test in TEST_MATRIX:
        print(f"\n[AUDITING]: {test['label']} ({test['model']})...")
        
        start_time = time.time()
        try:
            # We run a single specialist (Copy Editor) for speed, but use the full parallel engine
            results = await run_boardroom_parallel(
                content=SAMPLE_TEXT,
                requested_personas=["Copy Editor"],
                provider=test['provider'],
                model=test['model'],
                local_mode=(test['provider'] == 'ollama')
            )
            
            elapsed = time.time() - start_time
            report = results.get("Copy Editor", {})
            feedback = report.get("feedback", "BLACKOUT: No feedback received.")
            suggestions = report.get("suggestions", [])
            
            # Fidelity Checks
            is_json_valid = len(suggestions) > 0 or "_parsing_warning" not in report
            char_count = len(feedback)
            
            summary_entry = {
                "label": test['label'],
                "provider": test['provider'],
                "model": test['model'],
                "status": "SUCCESS" if char_count > 100 else "WEAK_SIGNAL",
                "duration": f"{elapsed:.2f}s",
                "length": char_count,
                "fidelity": "HIGH" if is_json_valid else "CORRUPT",
                "suggestions_count": len(suggestions)
            }
            master_summary.append(summary_entry)
            
            # Save Individual Report
            filename = f"{AUDIT_DIR}/{test['label']}_report.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# BOARDROOM AUDIT: {test['label']}\n")
                f.write(f"- **Provider:** {test['provider']}\n")
                f.write(f"- **Model:** {test['model']}\n")
                f.write(f"- **Duration:** {elapsed:.2f} seconds\n")
                f.write(f"- **Fidelity Score:** {summary_entry['fidelity']}\n")
                f.write(f"- **Suggestions Found:** {len(suggestions)}\n\n")
                f.write("## FEEDBACK\n")
                f.write(feedback)
                if suggestions:
                    f.write("\n\n## SUGGESTIONS\n")
                    f.write(json.dumps(suggestions, indent=2))
            
            print(f"  OK. Length: {char_count} chars. Time: {elapsed:.2f}s")
            
        except Exception as e:
            print(f"  FAILURE: {str(e)}")
            master_summary.append({
                "label": test['label'],
                "status": "FAILED",
                "error": str(e)
            })

    # Final Master Summary
    print("\n" + "="*50)
    print("BOARDROOM BENCHMARK SUMMARY")
    print("="*50)
    for s in master_summary:
        print(f"{s['label']:25} | {s['status']:8} | {s.get('duration', 'N/A'):6} | FID: {s.get('fidelity', 'N/A')}")
    
    with open(f"{AUDIT_DIR}/MASTER_SUMMARY.json", "w") as f:
        json.dump(master_summary, f, indent=2)
    
    print("\nAudit Complete. Please review the reports in the audit directory.")

if __name__ == "__main__":
    asyncio.run(run_audit_bench())
