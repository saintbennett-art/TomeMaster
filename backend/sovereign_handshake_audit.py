import os
import asyncio
from google import genai
from dotenv import load_dotenv

async def audit_handshake():
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Sovereign Vault Key not found in .env")
        return

    # [IDENTIFIER AUDIT]: Testing the specific 2026 series snapshots
    test_models = [
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.0-pro-exp-02-05"
    ]

    print(f"--- SOVEREIGN HANDSHAKE AUDIT [APRIL 2026] ---")
    client = genai.Client(api_key=api_key)

    for model in test_models:
        try:
            print(f"PULSE: Auditing {model}...", end=" ", flush=True)
            # Minimal heartbeat request
            response = await client.aio.models.generate_content(
                model=model,
                contents="Heartbeat pulse: Respond with 'ACTIVE'."
            )
            print(f"[PASS] -> {response.text.strip()}")
        except Exception as e:
            print(f"[FAIL] -> {str(e)}")

if __name__ == "__main__":
    asyncio.run(audit_handshake())
