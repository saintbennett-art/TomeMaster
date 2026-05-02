import json

def get_best_model_for_expert(persona, discovered):
    id_persona = persona.lower()
    if any(k in id_persona for k in ['narratologist', 'complex']):
        res = [m for m in discovered if 'deep-research' in m] or [m for m in discovered if '3.1-pro' in m]
        return res[0] if res else (discovered[0] if discovered else None)
    
    if any(k in id_persona for k in ['prose', 'stylist', 'voice']):
        res = [m for m in discovered if 'claude-3-5' in m] or [m for m in discovered if 'gpt-4o' in m]
        return res[0] if res else (discovered[0] if discovered else None)
        
    if any(k in id_persona for k in ['structural', 'arc', 'pacing']):
        res = [m for m in discovered if '3.1-pro' in m] or [m for m in discovered if '1.5-pro' in m]
        return res[0] if res else (discovered[0] if discovered else None)
        
    return [m for m in discovered if 'pro' in m][0] if [m for m in discovered if 'pro' in m] else (discovered[0] if discovered else None)

def run_mapping_proof():
    # DISCOVERED PORTFOLIO (From Step 172 Discovery Pulse)
    discovered_portfolio = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3.1-pro-preview",
        "deep-research-pro-preview-12-2025",
        "gemini-3.1-flash-live-preview",
        "gpt-4o",
        "claude-3-5-sonnet-latest"
    ]
    
    specialists = [
        "The Narratologist (Deep Theme Discovery)",
        "The Prose Stylist (Flow & Cadence)",
        "The Structural Lead (Pacing & Arc)",
        "General Board Member"
    ]
    
    print("--- [INITIATING INTELLIGENCE MAPPING PROOF] ---")
    for s in specialists:
        mapping = get_best_model_for_expert(s, discovered_portfolio)
        print(f"SPECIALIST: {s}")
        print(f"COORDINATED ENGINE: {mapping}")
        print("-" * 10)

if __name__ == "__main__":
    run_mapping_proof()
