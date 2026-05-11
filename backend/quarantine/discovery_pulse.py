import os
import asyncio
from google import genai
from dotenv import load_dotenv

async def discovery():
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print("--- SOVEREIGN DISCOVERY PULSE [RAW / APRIL 2026] ---")
    try:
        # [ABSOLUTE DISCOVERY]: Listing every authorized identifier
        models = await client.aio.models.list()
        for m in models:
            # Capturing the absolute identifier for the Boardroom Registry
            print(f"AUTHORIZED IDENTIFIER: {m.name}")
    except Exception as e:
        print(f"DISCOVERY FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(discovery())
