# TomeMaster V2: Master Design Architecture

> **Last Updated:** 2026-05-21 — Post-Audit Revision (9 defects resolved)

## Overview

TomeMaster V2 is a fully self-contained, locally sovereign transcription and publishing engine. It merges a responsive React User Interface with a parallel-processing backend powered by CrewAI Flows. The application is secured by Fernet AES-128-CBC authenticated encryption, with API keys and configuration locked to the user's physical hardware fingerprint. No cloud dependency is required — the system operates entirely offline once API keys are configured.

---

## 1. The Presentation Layer (Frontend)

### React Boardroom Dashboard (`frontend/`)

The user interface is built using a modern React frontend. It features real-time progress bars, settings panels, and a live-streaming text dashboard.

- **The Streaming Buffer:** Instead of waiting for an entire book to compile, the UI constantly polls the backend's `stream_buffer`. As soon as a single paragraph is processed by the AI, it instantly materializes on the screen, creating a dynamic, real-time feedback loop.

### Native Windows Wrapper (`backend/desktop_app.py`)

TomeMaster does not run in a standard web browser. The backend spawns a chromeless, native Windows Webview GUI using `pywebview`. This viewport traps the React dashboard inside an application window, making the Python/React hybrid feel like a premium, native Windows desktop executable.

- **Dynamic Port Allocation:** The server binds to a random available port at runtime (via `get_free_port()`), preventing conflicts with other services.
- **Health Check:** The GUI waits for the backend to respond on `/api/v1/ai/status` before rendering, with a 15-second timeout and graceful fallback.
- **Close Confirmation:** A native `tkinter` dialog prevents accidental shutdowns on touch devices.

---

## 2. The Bridge (FastAPI Middleware)

### The Routing Engine (`backend/routers/transcribe.py`)

The FastAPI backend acts as the bridge between the UI and the heavy AI agents. When a user clicks "Start", the React app pings the `/start` endpoint. The router:

1. Resolves the user's preferred vision model from the encrypted Vault via `settings_service.get_model_for_role()`.
2. Dynamically injects the project root into `sys.path` so the CrewAI pipeline can be imported.
3. Spawns an isolated background thread (via `threading.Thread`) so the UI does not freeze.
4. Triggers the core `TomeMasterPipeline.kickoff()` with the user's target folder.

### Concurrency Model

All legacy Redis/Celery dependencies have been permanently removed. The application now uses standard Python `threading` and `threading.Lock` for safe concurrent access to the shared `TRANSCRIPTION_STATE` buffer. The `transcriber_service.py` function `run_transcription_job()` is retained as deprecated legacy reference only.

---

## 3. Sovereign Security & Governance

### Hardware Fingerprinting (`get_key.py`)

The foundation of the security model. This script probes the underlying Windows hardware to generate a unique mathematical fingerprint of the physical machine. If `get_key.py` cannot be located at import time, the application raises a hard `RuntimeError` and refuses to start — it does not fall back to a universal default key.

### The Encrypted Vault (`src/tomemaster/vault_loader.py`)

Legacy `.env` files are banned. The user's API keys (OpenAI, Gemini, Anthropic, Groq) and Model Maps are encrypted using **Fernet (AES-128-CBC with HMAC authentication)** derived from the hardware fingerprint. The vault file (`settings.enc`) is impossible to decrypt if moved to a different computer.

- **Encryption:** `cryptography.fernet.Fernet` with a SHA-256-derived key from the hardware fingerprint.
- **Backward Compatibility:** If a legacy XOR-encrypted vault from a pre-upgrade installation is detected, it is transparently decrypted and auto-upgraded to Fernet on the next save operation.
- **Fallback:** If the `cryptography` package is not installed, the system falls back to legacy XOR with a console warning.

### Unified Settings Bridge (`backend/services/settings_service.py`)

The React Dashboard's settings panel routes directly into the encrypted Vault. When a user saves API keys or model preferences from the GUI, `settings_service.save_settings()` encrypts them via `vault_loader.save_vault()`. When the backend needs a key or model, `settings_service.load_settings()` decrypts from the same vault. There is no plaintext `settings.json` anywhere in the system.

- **Input Validation:** All incoming settings pass through `_validate_settings()`, which enforces a strict allowlist of permitted keys and casts values to safe types.
- **Slot Fallback:** Branded API key slots (`slot_primary`, `slot_specialist`, `slot_velocity`) cascade to their provider equivalents (`gemini`, `openai`, `groq`) if empty.

### Dual-Schema Vault Injection (`vault_loader.inject_keys_to_env()`)

The environment injector understands two schemas simultaneously:

1. **Nested GUI Schema:** `{"api_keys": {"gemini": "..."}, "preferred_models": {"vision": "..."}}`
2. **Flat CLI Schema:** `{"gemini_api_key": "...", "scribe_model": "..."}`

This ensures the backend CrewAI agents receive the correct API keys regardless of whether the user configures the system via the Web UI or the terminal `config_wizard.py`.

### The Setup Wizard (`src/tomemaster/config_wizard.py`)

A command-line terminal UI that allows the user to securely map their API keys and assign specific dynamic AI models (e.g., `gemini/gemini-3.1-pro` for transcription, `openai/gpt-4o` for pacing) to the Vault. It supports both local Ollama models and cloud engines.

### PII Redaction (`backend/services/pii_scrubber.py`)

