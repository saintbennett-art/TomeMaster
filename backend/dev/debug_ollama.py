import httpx
import json

async def test_ollama_failure():
    url = "http://127.0.0.1:11434/api/chat"
    target_model = "deepseek-r1:8b"
    persona = "Developmental Editor"
    prompt = "Suggest a chapter break for: Once upon a time in a land far away..."
    
    payload = {
        "model": target_model, 
        "messages": [
            {"role": "system", "content": f"Act as {persona}."}, 
            {"role": "user", "content": prompt}
        ], 
        "stream": False
    }
    
    print(f"Testing {target_model} with system message...")
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
    asyncio.run(test_ollama_failure())
