"""
[SOVEREIGN VAULT — DPAPI]: Windows Data Protection API encryption.

The vault (settings.enc) holds cloud API keys. Encryption is bound to the
current Windows *user account* via DPAPI (CryptProtectData): Windows holds the
key material, derived from the logged-in user's credentials. An attacker who
copies settings.enc to another machine — or who merely knows the hostname/OS
(the OLD, weak key input this replaces) — cannot decrypt it without logging in
as this exact Windows user on this machine.

Zero third-party dependency: crypt32.dll is called directly through ctypes, so
this works inside the PyInstaller bundle without pywin32.

On-disk format:  b"TMV2\\n" + DPAPI-protected(JSON-utf8)

Legacy read (migration only): pre-existing Fernet (machine-fingerprint) and XOR
vaults are still *readable*, so an existing install upgrades seamlessly. On the
first successful legacy decrypt the vault is immediately re-sealed with DPAPI —
closing the weak-crypto window right away rather than waiting for the next save.
Legacy formats are NEVER written.
"""

import os
import sys
import json
import base64
import hashlib
import ctypes
from ctypes import wintypes

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "settings.enc")

# New-format magic header. Distinguishes a DPAPI vault from a legacy Fernet/XOR
# blob on read (both legacy formats are base64/Fernet bytes that never start
# with this marker).
_MAGIC = b"TMV2\n"

# App-namespace entropy mixed into DPAPI. Not a secret (it ships in source) —
# it ties the ciphertext to this app so another DPAPI consumer under the same
# user can't trivially unprotect it. The real protection is the Windows user
# account binding above.
_APP_ENTROPY = b"TomeMaster::vault::v2::BennettConsulting"


# ─── DPAPI via ctypes (crypt32.dll) ──────────────────────────────────────────

class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


_DPAPI_AVAILABLE = sys.platform == "win32"
if _DPAPI_AVAILABLE:
    try:
        _crypt32 = ctypes.windll.crypt32
        _kernel32 = ctypes.windll.kernel32
    except Exception:
        _DPAPI_AVAILABLE = False

# CryptProtectData flag: never show a UI prompt — fail instead of blocking a
# headless/background process.
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def _to_blob(data: bytes) -> _DATA_BLOB:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _from_blob(blob: _DATA_BLOB) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


def _dpapi_protect(data: bytes) -> bytes:
    din, dent, dout = _to_blob(data), _to_blob(_APP_ENTROPY), _DATA_BLOB()
    ok = _crypt32.CryptProtectData(
        ctypes.byref(din), u"TomeMasterVault",
        ctypes.byref(dent), None, None,
        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dout),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _from_blob(dout)
    finally:
        _kernel32.LocalFree(dout.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    din, dent, dout = _to_blob(data), _to_blob(_APP_ENTROPY), _DATA_BLOB()
    ok = _crypt32.CryptUnprotectData(
        ctypes.byref(din), None,
        ctypes.byref(dent), None, None,
        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dout),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _from_blob(dout)
    finally:
        _kernel32.LocalFree(dout.pbData)


# ─── Legacy crypto (READ-ONLY — migration path only, never written) ──────────

def _legacy_fingerprint() -> str:
    """The old machine fingerprint, needed ONLY to read a pre-DPAPI Fernet/XOR
    vault so it can be migrated. Imported lazily so vault security no longer
    depends on get_key.py being present."""
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        from get_key import get_machine_fingerprint
        return get_machine_fingerprint()
    except Exception:
        # No get_key.py → cannot decrypt a legacy vault, but DPAPI vaults are
        # unaffected. Return a value that simply won't match any real vault.
        return ""


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """[LEGACY]: XOR cipher — retained ONLY to read a pre-DPAPI vault for migration."""
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))


def _try_read_legacy(raw_data: bytes):
    """Attempt to decrypt a pre-DPAPI vault (Fernet first, then XOR). Returns the
    parsed dict on success, or None if this isn't a readable legacy vault."""
    fingerprint = _legacy_fingerprint()
    if not fingerprint:
        return None

    # Legacy Fernet (machine-fingerprint key)
    try:
        from cryptography.fernet import Fernet, InvalidToken
        raw_key = hashlib.sha256(fingerprint.encode()).digest()
        f = Fernet(base64.urlsafe_b64encode(raw_key))
        try:
            return json.loads(f.decrypt(raw_data).decode("utf-8"))
        except InvalidToken:
            pass  # not a Fernet token — fall through to XOR
    except ImportError:
        pass

    # Legacy XOR (base64-wrapped)
    try:
        key = hashlib.sha256(fingerprint.encode()).digest()
        decrypted = _xor_crypt(base64.b64decode(raw_data), key).decode("utf-8")
        return json.loads(decrypted)
    except Exception:
        return None


# ─── Public API ──────────────────────────────────────────────────────────────

def save_vault(data: dict) -> None:
    """Encrypts and seals vault data with Windows DPAPI (user-account bound).

    Fails CLOSED: if DPAPI is unavailable this raises instead of silently
    downgrading to weak/legacy encryption — a security product must never write
    a vault it cannot protect.
    """
    if not _DPAPI_AVAILABLE:
        raise RuntimeError(
            "CRITICAL SECURITY FAILURE: Windows DPAPI is unavailable, so the "
            "vault cannot be encrypted. Refusing to write plaintext/weak keys. "
            "TomeMaster's vault requires Windows (DPAPI)."
        )
    json_bytes = json.dumps(data).encode("utf-8")
    protected = _dpapi_protect(json_bytes)
    with open(SETTINGS_FILE, "wb") as fh:
        fh.write(_MAGIC + protected)


def load_vault() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}

    with open(SETTINGS_FILE, "rb") as fh:
        raw_data = fh.read()

    # New-format DPAPI vault
    if raw_data.startswith(_MAGIC):
        if not _DPAPI_AVAILABLE:
            print("CRITICAL ERROR: DPAPI vault present but DPAPI is unavailable on this platform.")
            return {}
        try:
            return json.loads(_dpapi_unprotect(raw_data[len(_MAGIC):]).decode("utf-8"))
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to decrypt DPAPI vault (wrong Windows user or corrupt file): {e}")
            return {}

    # Legacy vault → decrypt for migration, then re-seal with DPAPI immediately.
    legacy = _try_read_legacy(raw_data)
    if legacy is not None:
        print("VAULT MIGRATION: Legacy vault detected — re-sealing with Windows DPAPI.")
        if _DPAPI_AVAILABLE:
            try:
                save_vault(legacy)  # overwrite the weakly-encrypted file now
                print("VAULT MIGRATION: Re-seal complete. settings.enc is now DPAPI-protected.")
            except Exception as e:
                print(f"VAULT MIGRATION WARNING: Re-seal failed (keys still load this session): {e}")
        return legacy

    print("CRITICAL ERROR: Failed to decrypt vault. Machine/user mismatch or corrupt file.")
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
