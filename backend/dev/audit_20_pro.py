import os
import asyncio
from google import genai
from dotenv import load_dotenv

async def audit():
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    try:
        # [2.0 PRO AUDIT]: Verifying high-fidelity member series
        res = await client.aio.models.generate_content(
            model='gemini-2.0-pro-exp-02-05', 
            contents='Verify 2.0 Pro Sovereign Handshake.'
        )
        print(f"PULSE [2.0 Pro]: SUCCESS -> {res.text.strip()}")
    except Exception as e:
        print(f"PULSE [2.0 Pro]: FAIL -> {e}")

if __name__ == "__main__":
    asyncio.run(audit())
