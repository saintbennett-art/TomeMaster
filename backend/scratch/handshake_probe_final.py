
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

async def probe():
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=key)
    
    test_names = ['gemini-flash-latest', 'models/gemini-flash-latest']
    
    for name in test_names:
        print(f"PROBE: Testing '{name}'...")
        try:
            model = genai.GenerativeModel(name)
            response = await model.generate_content_async("Hi")
            print(f"SUCCESS: '{name}' is working.")
        except Exception as e:
            print(f"FAIL: '{name}' failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(probe())
