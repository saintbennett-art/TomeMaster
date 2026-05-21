import os
import asyncio
import json
from google import genai
from google.genai import types

# Load local .env
from dotenv import load_dotenv
load_dotenv()

async def test_3_1():
    print("Testing Gemini 3.1 Flash Connectivity...")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment.")
        return

    try:
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model='gemini-3.1-flash',
            contents="Say 'Connectivity Confirmed'",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        print(f"SUCCESS: {response.text}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_3_1())