A deterministic, GovCloud/FERPA-compliant security checkpoint powered by Microsoft Presidio. **PII scrubbing is opt-in**, gated by the user's `preferences.pii_scrub` setting in the Vault (default: `false`).

When enabled:
- **UI Scrubbing:** Before text is streamed to the dashboard, it is scrubbed for SSNs, phone numbers, email addresses, and PII.
- **Pipeline Scrubbing:** The entire raw manuscript is scrubbed again before it is passed to the downstream Editor/Director agents.

When disabled (the default), text flows through unmodified — critical for fiction manuscripts where character names would otherwise be incorrectly redacted as `<PERSON>`.

### Freemium Watermarking (`src/tomemaster/main.py`)

The engine validates the user's `license_key` against the hardware fingerprint. If the license is missing or invalid, the engine operates in "Freemium Mode," injecting visible text watermarks into all output `.txt` and `.md` files. The output directory is resolved as an absolute path relative to the project root to prevent CWD-dependent behavior.

---

## 4. The Intelligence Engine (CrewAI)

### The Core Flow (`src/tomemaster/main.py`)

The `TomeMasterPipeline` dictates the chronological sequence of events using CrewAI `@start` and `@listen` decorators:

1. `setup_security`: Unlocks the Vault, injects keys into the environment, and checks licensing.
2. `run_transcription`: Triggers the parallel Transcription Crew with the user's folder path.
3. `run_chapterization`: The Structural Editor compiles the raw text into a chapterized Markdown manuscript.
4. `run_marketing_analysis`: *(Parallel)* The Marketing Director generates blurbs and campaign strategy.
5. `run_pacing_analysis`: *(Parallel)* The Pacing Analyst maps emotional beats and narrative arcs.
6. `finalize_outputs`: Waits for both parallel specialists to complete, then applies watermarks (if freemium).

Steps 4 and 5 execute **simultaneously** — both `@listen` to the same `run_chapterization` trigger, implementing the parallel "Boardroom Fan-Out" specified in the original Gemini architectural blueprint.

### The Asynchronous Fan-Out (`src/tomemaster/crews/transcription_crew/transcription_crew.py`)

Unlike procedural loops, the Transcription Crew dynamically scans the target folder and spawns a parallel, asynchronous `Task` for *every single image*.

- **Real-Time Hook:** Each parallel task triggers a `ui_sync_callback`, instantly dumping the decoded text into the UI's `stream_buffer` while the other agents continue working. PII scrubbing within the callback is gated by the user's preference.
- **The Stitcher:** A final synchronous compile task waits for all asynchronous Scribe agents to finish, stitching the parallel outputs into a single chronological `raw_manuscript.txt`.
- **Rate Limiting:** The Crew enforces `max_rpm=15` to prevent API rate-limit crashes.

### The Publishing Boardroom (`src/tomemaster/crews/publishing_crew/publishing_crew.py`)

The downstream specialist crew that analyzes the raw manuscript. Each agent dynamically pulls their designated model from the Vault at runtime via `os.environ`:

1. **The Editor** (`EDITOR_MODEL`): Generates a structured, chapterized `.md` book.
2. **The Marketing Director** (`DIRECTOR_MODEL`): Writes a commercial blurb and targeted market strategy.
3. **The Analyst** (`ANALYST_MODEL`): Produces an emotional pacing and narrative structure report.

### YAML Configuration (`config/agents.yaml` & `config/tasks.yaml`)

All agent personas and task instructions are externalized into YAML files, separating prompt engineering from runtime logic. This allows persona tuning without touching Python code.

---

## 5. Build & Distribution

### The Nuitka Compiler (`scripts/build_secure_exe.ps1`)

The final distribution pipeline script. When run, it performs four sequential steps:

1. **[1/4] Toolchain Installation:** Installs Nuitka and setuptools via pip.
2. **[2/4] Frontend Synthesis:** Commands `npm run build` to compile the React dashboard into static HTML/JS assets.
3. **[3/4] Asset Consolidation:** Moves the static assets into `backend/web_dist`.
4. **[4/4] C-Level Compilation:** Uses the Nuitka compiler to translate the entire Python backend — including CrewAI, Pydantic, Microsoft Presidio NLP, and the `cryptography` package — into raw C code, bundling everything into a single standalone `.exe` that hides the command prompt for a premium user experience.

---

## 6. Pipeline Execution Flow

```
[ Raw Images Folder ]
         │
         ▼
┌────────────────────────────────┐
│   @start: setup_security       │
│   Unlock Vault → Inject Keys   │
│   Validate License             │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│   @listen: run_transcription   │
│   [Scribe Agent]               │
│    ├── Page 001 → (Async) ──┐  │
│    ├── Page 002 → (Async) ──┤  │
│    └── Page N   → (Async) ──┘  │
│   Synchronous Anchor: Stitch   │
│   Optional PII Scrub (opt-in)  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│   @listen: run_chapterization  │
│   [Structural Book Editor]     │
│   → compiled_book.md           │
└────────────┬───────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼  (Parallel Fan-Out)
┌───────────┐  ┌───────────┐
│ Marketing │  │  Pacing   │
│ Director  │  │  Analyst  │
│ Blurbs    │  │ Arcs/Beats│
└─────┬─────┘  └─────┬─────┘
      └───────┬───────┘
              ▼
┌────────────────────────────────┐
│   @listen: finalize_outputs    │
│   Apply Watermarks (if free)   │
│   ✨ Pipeline Complete         │
└────────────────────────────────┘
```
