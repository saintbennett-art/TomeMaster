import os
from google import genai
from dotenv import load_dotenv

def discovery():
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print("--- SOVEREIGN DISCOVERY PULSE [SYNC / APRIL 2026] ---")
    try:
        # [BLOCKING DISCOVERY]: Forcing an immediate response
        models = client.models.list()
        for m in models:
            print(f"AUTHORIZED IDENTIFIER: {m.name}")
    except Exception as e:
        print(f"DISCOVERY FAILURE: {e}")

if __name__ == "__main__":
    discovery()
