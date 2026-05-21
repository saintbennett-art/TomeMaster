import httpx
import json

async def test_ollama_with_options(target_model):
    url = "http://127.0.0.1:11434/api/chat"
    persona = "Developmental Editor"
    prompt = "Hi"
    
    payload = {
        "model": target_model, 
        "messages": [
            {"role": "user", "content": prompt}
        ], 
        "stream": False,
        "options": {
            "num_ctx": 2048,
            "num_thread": 4
        }
    }
    
    print(f"Testing {target_model} with reduced context (2048)...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            print(f"Status Code: {res.status_code}")
            if res.status_code != 200:
                print(f"Error Response: {res.text}")
            else:
                print("Success!")
                # print(res.json().get("message", {}).get("content", ""))
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ollama_with_options("deepseek-r1:8b"))
