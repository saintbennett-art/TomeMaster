import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

async def diagnostic_handshake():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("CRITICAL: No GEMINI_API_KEY found.")
        return

    print(f"\n[INITIATING DIRECTORIAL HANDSHAKE AUDIT]")
    print(f"Key: {key[:10]}...")
    
    # We test both tiers to see where the credits reside
    targets = [
        "gemini-3.1-pro-preview",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    client = genai.Client(api_key=key)
    
    for model_id in targets:
        print(f"\n--- HANDSHAKING WITH: {model_id} ---")
        try:
            response = await client.aio.models.generate_content(
                model=model_id,
                contents="Hello. Identification protocol: State your name and version.",
                config=types.GenerateContentConfig(max_output_tokens=50)
            )
            print(f"STATUS: SUCCESS")
            print(f"RESPONSE: {response.text.strip()}")
        except Exception as e:
            print(f"STATUS: FAILED")
            print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(diagnostic_handshake())
