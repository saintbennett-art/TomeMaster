import asyncio
import sys
import os

# Add parent dir to sys.path for service imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import analyze_persona_async

async def run_audit():
    print("SOVEREIGN SYSTEM AUDIT: Initiating deepshake probe...")
    print("Target: gemma4:e2b @ 127.0.0.1:11434")
    
    test_text = "Tome-Master verification protocol. Probing local expert capabilities."
    persona = "Developmental Editor"
    
    try:
        # Targeting the user's actual displacement-optimized model
        persona_name, response = await analyze_persona_async(
            text=test_text,
            persona=persona,
            provider="ollama",
            model="gemma4:e2b"
        )
        
        if "feedback" in response and "Handshake failure" in response["feedback"]:
            print(f"ERROR: AUDIT FAILED: Handshake collision detected.\n{response['feedback']}")
            sys.exit(1)
            
        print("SUCCESS: AUDIT COMPLETE: Boardroom expert handshaking established.")
        print(f"Intelligence: {response.get('_actual_provider', 'unknown')}")
        sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: AUDIT CRITICAL FAILURE: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_audit())
