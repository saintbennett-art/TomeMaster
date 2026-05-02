
import asyncio
import os
import json
from services import ai_service
from dotenv import load_dotenv

async def simulate_boardroom():
    load_dotenv(override=True)
    print("--- LIVE BOARDROOM SIMULATION [FORENSIC] ---")
    
    # We use a real persona and a real (small) text
    text = "It was a snowy Christmas Eve. The fire crackled in the hearth."
    personas = ["Developmental Editor"]
    api_key = os.environ.get("GEMINI_API_KEY")
    
    print(f"SIMULATION: Handshaking with {personas} using Apex Engine...")
    try:
        results = await ai_service.run_boardroom(text, personas, "gemini", api_key, model="auto")
        print("\nSIMULATION RESULT:")
        print(json.dumps(results, indent=2))
        
        # Check if the result contains the error message
        feedback = results.get("Developmental Editor", {}).get("feedback", "")
        if "handshake issue" in feedback:
            print("\n!!!! SIMULATION CAPTURED THE ERROR !!!!")
        else:
            print("\n++++ SIMULATION SUCCESS: Connection is clean in Python ++++")
            
    except Exception as e:
        print(f"\n!!!! SIMULATION CRASHED: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_boardroom())
