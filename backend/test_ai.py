import asyncio
from services import ai_service
import json

async def run_test():
    text = "John walked down the hall and opened the door. It was dark."
    personas = ["Developmental Editor", "Hollywood Screenwriter"]
    
    tasks = [ai_service.analyze_persona_async(text, p) for p in personas]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for r in results:
        if isinstance(r, Exception):
            print("EXCEPTION CAUGHT:", repr(r))
        else:
            print("SUCCESS:", r[0])

if __name__ == "__main__":
    asyncio.run(run_test())
