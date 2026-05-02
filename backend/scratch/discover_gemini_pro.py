import sys
import os

# Align with backend logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from google import genai

def list_gemini_models():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR]: No GOOGLE_API_KEY in environment.")
        return

    try:
        client = genai.Client(api_key=api_key)
        print("--- [AVAILABLE GEMINI PORTFOLIO] ---")
        for model in client.models.list():
            # Filtering for Pro/Flash/3.x tiers
            print(f"ID: {model.name} | Tier: {model.display_name}")
    except Exception as e:
        print(f"[DISCOVERY FAILURE]: {str(e)}")

if __name__ == "__main__":
    list_gemini_models()
