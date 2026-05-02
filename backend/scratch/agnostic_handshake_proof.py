import sys
import os
import asyncio
import time

# Align with backend logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from google import genai

from dotenv import load_dotenv
load_dotenv()

async def prove_agnostic_handshake():
    api_key = os.getenv("GEMINI_API_KEY") 
    
    print("--- [INITIATING AGNOSTIC HANDSHAKE PROOF] ---")
    start_time = time.time()
    
    try:
        client = genai.Client(api_key=api_key)
        # Rule Validation: Using model-agnostic list pulse with 60s saturation gate
        res = await asyncio.wait_for(client.aio.models.list(config={'page_size': 1}), timeout=60.0)
        
        duration = time.time() - start_time
        print(f"[SUCCESS]: Handshake resolved in {duration:.2f}s.")
        print(f"Message: Google Handshake active: Vault authorized.")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"[FAILURE]: Handshake stalled after {duration:.2f}s.")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(prove_agnostic_handshake())
