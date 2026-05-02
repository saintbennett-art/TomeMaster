import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

def forensic_31_handshake():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    target_models = [
        "gemini-3.1-flash-live-preview",
        "deep-research-pro-preview-12-2025"
    ]
    
    print("--- 3.1 ERA HANDSHAKE INITIATED ---")
    for model_id in target_models:
        try:
            full_id = f"models/{model_id}" if not model_id.startswith("models/") else model_id
            # Using the correct SDK method for model retrieval
            model_info = client.models.get(model=full_id)
            print(f"VERIFIED: {model_id} - STATUS: ACTIVE (Tome-Master Authorized)")
        except Exception as e:
            print(f"COLLISION: {model_id} - ERROR: {str(e)}")

if __name__ == "__main__":
    forensic_31_handshake()
