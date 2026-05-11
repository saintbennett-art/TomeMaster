import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

async def discover_allowed_models():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("No GEMINI_API_KEY found.")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    
    print(f"\n[INITIATING DISCOVERY PULSE]")
    print(f"Checking authorized model portfolio for key: {key[:10]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"Success! {len(models)} models authorized.")
                
                # List the models and their capabilities
                for m in models:
                    name = m.get("name", "unknown")
                    # We look for 1.5, 2.0, 3.1, etc.
                    display_name = m.get("displayName", "")
                    print(f"- {name:40} | {display_name}")
            else:
                print(f"Handshake Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"Discovery Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(discover_allowed_models())
