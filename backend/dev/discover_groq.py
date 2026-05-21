import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def discover_groq_models():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("No GROQ_API_KEY found in .env")
        return

    print(f"Checking Groq Portfolio for key: {api_key[:10]}...")
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        models_res = client.models.list()
        print(f"Success! {len(models_res.data)} models found.")
        for m in models_res.data:
            print(f"- {m.id}")
    except Exception as e:
        print(f"Groq Handshake Failed: {str(e)}")

if __name__ == "__main__":
    discover_groq_models()
