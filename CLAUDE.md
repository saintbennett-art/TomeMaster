# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tome-Master** is a local-first manuscript editor with AI-powered literary analysis. It runs as a desktop app (PyWebView wrapper) or in the browser, with a FastAPI backend on port 8080 and a Next.js frontend on port 3000.

## Running the App

**Full launch (both servers)**:

```bat
Start_TomeMaster.bat
```

**Backend only**:

```powershell
cd backend
.\venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend only**:

```powershell
cd frontend
npm run dev
```

**Desktop app (PyWebView)**:

```powershell
cd backend
.\venv\Scripts\activate
python desktop_app.py
```

## Running Tests

No test framework config — tests are standalone scripts. Run from `backend/`:

```powershell
cd backend
.\venv\Scripts\activate
python test_ai.py
python test_api.py
python test_export.py
```

## Building the Executable

```bat
build_exe.bat
```

Uses PyInstaller to bundle the backend into a standalone `.exe`.

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI app; registers routers, configures CORS
- **`routers/`** — Thin HTTP layer: `analysis.py`, `document.py`, `ai.py`, `transcribe.py`, `settings.py`, `license.py`
- **`services/`** — All business logic lives here; routers delegate immediately
  - `ai_service.py` — AI orchestration, Spectrum Failover cascade
  - `document_parser.py` — DOCX/PDF/TXT ingestion
  - `exporter.py` — DOCX/EPUB/PDF export
  - `transcriber_service.py` — OCR via Groq/Gemini/GPT-4o
  - `sovereign_guardrails.py` — RAM/CPU safety checks and kill switches
- **`desktop_app.py`** — PyWebView wrapper; spawns FastAPI on a free port, opens browser viewport

### Frontend (`frontend/src/`)

- **`context/WorkstationContext.tsx`** — Monolithic global state store (28KB); all components consume this
- **`lib/apiClient.ts`** — Centralized API client (28KB); all backend calls go through here
- **`components/`** — UI components; all are `"use client"` heavy
- **`lib/migration_gate.ts`** — `performMasterMigration()` runs on app load for localStorage schema migration

### Storage

- **Frontend**: localStorage for API keys/settings (`tome_master_vault`, etc.); IndexedDB for manuscript content
- **Backend**: `api_usage_log.jsonl` — append-only JSONL ledger tracking every AI call (provider, model, tokens, cost)

### AI Provider Wiring

| Role | Primary Engine | Failover Cascade |
|---|---|---|
| Structural analysis | Gemini 3.1 Pro | → Gemini 3.x Flash → 2.1 Pro → 1.5 Pro |
| Prose critique | Claude 3.5 Sonnet | — |
| Logic/OCR | GPT-4o | — |
| Vision/handwriting | Groq `llama-3.2-90b-vision` | → Gemini (genai v2 only) |

**SDK rule**: Use `google-genai` v2 (`from google import genai`) exclusively — never the legacy `google-generativeai` v1.

## Governance Rules (from GOVERNANCE_PROTOCOL.md)

1. **Absolute path verification** — confirm file paths exist before operating on them
2. **End-to-end handshake** — after any model/provider change, verify the full request→response chain
3. **Pure state integrity** — no side effects in React component constructors or render paths
4. **Zero-fluff errors** — surface raw tracebacks; never swallow exceptions into generic messages
5. **Payload purity** — strip front-matter/metadata noise from AI inputs via fuzzy-match filters
6. **SDK Sovereignty** — `google-genai` v2 only (see above)
7. **Anti-Generic Mandate** — specific error paths only; no "Something went wrong" catch-alls
8. **Mask Destruction Protocol** — no path optimism; validate real state, not assumed state

## Key Constraints

- **Browser**: Microsoft Edge only for the desktop WebView
- **Vision models**: Groq `llama-3.2-90b-vision` or Gemini via `google-genai` v2 — no other models for OCR tasks
- **Hardware safety**: `sovereign_guardrails.py` enforces RAM/CPU thresholds; do not bypass kill switches
- **API keys**: Stored in `backend/.env`; synced to frontend localStorage at runtime — never hardcode
This project is for Bennett Consulting. The priority is 100% literal accuracy and reliability over cleverness.
