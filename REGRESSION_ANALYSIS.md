# Regression Analysis — How TomeMaster Got Broken

**Goal:** identify what changed since the last known-good state and restore each broken feature.
**Method:** git history (facts, not impressions). All timestamps from `git log`.

---

## 1. The decisive fact: git starts AFTER the golden build

- The user's confirmed working build was **2026-03-29 ~08:04** (PRoeditor, 11th manuscript: transcription+stitching done externally with Gemini, spelling, chapter structure, TOC in the left sidebar + TOC movement, all board members incl. Emotional ARC and pacing — all working).
- **Git tracking began 2026-05-01 (`2f65f3e` "Initializing project state under Git control").** There are **no commits before that.**
- So the exact March-29 build is **not in git**. The earliest tracked snapshots (May 1–3) are the closest preserved working state.

## 2. Attribution (corrected from the record)

Not a single saboteur — a chain of AI refactors on a working base. **Note: git author fields show the user's identity (`St. Bennett`/`saintbennett-art`), but these commits were AI agents acting under that identity, not the human.**
- **Antigravity Gemini** built the original (pre-git, March) — the working version.
- **Antigravity Gemini also went off-guardrails on `42b4147` (2026-05-10)** — ignoring the sovereign guidelines and "cleaning up" working code for no reason. This is the commit that broke launch stability **and** deleted the working manuscript autosave/restore (see §4). Committed under the `St. Bennett` identity; the human did not write it.
- The **other May rewrites that broke it were mostly `Viktor AI`**, merged under the `saintbennett-art` account.
- **Claude-code (June "P0–P3")** did the recovery — and also added new layers.

## 3. Original working architecture (May 1–3 snapshots)

- **Launch:** fixed port `8080`, `uvicorn main:app --reload`. Stable.
- **Transcription:** ONE 1,561-line monolith `transcriber_service.py` with `run_transcription_job` — the working OCR/stitch engine.
- **Boardroom:** **direct raw `httpx`** calls to specialists (the board members that produced the good ARC/pacing results).
- **Models:** simple/direct selection.

## 4. The destructive change-sets (chronological)

| When | Commit / Author | Change | Damage |
|---|---|---|---|
| 2026-05-10 | `42b4147` "r-tc-br" (Antigravity Gemini, committed under St. Bennett identity) | Added **`run.py` dynamic-port handshake**, rewrote launcher (+gov-cloud/governance docs), **and rewrote `WorkstationContext.tsx` (737 lines)** | **Launch instability** — port changes every restart → "backend disconnects on refresh." **AND the same rewrite DELETED the working manuscript autosave/restore** (`saveCompressed`/`loadCompressed<string>` of `tome_master_draft_html`/`_text` + TOC/reports/ARC/title/author/cover) → **empty-on-reload data loss.** The autosave was real and worked (carryover from the Mar-29 golden build); only the separate "Save Snapshot" button was ever a no-op 1×1-PNG stub. |
| 2026-05-18 | `af1d35a` | "restore missing dispatchers" | AI routing already breaking |
| 2026-05-21 | `dd28c45` (St. Bennett) | Introduced **CrewAI scaffolding** (`src/tomemaster/crews/`), celery removal | Parallel CrewAI architecture begins |
| 2026-05-22 | `fff53af` (Viktor) | **Dynamic model routing** — +266 lines in `settings_service.py`, replaced simple model choice with **live `/models` discovery** | **Slow transcription start** (~10s `/models` queries) |
| 2026-05-30 | **PR#13 `ddfa802`** (Viktor AI) | **Deleted the 1,561-line working transcriber monolith** (−1,437), split into 5 modules; removed `run_transcription_job` | Rebuilt the working OCR/stitch engine → source of **transcription lock/freeze** |
| 2026-05-30 | **PR#15 `2875e22`** (saintbennett-art) | **Replaced raw-httpx specialists with CrewAI agents**; gutted `ai_service.py` (−178), +825 lines CrewAI | **Replaced the working board members** (ARC, pacing) |
| 2026-05-30 | PR#14/#16/#17 | Wired dynamic models into CrewAI; split `analysis.py` + `document_parser.py` | More wiring to break |

## 5. The fatal flaw

PRs #13–#15 replaced **working code** (monolith transcriber + httpx boardroom) with **CrewAI** — but **`crewai` was never added to `requirements.txt`/installed.** The backend became **unbootable**; boardroom + transcription died.

## 6. What the June recovery did (and didn't)

- **P0–P1 (Jun 12):** restored **direct-gateway boardroom** + **direct OCR transcription** (un-broke the CrewAI damage). ✅
- **But** restored *into the modularized structure*, not the monolith → modular **lock/threading + slow dynamic discovery** remained.
- **P3 (Jun 14):** added new layers (provider registry, modality, sovereign lock) — useful, but more complexity.

## 7. Stability fix applied 2026-06-15

Reverted the launch to the **original working method**: fixed port + `--reload`
(`uvicorn main:app --reload --host 127.0.0.1 --port 8000 --timeout-keep-alive 300`).
Backend stays on one port; code changes auto-apply. No more `.sovereign_port` churn.
Frontend: `npm run dev` (3333). Open `http://localhost:3333/?api_port=8000`.

## 8. Restoration plan — feature by feature (one feature's code at a time)

Status legend: ⬜ not started · 🟡 in progress · ✅ verified working by user

| # | Feature (existed & worked Mar 29) | Status | Notes |
|---|-----------------------------------|--------|-------|
| 0 | Launch stability | ✅ | fixed port + reload (this doc §7) |
| 1 | AI gateway / Boardroom handshake (foundation for all specialists) | ⬜ | 3 keys sealed; verify a real specialist call returns content |
| 2 | Board members — full panel | ⬜ | |
| 3 | Emotional ARC | ⬜ | |
| 4 | Pacing analysis | ⬜ | |
| 5 | Transcription + stitching | ⬜ | carries lock/freeze + slow discovery |
| 6 | Chapter structure defined + placed | ⬜ | frontend |
| 7 | TOC build + left sidebar + TOC movement | ⬜ | frontend |
| 8 | Spelling features | ⬜ | frontend |
| 9 | Manuscript autosave + restore (silent, crash-safe) | 🟡 | deleted by `42b4147`; re-grafting `saveCompressed`/`loadCompressed` into `EditorContext`/`WorkstationContext` (cloud PR in flight). NOT the "Save Snapshot" button (always a stub). |

**Rule:** work strictly within ONE feature's code per step; do not modify out-of-feature code. Nothing is reported "fixed" until the user confirms it live.
