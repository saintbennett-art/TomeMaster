import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

def find_gemini_models_v1beta():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FAILURE: No GEMINI_API_KEY.")
        return

    # Default (v1beta)
    client = genai.Client(api_key=api_key)
    print("SEARCHING MODELS (v1beta)...")
    try:
        models = list(client.models.list())
        for model in models:
            if "1.5-pro" in model.name or "1.5-flash" in model.name:
                print(f"FOUND (v1beta): {model.name}")
    except Exception as e:
        print(f"V1BETA SEARCH FAILURE: {e}")

    # Explicit v1
    client_v1 = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    print("\nSEARCHING MODELS (v1)...")
    try:
        models = list(client_v1.models.list())
        for model in models:
            if "1.5-pro" in model.name or "1.5-flash" in model.name:
                print(f"FOUND (v1): {model.name}")
    except Exception as e:
        print(f"V1 SEARCH FAILURE: {e}")

if __name__ == "__main__":
    find_gemini_models_v1beta()
