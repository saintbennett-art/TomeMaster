import httpx
import json
import time
import asyncio

async def test_gemma_latency():
    url = "http://127.0.0.1:11434/api/chat"
    target_model = "gemma4:e2b"
    prompt = "Hi, respond with only one word: OK."
    
    payload = {
        "model": target_model, 
        "messages": [
            {"role": "user", "content": prompt}
        ], 
        "stream": False,
        "options": {
            "num_ctx": 1024
        }
    }
    
    print(f"Testing latency for {target_model}...")
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            res = await client.post(url, json=payload)
            end_time = time.time()
            duration = end_time - start_time
            print(f"Status Code: {res.status_code}")
            print(f"Duration: {duration:.2f} seconds")
            if res.status_code == 200:
                print(f"Response: {res.json().get('message', {}).get('content', '')}")
            else:
                print(f"Error: {res.text}")
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception Message: '{str(e)}'")

if __name__ == "__main__":
    asyncio.run(test_gemma_latency())
