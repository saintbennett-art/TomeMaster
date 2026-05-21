import httpx
import json

async def test_ollama_model(target_model):
    url = "http://127.0.0.1:11434/api/chat"
    persona = "Developmental Editor"
    prompt = "Hi"
    
    payload = {
        "model": target_model, 
        "messages": [
            {"role": "system", "content": f"Act as {persona}."}, 
            {"role": "user", "content": prompt}
        ], 
        "stream": False
    }
    
    print(f"Testing {target_model}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload)
            print(f"Status Code: {res.status_code}")
            if res.status_code != 200:
                print(f"Error Response: {res.text}")
            else:
                print("Success!")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    import asyncio
    async def main():
        await test_ollama_model("gemma4:e2b")
        print("-" * 20)
        await test_ollama_model("gemma4:e4b")
    asyncio.run(main())
