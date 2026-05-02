import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

def list_models_forensic():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FAILURE: No GEMINI_API_KEY found.")
        return

    client = genai.Client(api_key=api_key)
    print("PROBING AVAILABLE MODELS (FORENSIC)...")
    try:
        models = list(client.models.list())
        for model in models:
            # Just print the name and the type to see what we have
            print(f"MODEL NAME: {model.name}")
            # If it's a model we care about, let's look closer
            if "1.5-pro" in model.name or "1.5-flash" in model.name:
                print(f"  FULL OBJECT: {model}")
    except Exception as e:
        print(f"DISCOVERY FAILURE: {e}")

if __name__ == "__main__":
    list_models_forensic()
