import asyncio
import os
from services import ai_service

async def test_safeguard():
    print("Testing Ollama Safeguard Logic...")
    
    # 1. Test Passive Mode (local_mode=False, Env Var=False)
    os.environ["OLLAMA_ACTIVE"] = "false"
    persona, result = await ai_service.analyze_persona_async(
        text="Test", 
        persona="Developmental Editor", 
        provider="ollama", 
        local_mode=False
    )
    
    if "LOGISTICS ERROR" in str(result.get("feedback", "")):
        print("SUCCESS: Safeguard blocked request in Passive Mode.")
    else:
        print("FAILURE: Safeguard did NOT block request in Passive Mode.")
        print(f"Result: {result}")

    # 2. Test Local Mode (local_mode=True, Env Var=False)
    # This should attempt a connection and fail with a connection error (since Ollama isn't running),
    # but it should NOT return the LOGISTICS ERROR.
    print("\nTesting Local Mode Activation...")
    persona, result = await ai_service.analyze_persona_async(
        text="Test", 
        persona="Developmental Editor", 
        provider="ollama", 
        local_mode=True
    )
    
    feedback = str(result.get("feedback", ""))
    if "LOGISTICS ERROR" in feedback:
        print("FAILURE: Safeguard still blocked request despite local_mode=True.")
    elif "CONNECTION REFUSED" in feedback or "LOCAL ENGINE ERROR" in feedback:
        print("SUCCESS: Logic bypassed safeguard and attempted connection.")
    else:
        print(f"Unexpected result: {feedback}")

if __name__ == "__main__":
    asyncio.run(test_safeguard())
