import os
import asyncio
from google import genai
from dotenv import load_dotenv
load_dotenv()

async def inspect_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print("Inspecting a 3.1 model object structure...")
    
    try:
        models = client.models.list()
        # Find any 3.1 model
        gemini_31 = next((m for m in models if "gemini-3.1" in m.name), None)
        if gemini_31:
            print(f"MODEL NAME: {gemini_31.name}")
            # Use dir() to see all attributes
            print(f"ATTRIBUTES: {dir(gemini_31)}")
            # If it's a dict-like or has a specific property
            if hasattr(gemini_31, 'supported_generation_methods'):
                print(f"METHODS (v1): {gemini_31.supported_generation_methods}")
            elif hasattr(gemini_31, 'supported_methods'):
                print(f"METHODS (v2): {gemini_31.supported_methods}")
            else:
                 print("Methods property not found. Printing raw object...")
                 print(gemini_31)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_model())
