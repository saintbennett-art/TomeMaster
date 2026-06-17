# Local AI Job Policy (BitNet / local engines)

How TomeMaster runs local-engine inference so it stays viable on low-power, RAM-constrained
hardware (e.g. an 8 GB i5-1334U laptop) **without degrading the machine**. Pairs with
`LOCAL_SOVEREIGNTY.md` (which engine/modality is chosen) — this doc governs *when* and
*how hard* a local job runs.

## Why (the three "bites" on thin hardware)
1. **Thermal/throttle** — sustained CPU inference spins fans, throttles clocks, drains battery.
2. **UI lag** — inference contends for the few performance cores; typing can stutter.
3. **Installer bloat** — bundling ~1 GB of weights makes a heavy `.exe`.

BitNet b1.58 **2B** is the ceiling on 8 GB; it is **text-only** (no OCR/vision). In production
(no dev servers) there is ~3–4 GB headroom, so the model fits — the risk is contention, not size.

## Principle
Local inference is **opportunistic and bounded** — event-driven, single-flight, scoped, backgrounded.
The policy is an **additive** layer that wraps routing; it never rewrites the gateway
(`get_model_for_role` / `_resolve_local_or_custom_endpoint`, `settings_service.py`).

## 1. Job classification
Reuses the role→category map in `get_model_for_role`:
- **Local-eligible** (background, structured, retrieval): continuity sentinel (`run_sentinel_async`),
  research-summarize, character-bible/consistency checks.
- **Cloud-only** (always): OCR/vision (`TRANSCRIBER_LEAD`, `OCR_ENGINE` — BitNet can't), and nuanced
  creative/voice critique (boardroom prose). Non-eligible jobs bypass the gate and route as today.

## 2. The gate — `local_job_gate(job) -> RUN_LOCAL | DEFER | ESCALATE_CLOUD`
Ordered checks:
| Check | Default | Bite |
|---|---|---|
| Local engine present (`probe_local_engines`, cached) | required | correctness |
| Concurrency == 0 (one local job at a time) | max 1 | thermal + lag |
| RAM headroom ≥ threshold | ≥ ~1.8 GB free | prevents swap |
| On AC power? | heavy jobs **defer on battery** | thermal/battery |
| User toggle "local AI" enabled | required | opt-in |

Hard-check fail → **DEFER** (re-queue) for background jobs, or **ESCALATE_CLOUD** (honest
"local unavailable — use cloud?" prompt) for user-initiated jobs. Never silent-fail, never
silently spend cloud tokens. Sovereign lock still wins (forces local; honest `sovereign_blocked`).

## 3. Trigger policy (minimizes thermal — *when*)
- Never per-keystroke. Fire on **discrete events**: chapter-complete, on-save, explicit
  "Check continuity".
- **Debounce** (3–5 s) and **coalesce** duplicate pending checks.
- Optional **idle trigger**: run queued background checks only after N s of no typing.

## 4. Execution profile (minimizes lag/thermal — *how*)
- **Thread cap** (~2–4, biased to E-cores) — leave P-cores for the UI. *(bitnet.cpp launch-side;
  the app can't set it over the HTTP API — see Implementation note.)*
- **Below-normal process priority** for the inference process. *(launch-side.)*
- **Scoped context** — feed the chapter + relevant bible slice, not the whole manuscript.
- **Async/non-blocking** with status in the **Nerve Center** bar; the editor never blocks. *(app-side.)*
- **Single-flight** — at most one in-flight local job. *(app-side.)*

## 5. Insertion points (real)
- Routing unchanged: `settings_service.get_model_for_role` / `_resolve_local_or_custom_endpoint`
  (lines ~518 / ~431). The gate gates the *caller*, not these.
- New, additive: `backend/services/local_policy.py` — `classify_job()`, `local_job_gate()`,
  `exec_profile()`. Logic only (`os` / `psutil` + `providers.probe_local_engines`).
- Wire-in: local-eligible callers (start with `run_sentinel_async`, `ai_service.py:336`) consult the
  gate before dispatch. Cloud paths untouched.
- Config: `preferences.local_policy` in the vault (`enabled`, `battery_ok`, `min_free_gb`, `threads`);
  Settings UI toggle later.

## Implementation note — where thread-cap / priority actually live
bitnet.cpp runs as a **separate user-launched server** on `:8080` (the app calls its
OpenAI-compatible endpoint; it does not spawn it). Thread count and process priority are therefore
**launch-side**, not settable per HTTP request. They belong in the recommended launch command /
a launch script (and would only become app-controlled if the app ever spawns bitnet.cpp itself).
Recommended launch (tune to taste):
`llama-server -m <bitnet-2B>.gguf -t 4 --port 8080` started at below-normal priority
(`start /belownormal ...` on Windows).

## Rollout
- **A (this doc):** policy designed.
- **B (next, safe slice):** app-side execution profile only — async/non-blocking status +
  single-flight guard on the sentinel call. Thread-cap/priority captured as the launch recipe above.
- **C (later):** full gate (`local_policy.py`) + triggers + Settings toggle.
