import sys
import json
import os
import re

# [RESURRECTION]: Hardened MCP Handshake with Manual Stitching Tool
PROJECT_ROOT = r"C:\Users\saint\OneDrive\Documents\This Close\Demo\This Close"
LEDGER_PATH = os.path.join(PROJECT_ROOT, "project_ledger.json")

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', os.path.basename(s))]

def run_stitcher():
    all_rtfs = []
    search_areas = [PROJECT_ROOT, os.path.join(PROJECT_ROOT, "Archive")]
    for area in search_areas:
        if os.path.exists(area):
            for f in os.listdir(area):
                if f.lower().endswith(".rtf"):
                    all_rtfs.append(os.path.join(area, f))
    
    all_rtfs.sort(key=natural_sort_key)
    if not all_rtfs:
        return "ERROR: No RTF pages found."

    final_text = ""
    for rtf_path in all_rtfs:
        try:
            with open(rtf_path, "r", encoding="utf-8", errors="ignore") as f:
                final_text += f.read() + "\n\n"
        except: continue

    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r") as f:
            ledger = json.load(f)
    else:
        ledger = {"status": "complete", "total_images": 498}

    ledger.update({
        "status": "complete",
        "text": final_text.strip(),
        "error_message": "Your manuscript is ready!"
    })

    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=4)
    
    return f"SUCCESS: Unified {len(all_rtfs)} pages."

def send_response(response_id, result):
    response = {
        "jsonrpc": "2.0",
        "id": response_id,
        "result": result
    }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            
            request = json.loads(line)
            req_id = request.get("id")
            method = request.get("method")

            if method == "initialize":
                send_response(req_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "TomeMaster-Resurrection-Bridge",
                        "version": "1.0.0"
                    }
                })
            elif method == "tools/list":
                send_response(req_id, {
                    "tools": [
                        {
                            "name": "stitch_manuscript",
                            "description": "Unifies 498 RTF pages from root and Archive into the project ledger.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                })
            elif method == "tools/call":
                params = request.get("params", {})
                if params.get("name") == "stitch_manuscript":
                    result_msg = run_stitcher()
                    send_response(req_id, {
                        "content": [{"type": "text", "text": result_msg}]
                    })
            elif method == "notifications/initialized":
                continue
            else:
                send_response(req_id, {})
                
        except Exception:
            continue

if __name__ == "__main__":
    main()
