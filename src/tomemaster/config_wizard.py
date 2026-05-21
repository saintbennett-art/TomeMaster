import os
import sys

# Ensure root path is imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tomemaster.vault_loader import save_vault, load_vault
from get_key import get_machine_fingerprint
import hashlib

def generate_valid_license():
    machine_id = get_machine_fingerprint()
    combined = f"{machine_id}::TomeMaster-2026-StandardConsulting-Salt"
    full_hash = hashlib.sha256(combined.encode()).hexdigest()
    prefix = full_hash[:12].upper()
    return f"TOME-{prefix[:4]}-{prefix[4:8]}-{prefix[8:]}"

def run_wizard():
    print("="*50)
    print(" TomeMaster 2026: Setup & Configuration Wizard")
    print("="*50)
    print("\nThis wizard will securely encrypt your keys tied to your machine hardware.")
    
    vault = load_vault()
    
    print("\n--- 1. License Verification ---")
    print("If you purchased the app, enter your hardware-locked license key to unlock watermark-free outputs.")
    print("Otherwise, leave blank to run in Freemium (Watermarked) Mode.")
    lic = input(f"License Key (Current: {vault.get('license_key', 'None')}): ").strip()
    if lic:
        vault['license_key'] = lic
        
    if vault.get('license_key') == generate_valid_license():
        print(">> PRO LICENSE CONFIRMED. Outputs will not be watermarked.")
    else:
        print(">> RUNNING IN FREEMIUM MODE. All outputs will be watermarked.")

    print("\n--- 2. API Keys ---")
    print("Leave blank to keep current key.")
    gemini = input("Gemini API Key (Mandatory for Scribe/Editor): ").strip()
    if gemini: vault['gemini_api_key'] = gemini
    
    anthropic = input("Anthropic API Key (Optional for Marketing): ").strip()
    if anthropic: vault['anthropic_api_key'] = anthropic
    
    openai = input("OpenAI API Key (Optional for Pacing Analyst): ").strip()
    if openai: vault['openai_api_key'] = openai
    
    print("\n--- 3. Dynamic Model Routing ---")
    print("Configure which engine runs which specialist.")
    scribe_model = input(f"Scribe/Vision Model [Default: gemini/gemini-3.1-pro]: ").strip()
    vault['scribe_model'] = scribe_model if scribe_model else "gemini/gemini-3.1-pro"
    
    editor_model = input(f"Editor Model [Default: gemini/gemini-3.1-pro]: ").strip()
    vault['editor_model'] = editor_model if editor_model else "gemini/gemini-3.1-pro"
    
    director_model = input(f"Marketing Model [Default: anthropic/claude-3-5-sonnet-20241022]: ").strip()
    vault['director_model'] = director_model if director_model else "anthropic/claude-3-5-sonnet-20241022"
    
    analyst_model = input(f"Analyst Model [Default: openai/gpt-4o]: ").strip()
    vault['analyst_model'] = analyst_model if analyst_model else "openai/gpt-4o"
    
    save_vault(vault)
    print("\n" + "="*50)
    print(" Setup Complete! Keys securely encrypted to hardware footprint.")
    print(" You can now run the pipeline.")
    print("="*50)

if __name__ == "__main__":
    run_wizard()
