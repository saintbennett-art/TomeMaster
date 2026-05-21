import os
import json
import base64
import hashlib
import sys

# Ensure get_key is imported from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    from get_key import get_machine_fingerprint
except ImportError:
    # [N3 FIX]: Hard-fail instead of silently falling back to a universal key
    raise RuntimeError(
        "CRITICAL SECURITY FAILURE: get_key.py not found. "
        "The hardware fingerprint module is required for vault encryption. "
        "Ensure get_key.py exists in the project root."
    )

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "settings.enc")

def _get_fernet_key():
    """Derive a Fernet-compatible key (URL-safe base64 of 32 bytes) from the hardware fingerprint."""
    fingerprint = get_machine_fingerprint()
    raw_key = hashlib.sha256(fingerprint.encode()).digest()
    return base64.urlsafe_b64encode(raw_key)

def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """[LEGACY]: Basic XOR cipher retained only for backward-compatible vault migration."""
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))

def save_vault(data: dict):
    """Encrypts and saves vault data using Fernet (AES-128-CBC + HMAC)."""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_fernet_key())
        json_bytes = json.dumps(data).encode('utf-8')
        encrypted = f.encrypt(json_bytes)
        with open(SETTINGS_FILE, "wb") as fh:
            fh.write(encrypted)
    except ImportError:
        # Fallback: if cryptography is not installed, use legacy XOR
        print("WARNING: 'cryptography' package not installed. Falling back to legacy XOR encryption.")
        key = hashlib.sha256(get_machine_fingerprint().encode()).digest()
        json_str = json.dumps(data)
        encrypted = _xor_crypt(json_str.encode('utf-8'), key)
        with open(SETTINGS_FILE, "wb") as fh:
            fh.write(base64.b64encode(encrypted))

def load_vault() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    
    with open(SETTINGS_FILE, "rb") as fh:
        raw_data = fh.read()
    
    # Attempt Fernet (AES) decryption first
    try:
        from cryptography.fernet import Fernet, InvalidToken
        f = Fernet(_get_fernet_key())
        try:
            decrypted = f.decrypt(raw_data).decode('utf-8')
            return json.loads(decrypted)
        except InvalidToken:
            pass  # Not a Fernet token — try legacy XOR below
    except ImportError:
        pass  # cryptography not installed — try legacy XOR below
    
    # [BACKWARD COMPAT]: Try legacy XOR decryption for pre-upgrade vaults
    try:
        key = hashlib.sha256(get_machine_fingerprint().encode()).digest()
        encrypted = base64.b64decode(raw_data)
        decrypted = _xor_crypt(encrypted, key).decode('utf-8')
        data = json.loads(decrypted)
        # Auto-upgrade: re-encrypt with Fernet on next save
        print("VAULT MIGRATION: Legacy XOR vault detected. Will upgrade to AES on next save.")
        return data
    except Exception:
        print("CRITICAL ERROR: Failed to decrypt vault. Machine fingerprint mismatch or corrupt file.")
        return {}

def inject_keys_to_env():
    vault = load_vault()
    if not vault:
        return False
    
    # 1. Inject API Keys into environment (Support Nested GUI Schema)
    api_keys = vault.get('api_keys', {})
    if 'gemini' in api_keys and api_keys['gemini']: os.environ['GEMINI_API_KEY'] = api_keys['gemini']
    if 'openai' in api_keys and api_keys['openai']: os.environ['OPENAI_API_KEY'] = api_keys['openai']
    if 'anthropic' in api_keys and api_keys['anthropic']: os.environ['ANTHROPIC_API_KEY'] = api_keys['anthropic']
    if 'groq' in api_keys and api_keys['groq']: os.environ['GROQ_API_KEY'] = api_keys['groq']
    
    # 2. Support Flat Schema from config_wizard.py
    if 'gemini_api_key' in vault: os.environ['GEMINI_API_KEY'] = vault['gemini_api_key']
    if 'openai_api_key' in vault: os.environ['OPENAI_API_KEY'] = vault['openai_api_key']
    if 'anthropic_api_key' in vault: os.environ['ANTHROPIC_API_KEY'] = vault['anthropic_api_key']
    
    # 3. Inject Model Maps (Nested GUI Schema)
    preferred_models = vault.get('preferred_models', {})
    if 'vision' in preferred_models: os.environ['SCRIBE_MODEL'] = preferred_models['vision']
    if 'COPY_EDITOR' in preferred_models: os.environ['EDITOR_MODEL'] = preferred_models['COPY_EDITOR']
    if 'Editor-in-Chief' in preferred_models: os.environ['DIRECTOR_MODEL'] = preferred_models['Editor-in-Chief']
    if 'analysis' in preferred_models: os.environ['ANALYST_MODEL'] = preferred_models['analysis']

    # 4. Support Flat Schema from config_wizard.py
    if 'scribe_model' in vault: os.environ['SCRIBE_MODEL'] = vault['scribe_model']
    if 'editor_model' in vault: os.environ['EDITOR_MODEL'] = vault['editor_model']
    if 'director_model' in vault: os.environ['DIRECTOR_MODEL'] = vault['director_model']
    if 'analyst_model' in vault: os.environ['ANALYST_MODEL'] = vault['analyst_model']
        
    return True
