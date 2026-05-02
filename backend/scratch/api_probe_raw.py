
import requests
import json
import os
from dotenv import load_dotenv

def probe_api():
    load_dotenv()
    api_base = "http://127.0.0.1:8080/api/v1"
    url = f"{api_base}/analysis/multi-agent"
    
    payload = {
        "text": "This is a test manuscript for forensic verification.",
        "personas": ["Developmental Editor"],
        "provider": "gemini",
        "api_key": os.environ.get("GEMINI_API_KEY"),
        "model": "auto"
    }
    
    print(f"PROBE: Sending payload to {url}...")
    try:
        response = requests.post(url, json=payload, timeout=20)
        print(f"STATUS: {response.status_code}")
        print(f"RESPONSE: {response.text}")
    except Exception as e:
        print(f"FAIL: API request failed: {e}")

if __name__ == "__main__":
    probe_api()
