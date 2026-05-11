import os
import asyncio
from google import genai
from dotenv import load_dotenv
load_dotenv()

async def inspect_flash_lite():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print("Checking Gemini 3.1 Flash Lite structure...")
    
    try:
        lite = client.models.get(model='gemini-3.1-flash-lite-preview')
        print(f"MODEL NAME: {lite.name}")
        print(f"ACTIONS: {getattr(lite, 'supported_actions', 'Unknown')}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_flash_lite())
