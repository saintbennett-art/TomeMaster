
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

async def probe():
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    test_models = ['gemini-flash-latest', 'gemini-flash-lite-latest']
    
    genai.configure(api_key=key)
    
    for m_name in test_models:
        print(f"PROBE: Testing {m_name}...")
        try:
            model = genai.GenerativeModel(m_name)
            response = await model.generate_content_async("Hi")
            print(f"SUCCESS: {m_name} is LIVE.")
            return m_name
        except Exception as e:
            print(f"FAIL: {m_name} error: {e}")
    
    print("STATUS: ALL MODELS EXHAUSTED.")

if __name__ == "__main__":
    asyncio.run(probe())
