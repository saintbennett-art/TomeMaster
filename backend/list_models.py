import os
import asyncio
from google import genai
from dotenv import load_dotenv
load_dotenv()

async def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print("Enumerating Gemini Models and their Capabilities...")
    
    try:
        # Check the SDK's model objects
        models = client.models.list()
        for m in models:
            # In the latest SDK, it might be 'supported_generation_methods' or similar
            # Printing the whole object to be 100% sure
            methods = getattr(m, 'supported_methods', 'Unknown')
            print(f"- NAME: {m.name}")
            print(f"  METHODS: {methods}")
    except Exception as e:
        print(f"FAILED TO LIST MODELS: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
