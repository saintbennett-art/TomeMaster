import os
import glob
import time
import json
import base64
import traceback
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# [MASTER DIRECTIVE]: Anchoring to the .env bedrock
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("FATAL ERROR: No OPENAI_API_KEY found in .env file. Resurrection cannot proceed.")
    exit(1)

client = OpenAI(api_key=api_key)

# [MASTER DIRECTIVE]: GPT-4o is the mandated Vision Engine
MODEL = "gpt-4o"

IMAGE_DIR = r"C:\Users\saint\OneDrive\Documents\This Close\This Close"
OUTPUT_JSON = "transcription_cache.json"
OUTPUT_MD = "Master_Transcribed.md"

# Conservative batch size for high-fidelity vision context
BATCH_SIZE = 1 
COOLDOWN_SECONDS = 2 

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def run_transcription():
    print(f"--- TOMEMASTER RESURRECTION ENGINE ---")
    print(f"Scanning directory: {IMAGE_DIR}")
    
    all_files = glob.glob(os.path.join(IMAGE_DIR, "*.jpg")) + \
                glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")) + \
                glob.glob(os.path.join(IMAGE_DIR, "*.png"))
                
    all_files = sorted(all_files)
    total_files = len(all_files)
    
    print(f"Found {total_files} manuscript photos.")
    if total_files == 0:
        return

    # [JARVIS]: Load existing cache for safe resume
    master_pages = []
    if os.path.exists(OUTPUT_JSON):
        print("Found existing transcription cache! Resuming resurrection...")
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            try:
                master_pages = json.load(f)
            except:
                print("Cache corruption detected. Starting fresh.")
                master_pages = []
            
    processed_count = len(master_pages)
    files_to_process = all_files[processed_count:]
    
    print(f"Remaining unprocessed photos: {len(files_to_process)}\n")

    for i, file_path in enumerate(files_to_process):
        current_index = processed_count + i + 1
        print(f"[*] Resurrecting Page {current_index}/{total_files}: {os.path.basename(file_path)}")
        
        try:
            base64_image = encode_image(file_path)
            
            # [MASTER DIRECTIVE]: High-fidelity authorial prompt
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe this manuscript page exactly. Join lines within paragraphs into single continuous blocks. Use double newlines between paragraphs. No smart quotes. Return as a JSON object with 'page_number' and 'text' fields."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                }
                            },
                        ],
                    }
                ],
                response_format={ "type": "json_object" }
            )
            
            raw_content = response.choices[0].message.content
            page_data = json.loads(raw_content)
            
            # Add metadata for sorting
            page_data['file_path'] = file_path
            page_data['timestamp'] = time.time()
            
            master_pages.append(page_data)
            
            # [JARVIS]: Hardened save after every successful page
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(master_pages, f, indent=4)
                
            print(f"   [OK] Page {page_data.get('page_number', '??')} processed.")
            time.sleep(COOLDOWN_SECONDS)
            
        except Exception as e:
            print(f"!!! ERROR ON PAGE {current_index}: {e}")
            print("Engine pausing for safety. Restart to resume.")
            break

    print("\n--- Resurrection Complete ---")
    
    if master_pages:
        # Stitching Phase
        print(f"Stitching {len(master_pages)} pages into Master Markdown...")
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            for page in master_pages:
                f.write(f"## Page {page.get('page_number', '??')}\n\n")
                f.write(page.get("text", "") + "\n\n")
                
        print(f"Master file saved to: {os.path.abspath(OUTPUT_MD)}")

if __name__ == "__main__":
    run_transcription()
