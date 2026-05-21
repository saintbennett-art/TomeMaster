# TomeMaster V2

**A locally sovereign, multi-agent manuscript transcription and publishing engine.**

TomeMaster takes a folder of handwritten manuscript photographs and autonomously transcribes, chapterizes, and analyzes them — producing a publishable book, marketing blurbs, and emotional pacing reports — all without sending your data to external servers beyond the LLM API calls you configure.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Initial Setup](#initial-setup)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Build & Distribution](#build--distribution)
- [Configuration Reference](#configuration-reference)
- [Architecture Overview](#architecture-overview)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Prerequisites

Before installing TomeMaster, ensure you have the following on your Windows machine:

| Requirement | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core runtime |
| **Node.js** | 18+ | React frontend build |
| **npm** | 9+ | Frontend dependency management |
| **Git** | Any | Version control |

You will also need at least one LLM API key from a supported provider:

- **Google Gemini** (recommended for transcription) — `GEMINI_API_KEY`
- **Anthropic Claude** (recommended for marketing analysis) — `ANTHROPIC_API_KEY`
- **OpenAI GPT** (recommended for pacing analysis) — `OPENAI_API_KEY`
- **Groq** (optional, for high-speed inference) — `GROQ_API_KEY`

---

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url> TomeMaster
cd TomeMaster
```

### 2. Install Python Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install crewai[tools] pydantic cryptography presidio-analyzer presidio-anonymizer pywebview uvicorn fastapi Pillow PyMuPDF psutil
```

**Note:** The `cryptography` package is required for AES-encrypted vault storage. If omitted, the system falls back to legacy XOR encryption with a console warning.

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Install the CrewAI Flow

```bash
crewai install
```

---

## Initial Setup

### Configure the Encrypted Vault

TomeMaster does not use `.env` files. All API keys and model preferences are encrypted and locked to your specific hardware. Run the setup wizard:

```bash
cd src/tomemaster
python config_wizard.py
```

The wizard will prompt you for:

1. **License Key** — Enter your hardware-locked Pro license key, or leave blank for Freemium mode (watermarked outputs).
2. **API Keys** — Enter your Gemini, Anthropic, and/or OpenAI keys.
3. **Model Routing** — Assign which AI model handles each specialist role:
   - **Scribe/Vision Model** — Used for handwriting OCR (default: `gemini/gemini-3.1-pro`)
   - **Editor Model** — Used for structural chapterization (default: `gemini/gemini-3.1-pro`)
   - **Marketing Model** — Used for blurb generation (default: `anthropic/claude-3-5-sonnet-20241022`)
   - **Analyst Model** — Used for pacing analysis (default: `openai/gpt-4o`)

Your keys are encrypted using your machine's hardware fingerprint and stored in `settings.enc`. This file cannot be decrypted on any other computer.

---

## Usage

### Option A: Desktop GUI (Recommended)

Launch the native desktop application:

```bash
cd backend
python desktop_app.py
```

This opens the Boardroom Dashboard — a native Windows application window. From the GUI you can:

- Browse and select your manuscript photo folder
- Start/stop transcription jobs
- Watch pages stream in real-time as they are processed
- Configure API keys and model preferences in the Settings panel
- Toggle PII scrubbing on/off for FERPA compliance

### Option B: CLI Pipeline (Headless)

Run the full pipeline directly from the command line:

```bash
cd src/tomemaster
python main.py
```

By default, this processes images in the `./test_batch/` directory. To change the target folder, modify the `folder_path` in `TomeMasterState` or pass it programmatically:

```python
pipeline = TomeMasterPipeline()
pipeline.state.folder_path = "C:/path/to/your/manuscript/photos"
pipeline.kickoff()
```

### Pipeline Phases

When the pipeline runs, it executes these phases automatically:

| Phase | Agent | Output |
|---|---|---|
| **Phase 0** | Security | Vault decryption, key injection, license check |
| **Phase 1** | Scribe (parallel) | `output/raw_manuscript.txt` |
| **Phase 2** | Structural Editor | `output/compiled_book.md` |
| **Phase 3A** | Marketing Director *(parallel)* | `output/marketing_report.txt` |
| **Phase 3B** | Pacing Analyst *(parallel)* | `output/pacing_report.txt` |
| **Finalize** | Watermarker | Applies freemium watermarks if unlicensed |

### PII Scrubbing

PII redaction is **disabled by default** to preserve fiction character names. To enable it:

1. Open the Settings panel in the GUI, or
2. Set `"pii_scrub": true` in your vault preferences via the config wizard.

When enabled, Microsoft Presidio will redact: `PERSON`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, `US_SSN`, and `US_PASSPORT` entities.

---

## Project Structure

```
TomeMaster/
├── get_key.py                    # Hardware fingerprint generator
├── pyproject.toml                # Python project dependencies
├── MASTER_DESIGN.md              # Full architectural specification
├── settings.enc                  # Encrypted vault (auto-generated)
│
├── src/tomemaster/               # CrewAI Intelligence Engine
│   ├── main.py                   # Core Flow pipeline (@start, @listen)
│   ├── vault_loader.py           # Fernet AES vault encryption/decryption
│   ├── config_wizard.py          # CLI setup wizard
│   └── crews/
│       ├── transcription_crew/
│       │   ├── transcription_crew.py   # Scribe agent + async fan-out
│       │   └── config/
│       │       ├── agents.yaml         # Scribe persona definition
│       │       └── tasks.yaml          # Transcription task prompts
│       └── publishing_crew/
│           ├── publishing_crew.py      # Editor, Director, Analyst agents
│           └── config/
│               ├── agents.yaml         # Specialist persona definitions
│               └── tasks.yaml          # Publishing task prompts
│
├── backend/                      # FastAPI + Desktop GUI
│   ├── desktop_app.py            # Native Windows webview wrapper
│   ├── main.py                   # FastAPI application entry point
│   ├── routers/
│   │   └── transcribe.py         # API routes for transcription control
│   └── services/
│       ├── settings_service.py   # Vault-backed settings management
│       ├── transcriber_service.py # Legacy transcription engine (reference)
│       └── pii_scrubber.py       # Microsoft Presidio PII redaction
│
├── frontend/                     # React Dashboard
│   ├── package.json
│   └── src/                      # React components
│
├── scripts/
│   └── build_secure_exe.ps1      # Nuitka build script
│
├── output/                       # Pipeline output directory
│   ├── raw_manuscript.txt
│   ├── compiled_book.md
│   ├── marketing_report.txt
│   └── pacing_report.txt
│
└── test_batch/                   # Sample images for testing
```

---

## Build & Distribution

To compile TomeMaster into a standalone Windows executable:

```powershell
# Run from the project root
.\scripts\build_secure_exe.ps1
```

This script performs 4 steps:

1. Installs Nuitka compilation toolchain
2. Builds the React frontend (`npm run build`)
3. Copies static assets to `backend/web_dist/`
4. Compiles the entire Python backend into a single `.exe` using Nuitka

The output executable will be in the `build_output/` directory. Distribute it alongside `config_wizard.py` so users can configure their vault on first run.

**Bundled packages:** CrewAI, Pydantic, Presidio Analyzer, Presidio Anonymizer, and the `cryptography` library are all explicitly included in the Nuitka compilation.

---

## Configuration Reference

### Supported Models

| Role | Environment Variable | Default | Provider |
|---|---|---|---|
| Scribe (Vision/OCR) | `SCRIBE_MODEL` | `gemini/gemini-3.1-pro` | Gemini |
| Structural Editor | `EDITOR_MODEL` | `gemini/gemini-3.1-pro` | Gemini |
| Marketing Director | `DIRECTOR_MODEL` | `anthropic/claude-3-5-sonnet-20241022` | Anthropic |
| Pacing Analyst | `ANALYST_MODEL` | `openai/gpt-4o` | OpenAI |

### Settings Schema

The vault stores a JSON structure with the following permitted keys:

```json
{
    "api_keys": {
        "openai": "", "gemini": "", "groq": "", "anthropic": "",
        "slot_primary": "", "slot_specialist": "", "slot_velocity": ""
    },
    "preferred_models": {
        "vision": "gemini-3-flash-preview",
        "logic": "gemini-3-flash-preview",
        "analysis": "gemini-3.1-pro-preview",
        "NARRATIVE_ARCHITECT": "gemini-3.1-pro-preview",
        "COPY_EDITOR": "claude-3-5-sonnet-20241022",
        "TRANSCRIBER_LEAD": "gemini-3-flash-preview"
    },
    "preferences": {
        "theme": "dark",
        "auto_stitch": true,
        "language": "en",
        "pii_scrub": false
    }
}
```

---

## Architecture Overview

For the complete technical specification, see [MASTER_DESIGN.md](MASTER_DESIGN.md).

```
User clicks "Start" in the React Dashboard
         │
         ▼
FastAPI Router (/start) → Background Thread
         │
         ▼
TomeMasterPipeline.kickoff()
         │
         ├── setup_security     → Decrypt vault, inject keys
         ├── run_transcription  → Parallel async OCR on all images
         ├── run_chapterization → Structural editor compiles book
         ├── run_marketing      ┐
         ├── run_pacing         ┤ (Parallel fan-out)
         └── finalize_outputs   → Watermark if freemium
```

---

## Troubleshooting

### "CRITICAL SECURITY FAILURE: get_key.py not found"
The `get_key.py` file must exist in the project root. This file generates the hardware fingerprint used for vault encryption. Without it, the application will not start.

### "Vault not found. Please run config_wizard.py first."
You haven't configured your API keys yet. Run:
```bash
cd src/tomemaster
python config_wizard.py
```

### "VAULT MIGRATION: Legacy XOR vault detected"
This is informational, not an error. Your existing vault from a pre-upgrade installation is being read successfully. It will automatically upgrade to AES encryption the next time settings are saved.

### PII scrubber redacting character names
PII scrubbing is opt-in. Ensure `pii_scrub` is set to `false` in your preferences (it is by default). If you previously enabled it, toggle it off in the Settings panel.

### API rate limiting errors
The transcription crew is throttled to `max_rpm=15` by default. If you are still hitting limits, reduce this value in `src/tomemaster/crews/transcription_crew/transcription_crew.py`.

---

## License

See [LICENSE.md](LICENSE.md) for terms.
