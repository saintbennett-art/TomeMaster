
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

async def validate_sanitizer():
    load_dotenv()
    env_key = os.environ.get("GEMINI_API_KEY")
    
    # Simulate the "Ghost Arguments" from the UI
    poisoned_keys = ["null", "undefined", "  ", "None"]
    
    for pk in poisoned_keys:
        print(f"TEST: Attempting connection with poisoned key: '{pk}'")
        try:
            # We mimic the BUGGY logic first:
            final_key = pk or env_key # In Python, "null" is truthy! It won't fall back to env_key.
            print(f"  -> Decided key: '{final_key}' (Length: {len(final_key)})")
            
            genai.configure(api_key=final_key)
            model = genai.GenerativeModel('gemini-flash-latest')
            await model.generate_content_async("Hi")
            print("  -> SUCCESS (Unexpected!)")
        except Exception as e:
            print(f"  -> FAIL (Expected): {e}")
            
    # Now test the PROPOSED FIX logic:
    print("\nTEST: Attempting SANITIZED connection with poisoned key: 'null'")
    def sanitize(k):
        if not k: return env_key
        if k.lower() in ["null", "undefined", "none"]: return env_key
        if not k.strip(): return env_key
        return k
        
    sanitized_key = sanitize("null")
    print(f"  -> Sanitized key: '{sanitized_key[:4]}...' (Length: {len(sanitized_key)})")
    try:
        genai.configure(api_key=sanitized_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        await model.generate_content_async("Hi")
        print("  -> SUCCESS: Sanitizer recovered the connection!")
    except Exception as e:
        print(f"  -> FAIL: even sanitized key failed: {e}")

if __name__ == "__main__":
    asyncio.run(validate_sanitizer())
