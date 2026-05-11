import os
from typing import Dict

ALLOWED_VAULT_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}

def save_vault_to_env(keys: Dict[str, str]) -> bool:
    """
    [VAULT STEWARD]: Commits credentials to .env and propagates to live env.
    Ensures that only whitelisted industrial keys are persisted.
    """
    env_path = ".env"
    if not os.path.exists(env_path):
        env_path = "backend/.env"

    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        new_lines = []
        updated_keys = set()

        # Update existing lines
        for line in lines:
            found = False
            for provider, env_var in ALLOWED_VAULT_KEYS.items():
                if line.startswith(f"{env_var}="):
                    val = keys.get(provider, "").strip()
                    if val:
                        new_lines.append(f"{env_var}={val}\n")
                        updated_keys.add(provider)
                        found = True
                        break
            if not found:
                new_lines.append(line)

        # Append new keys
        for provider, env_var in ALLOWED_VAULT_KEYS.items():
            val = keys.get(provider, "").strip()
            if val and provider not in updated_keys:
                new_lines.append(f"{env_var}={val}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

        # Propagate to live process env (strictly whitelisted keys only)
        for provider, env_var in ALLOWED_VAULT_KEYS.items():
            val = keys.get(provider, "").strip()
            if val:
                os.environ[env_var] = val

        return True
    except Exception as e:
        print(f"VAULT STEWARD ERROR: Persistence Failure: {e}")
        return False

def check_vault_presence() -> Dict[str, bool]:
    """Returns presence booleans for all industrial slots."""
    return {
        provider: bool(os.environ.get(env_var, "").strip())
        for provider, env_var in ALLOWED_VAULT_KEYS.items()
    }
