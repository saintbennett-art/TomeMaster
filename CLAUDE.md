# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tome-Master** is a local-first manuscript editor with AI-powered literary analysis. It runs as a desktop app (PyWebView wrapper) or in the browser: a FastAPI backend (dynamic port) and a Next.js frontend (port **3333**). This project is for Bennett Consulting. The priority is **100% literal accuracy and reliability over cleverness**.

## Running the App

**Full launch (both servers + port handshake)**:

```bat
Start_TomeMaster.bat
```

**Backend only** — `run.py` claims a free OS port, writes it to `.sovereign_port`, and starts uvicorn on it (zero hardcoded port):

```powershell
cd backend
.\venv\Scripts\activate
python run.py
```

**Frontend only** (dev server on 3333):

```powershell
cd frontend
npm run dev
```

**Desktop app (PyWebView)** — spawns FastAPI on a free port, opens an Edge WebView with `?api_port=` injected:

```powershell
cd backend
.\venv\Scripts\activate
python desktop_app.py
```

## Running Tests

Automated suite (pytest) lives in `backend/tests/` — contract (frontend↔backend route parity), security (path traversal, key masking, upload rejects), and export round-trips:

```powershell
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -q
```

`backend/dev/` holds ad-hoc diagnostic scripts; several are stale (they reference functions that no longer exist) — do not treat them as a test suite.

## Building the Executable

The frontend compiles to a static export (`next.config.ts` → `output: 'export'` → `frontend/out/`), which the backend serves. Build the frontend first (`npm run build`), then:

```bat
build_exe.bat
```

PyInstaller bundles the backend into a standalone `.exe`.

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI app; registers routers, CORS (localhost regex), a Windows console guard (`stdout/stderr errors="replace"` — cp1252 consoles otherwise crash `print()` on em-dashes/arrows and have aborted worker pipelines), and vault key hydration at startup.
- **`routers/`** — thin HTTP layer; delegate to services immediately:
  - `boardroom.py`, `vault.py`, `system.py` — all mounted under `/api/v1/analysis` (AI specialists, key/model management, telemetry).
  - `document.py` (`/api/v1/document`) — upload, export, native pickers (`target`/`load`), `read`, `photo`.
  - `transcribe.py` (`/api/v1/transcribe`) — the **single** transcription surface (start, status, abort, clear, resolve, offset, resort, ingest, start-pipeline).
  - `ai.py`, `settings.py`, `license.py`.
- **`services/`** — business logic:
  - `ai_service.py` — **canonical** brand-agnostic gateway dispatcher (`_call_standard_gateway` / `_call_anthropic_gateway`); the boardroom specialist functions (`run_boardroom_parallel`, `run_structural_analysis_async`, …) live here. Logs token usage to the ledger.
  - `settings_service.py` — encrypted-vault load/save + dynamic role→model resolution (`get_model_for_role`, `_resolve_auto_model`, `_ROLE_RANKING`). "auto" means query the live model list and rank per role — no hardcoded model names.
  - `parsers/` — DOCX/PDF/TXT/EPUB ingestion package.
  - `exporter.py` — DOCX/EPUB/PDF export.
  - `transcriber_service.py` — facade re-exporting the `services/transcriber/` submodules.
  - `services/transcriber/ocr_job.py` — the direct OCR transcription loop (smart text-parse vs vision-OCR + spectrum failover); honors the `TRANSCRIPTION_ABORT` event.
  - `security.py` — `validate_project_path` (home-directory guard). **Use it on every endpoint that accepts a folder/path.**
  - `logger_service.py` — appends to `api_usage_log.jsonl`.
- **`desktop_app.py`** — PyWebView wrapper.

### CrewAI (optional, not the analysis path)

`src/tomemaster/crews/` holds CrewAI agents. The boardroom analysis path was **reverted to the direct gateway** — CrewAI is reachable only via `POST /api/v1/transcribe/start-pipeline` and requires `pip install "crewai[tools]"` (deliberately **not** in `requirements.txt`). Do not reintroduce a hard `crewai` import on the boot path.

### Frontend (`frontend/src/`)

- **`context/WorkstationContext.tsx`** + **`context/EditorContext.tsx`** — global state stores.
- **`lib/apiClient.ts`** — centralized API client; all backend calls go through here.
- **`types/industrial.ts`** — shared type source of truth (Chapter, TranscriptionStatus, etc.).
- **`lib/migration_gate.ts`** — `performMasterMigration()` runs on load for localStorage schema migration.
- **`lib/vault.ts`** — `secureVault` is a **deprecated stub** (returns `{}`); keys live backend-side, never in the browser.

### Storage

- **Keys/settings**: encrypted vault `settings.enc` (Fernet, derived from the machine fingerprint) via `src/tomemaster/vault_loader.py`; hydrated into env vars at startup. `GET /api/v1/settings/` returns keys **masked**; `/api/v1/analysis/vault-sync` returns presence booleans only.
- **Manuscript content**: IndexedDB (frontend).
- **Usage ledger**: `api_usage_log.jsonl` — append-only, per AI call (provider, model, tokens).

### AI Provider Wiring

Model selection is **dynamic** (`settings_service.get_model_for_role` + `_ROLE_RANKING`), resolved from whatever the user's API keys can access; failover cascades through `ai_service`. Rough role intent:

| Role | Tier |
|---|---|
| Structural analysis / chapterization | reasoning (Gemini Pro › GPT-4o › Claude Sonnet) |
| Copy editing / prose critique | linguistic fidelity (Sonnet / Gemini Pro) |
| Transcription / OCR / vision | multimodal Flash / vision models |

**SDK rule**: use `google-genai` v2 (`from google import genai`) exclusively — never the legacy `google-generativeai` v1.

## Governance Rules (from GOVERNANCE_PROTOCOL.md)

1. **Absolute path verification** — confirm file paths exist before operating on them.
2. **End-to-end handshake** — after any model/provider change, verify the full request→response chain.
3. **Pure state integrity** — no side effects in React component constructors or render paths.
4. **Zero-fluff errors** — surface raw tracebacks; never swallow exceptions into generic messages or fake success.
5. **Payload purity** — strip front-matter/metadata noise from AI inputs.
6. **SDK Sovereignty** — `google-genai` v2 only (see above).
7. **Anti-Generic Mandate** — specific error paths only; no "Something went wrong" catch-alls.
8. **Mask Destruction Protocol** — no path optimism; validate real state, not assumed state.

## Key Constraints

- **Browser**: Microsoft Edge only for the desktop WebView.
- **Vision models**: vision-capable Gemini (via `google-genai` v2) or Groq vision models — no text-only models for OCR.
- **API keys**: stored in the encrypted vault (`settings.enc`) and hydrated to env at startup — never hardcode, never return raw over the wire.
- **Paths**: every folder/path-accepting endpoint must go through `services.security.validate_project_path`.
