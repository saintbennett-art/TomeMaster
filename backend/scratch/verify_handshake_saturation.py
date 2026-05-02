import sys
import os
import time

# Align with backend logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from google import genai
from services import ai_service

def test_optimized_validation():
    # Retrieve key from user's vault safely
    api_key = os.environ.get("GOOGLE_API_KEY") # Simulation uses local env for safety
    if not api_key:
        print("[SKIP]: No API key detected in environment for simulation.")
        return

    print("--- [STARTING OPTIMIZED HANDSHAKE] ---")
    start_time = time.time()
    
    try:
        # Optimized Logic: Lightweight list check instead of full model retrieval
        client = genai.Client(api_key=api_key)
        # We only need to see IF we can list, not retrieve full metadata
        models = list(client.models.list(config={'page_size': 1}))
        
        duration = time.time() - start_time
        print(f"[SUCCESS]: Handshake resolved in {duration:.2f}s.")
        print(f"Top Model Identified: {models[0].name}")
    except Exception as e:
        duration = time.time() - start_time
        print(f"[FAILURE]: Handshake stalled after {duration:.2f}s.")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_optimized_validation()
