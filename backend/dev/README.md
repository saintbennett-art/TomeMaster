# Development & Debug Scripts

These are development-time diagnostic, debug, and test scripts.
They are NOT part of the production TomeMaster application.

## Categories

- `debug_ollama*.py` — Ollama connection diagnostics
- `test_*.py` — Manual API/feature tests
- `verify_*.py` — Handshake and optimization verification
- `inspect_*.py` — Model inspection utilities
- `discover_*.py` / `discovery_*.py` — AI provider model discovery
- `diag_*.py` / `diagnostic_*.py` — AI service diagnostics
- `audit_*.py` / `*_audit_*.py` — Audit and benchmarking
- `Auto_Transcriber.py` — Legacy standalone transcriber (pre-CrewAI)

## Usage

Run from the `backend/` directory:
```bash
cd backend
python dev/debug_ollama.py
```
