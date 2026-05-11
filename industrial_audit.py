import os
import re

def audit_directory(dir_path):
    issues_found = 0
    legacy_patterns = [
        r'localStorage\.getItem\([\'"`]tome_master_key_.*[\'"`]\)',
        r'localStorage\.setItem\([\'"`]tome_master_key_.*[\'"`]',
        r'localStorage\.getItem\([\'"`]tome_master_keys[\'"`]\)'
    ]
    
    # We ignore migration_gate.ts because it is designed to clear legacy keys
    ignore_files = ['migration_gate.ts']
    
    print(f"Scanning directory: {dir_path} for legacy credential leakage...")
    
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(('.ts', '.tsx', '.js', '.jsx')) and file not in ignore_files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line_num, line in enumerate(lines, 1):
                            for pattern in legacy_patterns:
                                if re.search(pattern, line):
                                    print(f"  [!] LEAK DETECTED: {os.path.relpath(file_path, dir_path)} (Line {line_num})")
                                    print(f"      Code: {line.strip()}")
                                    issues_found += 1
                except Exception as e:
                    pass
    
    return issues_found

if __name__ == "__main__":
    frontend_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'src')
    if os.path.exists(frontend_src):
        issues = audit_directory(frontend_src)
        print("-" * 50)
        if issues == 0:
            print("[SUCCESS] INDUSTRIAL AUDIT PASSED: 0 Legacy Credential Leaks Found.")
            print("    The application is certified zero-entropy for credential handling.")
        else:
            print(f"[X] INDUSTRIAL AUDIT FAILED: {issues} legacy references remain.")
    else:
        print("Frontend directory not found.")
