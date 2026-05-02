import httpx
import json
import asyncio

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
            "num_ctx": 1024,
        }
    }
    
    print(f"Testing {target_model} with reduced context (1024)...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, json=payload)
            print(f"Status Code: {res.status_code}")
            print(f"Response: {res.text}")
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception Message: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ollama_with_options("deepseek-r1:8b"))
