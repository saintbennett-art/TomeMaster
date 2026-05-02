import asyncio
import httpx

async def test_endpoint():
    async with httpx.AsyncClient() as client:
        print("Sending request to /api/v1/analysis/multi-agent")
        res = await client.post("http://localhost:8080/api/v1/analysis/multi-agent", json={"text": "This is a quick test chapter. John walked down the hall and opened the door.", "personas": ["Developmental Editor", "Hollywood Screenwriter"]}, timeout=10.0)
        print(res.status_code)
        print(res.text)

if __name__ == "__main__":
    asyncio.run(test_endpoint())
