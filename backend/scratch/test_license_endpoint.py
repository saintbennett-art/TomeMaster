import requests

try:
    res = requests.get("http://127.0.0.1:8080/api/v1/license/status")
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
except Exception as e:
    print(f"Error: {e}")
