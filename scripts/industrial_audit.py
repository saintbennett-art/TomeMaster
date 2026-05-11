import os
import re
import sys

# --- [CONFIGURATION] ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend", "src")
BACKEND_SRC = os.path.join(PROJECT_ROOT, "backend")

# Files allowed to have some debt (e.g. legacy extensions)
WHITELIST = ["Spellcheck.ts", "RichTextEditor.tsx"] 

def audit_namespaces():
    """Checks for state key collisions across contexts."""
    context_dir = os.path.join(FRONTEND_SRC, "context")
    registry = {}
    collisions = []
    
    for file in os.listdir(context_dir):
        if not file.endswith(".tsx"): continue
        path = os.path.join(context_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find interface properties (State keys)
            matches = re.findall(r"(\w+):\s*([^;]+);", content)
            for key, val in matches:
                if "actions" in file.lower(): continue # Skip action objects
                if key in registry and registry[key] != file:
                    collisions.append(f"COLLISION: Key '{key}' exists in both {registry[key]} and {file}")
                registry[key] = file
    return collisions

def audit_types():
    """Scans for 'any' usage and cheating markers in the source tree."""
    type_debt = []
    cheating_markers = [
        (r": any", "Explicit 'any' type declaration"),
        (r"as any", "Explicit type cast to 'any'"),
        (r"<any>", "Generic 'any' usage"),
        (r"//\s*@ts-ignore", "Cheat marker: @ts-ignore detected"),
        (r"//\s*@ts-nocheck", "Cheat marker: @ts-nocheck detected")
    ]
    
    for root, dirs, files in os.walk(FRONTEND_SRC):
        for file in files:
            if file.endswith((".ts", ".tsx")) and file not in WHITELIST:
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        for pattern, msg in cheating_markers:
                            if re.search(pattern, line):
                                type_debt.append(f"ANTI-CHEAT: {msg} in {os.path.relpath(path, PROJECT_ROOT)}:L{i}")
    return type_debt

def audit_placeholders():
    """Checks for TODOs and empty stubs."""
    stubs = []
    patterns = [
        (r"TODO", "Found TODO marker"),
        (r"async\s*\(\)\s*=>\s*{\s*}", "Found empty async stub"),
        (r"console\.log", "Found debug console.log")
    ]
    
    for root, dirs, files in os.walk(FRONTEND_SRC):
        for file in files:
            if file.endswith((".ts", ".tsx")):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern, msg in patterns:
                        if re.search(pattern, content):
                            stubs.append(f"HYGIENE: {msg} in {os.path.relpath(path, PROJECT_ROOT)}")
    return stubs

def run_audit():
    print("--- [INDUSTRIAL SOVEREIGN AUDIT] ---")
    
    collisions = audit_namespaces()
    types = audit_types()
    hygiene = audit_placeholders()
    
    success = True
    
    print(f"\n[1/3] NAMESPACE PURITY: {len(collisions)} issues")
    if collisions:
        success = False
        for c in collisions: print(f"  !! {c}")
    else:
        print("  >> [STATUS: PURE]")
        
    print(f"\n[2/3] TYPE INTEGRITY: {len(types)} issues")
    if types:
        success = False 
        for t in types[:10]: print(f"  !! {t}")
        if len(types) > 10: print(f"  ... and {len(types)-10} more.")
    else:
        print("  >> [STATUS: HARDENED]")

    print(f"\n[3/3] INDUSTRIAL HYGIENE: {len(hygiene)} issues")
    if hygiene:
        for h in hygiene[:10]: print(f"  !! {h}")
        if len(hygiene) > 10: print(f"  ... and {len(hygiene)-10} more.")
        
    print("\n" + "="*40)
    if success:
        print("FINAL VERDICT: [SYSTEM SOVEREIGN]")
        sys.exit(0)
    else:
        print("FINAL VERDICT: [SYSTEM COMPROMISED - ENTROPY DETECTED]")
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
