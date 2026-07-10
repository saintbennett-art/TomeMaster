# Tome-Master — Verify & Rebuild Tracker

One-page dashboard for the verify-and-test pass on `fix/p0-direct-gateway`.
Each module runs the same ritual: **Discern → Gap list → Plan → Implement → Test → Lock down → Gate.**
Out-of-scope code stays untouched per module. Modules are locked for transferability to future projects.

Legend: ⬜ not started · 🟡 in progress · ✅ locked (gated closed) · ⚠️ blocked

---

## Module order (manuscript data flow)

| # | Module | State | Notes |
|---|--------|-------|-------|
| 0 | **Key/Model substrate** (keys, secure storage, dynamic model discovery, gateway) | 🟡 | Wave 1 fixes done + 33 tests green. Wave 2 (universal endpoint ladder, zero-maintenance) planned below. Awaiting live-key handshake before gate. |
| 1 | OCR/PDF transcription engine | 🟡 | Discerned 2026-06-14 (read-only). Well-built; found a Wave 2 regression (G1) + packaging/honesty gaps. Plan below. |
| 2 | Chapter structure build + TOC + heading↔TOC-sidebar linkage | ⬜ | |
| 3 | Spellchecker + persistent local dictionary (user-flagged words) | ⬜ | |
| 4 | Grammar analysis + accept/reject change verification | ⬜ | |
| 5 | Boardroom (user-chosen AI) → publisher-ready manuscript | ⬜ | Depends on 0–4. |

---

## Module 0 — Key/Model substrate

**Files (module boundary):**
`backend/services/settings_service.py`, `src/tomemaster/vault_loader.py`,
`backend/services/ai_service.py` (gateway + discovery), `backend/routers/vault.py`,
`backend/routers/settings.py`. (`backend/services/vault_steward.py` → retired.)
`get_key.py` (root) supplies the machine fingerprint for vault encryption.

**Public interface (don't break):**
`get_model_for_role(role) -> {url,key,model,provider}` · `get_api_key(provider)` ·
`save_settings(dict)` / `load_settings()` · `_resolve_auto_model(role)` ·
one canonical model-discovery fn · `detect_provider_from_key(key)` (new).

### Discerned state
Core design is sound and matches CLAUDE.md: gateway dispatcher is brand-agnostic,
`"auto"` truly queries a live `/models` endpoint and ranks per role, Anthropic adapter
branches to `/messages`, ledger logs tokens, keys masked on the wire, vault is real Fernet.
This is tightening, not a rewrite.

### Findings
| # | Sev | Finding | Status |
|---|-----|---------|--------|
| F1 | High | Live key-save path was the **deprecated plaintext-`.env` writer** (`vault_steward`); root `.env` not gitignored. | ✅ `/vault-save` + `/vault-sync` now go through encrypted vault only; `vault_steward` deleted; root `.env` + `.env.*` ignored. |
| F2 | High | **Three divergent model-discovery impls** (urllib / httpx / SDK); only SDK is v2. | ✅ Unified per lane: `_fetch_model_list_sync` handles every provider (incl. anthropic); shared portfolio constant. |
| F3 | Med | **Stale, inconsistent hardcoded Anthropic portfolios** in 3 places; `/v1/models` now exists. | ✅ Single `ANTHROPIC_STATIC_PORTFOLIO`; anthropic now queried live via `/v1/models` with static fallback; ranking ids refreshed. |
| F4 | Med | **"Parse the key → detect provider" not implemented** (provider is picked manually). | ✅ `detect_provider_from_key()` added (supplements explicit choice). |
| F5 | Low | Model cache thrashes with multiple providers (single global slot). | ✅ Cache now keyed per provider. |
| F6 | Low | `validate-key` timeout message lies (code 60s / msg "30s" / doc 15s). | ✅ Message states real timeout + true cause (provider endpoint, not "local CPU"). |
| F7 | Low | Hardcoded emergency fallbacks + hand-maintained ranking will go stale. | 🟡 Acknowledged — ranking is a *preference order* intersected with live discovery; refresh path documented here. Not "fixed", by design. |
| F8 | Info | `slot_primary/specialist/velocity` half-implemented — keep or drop (decision pending). | ⬜ Left as-is (non-breaking); **your decision**. |
| F9 | Low | Untracked diagnostic artifacts not gitignored (`audit_gemini-*.json`, etc.). | ✅ Ignore patterns added. |
| F10 | Low | `inject_keys_to_env` prints "API keys restored" even when the vault holds no keys. | ⬜ Minor honesty nit; noted, not yet fixed. |

**Tests:** `backend/tests/test_substrate.py` — 19 offline tests (detection, resolution ranking/fuzzy/first-available/no-key, per-provider cache, single Anthropic source, vault round-trip, masking). Full suite **33 passed**. Real `settings.enc` never touched (vault + net stubbed).

### Implementation plan
1. Unify key-save onto the encrypted vault; stop writing plaintext `.env`; `vault-sync` reads vault. Retire `vault_steward`. (F1)
2. Collapse discovery to one canonical fn; single Anthropic portfolio (`/v1/models` + static fallback). (F2/F3)
3. Add `detect_provider_from_key()`; auto-route when provider not given. (F4)
4. Per-provider cache; honest timeout message. (F5/F6)
5. gitignore artifacts (F9); decide slots (F8).
6. Lock down module + "don't break" list.

### Testing plan
**Now (offline, no key):** provider detection over 4 key formats; `_resolve_auto_model` with
monkeypatched portfolio (ranking/fuzzy/first-available); cache non-eviction; vault save→load
round-trip + masking never leaks; `vault-sync` reflects vault after save.
**Later (live key):** `/validate-key` real portfolio per provider; `/resolved-models` real per role;
one real boardroom call → content + ledger entry; one-page Gemini vision-OCR smoke test.

### Wave 2 — Universal endpoint resolution ("the ladder")
**Goal:** support any engine the user has a key (or localhost) for, with **zero forced
developer maintenance**. Everything is "an OpenAI-compatible endpoint + optional key";
the only variable is *how the app learns the endpoint*. Models are ALWAYS discovered live
from `<endpoint>/models` — no hardcoded model lists anywhere.

**The ladder (one resolver, four ways to find the endpoint):**
1. **Known cloud brand** (OpenAI, Anthropic, Google, Groq, xAI, OpenRouter) → **key only**;
   endpoint from distinctive key-prefix auto-detect or a dropdown pick.
2. **Exotic / OpenAI-compatible cloud** (Kimi, DeepSeek, Together…) → **key + base URL**
   (the one fact a `sk-…` key can't carry). Optional name→URL convenience seeds auto-fill
   popular ones; novel ones just type the URL.
3. **Local engine** (Ollama, LM Studio, vLLM, llama.cpp/BitNet) → **nothing** — auto-probe
   known localhost ports (11434 / 1234 / 8000 / 8080), no key, list whatever responds.
   Non-default/LAN setups reuse the same base-URL field.
4. **User-defined custom provider** → persisted `{label, base_url, key}` in the vault; flows
   through the same registry + universal adapter. This is what makes it self-service.

**Build items:**
- **B1. Provider registry (data, not scattered code):** collapse the ~6 places that currently
  redefine endpoints/auth/prefixes/env-vars into ONE table `{base_url, discovery_path,
  auth_style, key_prefix, env_var, label}`. Internal refactor, no behavior change. Backbone
  for everything below + the transferable unit.
- **B2. `resolve_endpoint(key?, provider?, base_url?)`** implementing the ladder.
- **B3. Fix the `sk-` mis-route:** bare `sk-…` resolves to `openai-compatible (needs base_url)`,
  NOT silently `openai` — never hit the wrong server. (Amends F4.)
- **B4. Local auto-probe** on startup/health (safe: localhost, keyless, instant). Reuses the
  existing `BITNET_HOST` + localhost health-ping bones.
- **B5. User-extensible custom providers** in the vault + Settings UI field.
- **B6. Optional name→URL convenience seeds** (Kimi/DeepSeek/Together) — additive, never
  load-bearing; stale = user types URL.

**Zero-maintenance guarantee:** every rung falls back to user self-service, so the app keeps
working for any provider with no dev release. The only thing that can go stale is the *convenience*
built-in table (rare, ~multi-year, non-breaking).

**OPTIONAL — onboarding refresh (decision pending, user idea):** at purchase/onboarding (email
captured), optionally fetch a refreshed provider-config JSON so convenience updates can be pushed
centrally **without a reinstall**. Trade-off: adds a hosted config + a network dependency + a mild
supply-chain surface (weigh against the local-first/sovereign posture + prior leak history). The
baked-in default always works offline regardless. Recommend: keep OPTIONAL and consent-gated.

**Wave 2 tests (offline):** registry lookup; ladder resolution for each of the 4 cases; `sk-`
ambiguity fix; custom-provider vault round-trip; local-probe against a mocked localhost responder;
assert no hardcoded model id is ever returned without discovery.

**Wave 2 status (2026-06-14): backend DONE — 47 tests green.**
- ✅ B1 registry → `backend/services/providers.py` (standalone module, imports only `os`; pin tests guard byte-identical URLs). The ~6 scattered endpoint tables now source from it.
- ✅ B2 `resolve_endpoint` ladder · ✅ B3 base_url-wins fix (Kimi sk-+URL routes correctly) · ✅ B6 convenience seeds.
- ✅ B4 `probe_local_engines` (logic + mock test) · ✅ B5 custom-provider vault storage + sanitize + round-trip.
- ✅ **Frontend wired (2026-06-14):** `GET /analysis/local-engines` endpoint; `SettingsModal` "Local & Exotic Engines" panel — auto-scans localhost on open, lists detected engines, and an "Add OpenAI-compatible endpoint" form (label+URL+key) that validates via `/validate-key` (custom_url) and persists to `custom_providers`. `/list-models` now honors `custom_url`; custom-provider keys masked in `GET /settings/`. tsc 0 errors, 47 tests green.
- ✅ **Selected local/custom engine drives analysis (2026-06-14):** `get_model_for_role` now falls back to a user custom endpoint or a running local engine when no cloud key is present (`_resolve_local_or_custom_endpoint`, cached probe). So a keyless local model (BitNet/Ollama) can run the boardroom fully offline. Cloud key, when present, always wins (tested).
- ⬜ **Deferred to live pass:** live-key (or live local engine) handshake to GATE the module closed.
- 🟡 **BitNet viability (user TODO):** no local LLM installed yet. App wiring exists end-to-end (probe detects :8080, keyless sentinel, gateway routes, resolution fallback). **Division of labor (refined):** local model is viable for *retrieval/consistency* work the SYSTEM feeds it — web-research summarize, character-bible continuity checks (these are tooling problems: fetch + vector store + diff, model reasons over supplied context). NOT for vision/OCR (not multimodal) and weak on nuanced prose/voice critique (needs raw model strength → cloud). Design toward: local = retrieval+consistency, cloud = creative judgment. Needs user to run bitnet.cpp to evaluate.
- **Decision locked:** self-service only — no hosted config/onboarding-refresh (clean seam left if ever wanted).
- **Portability:** `providers.py` is dependency-free (only `os`) → drop-in reusable in any future project.

---

## Module 1 — OCR/PDF transcription engine (discerned 2026-06-14, read-only)

**Files:** `routers/transcribe.py` (HTTP surface), `services/transcriber_service.py` (facade),
`services/transcriber/ocr_job.py` (the loop), `…/vision_processor.py` (parse-vs-rasterize),
`…/ai_engine.py` (vision model calls + spectrum failover), `…/asset_scanner.py`,
`…/artifact_steward.py`, `…/industrial_stitcher.py`.

**Flow (verified):** `/transcribe/start` → `get_model_for_role("TRANSCRIBER_LEAD")` (+ groq fallback)
→ daemon thread → `run_transcription_job`. Per asset: scan → **smart routing** (`is_parseable_document`:
.docx/legacy/text-layer-PDF → free `parse_document_text`; else rasterize) → vision OCR via
`_call_ai_with_failover` (primary → groq fallback, 3 retries + backoff) → parse `<page><number><text>`
→ save RTF artifact → atomic fsync cache commit → archive source → final `resort_from_cache` stitch.
Up to 3 async workers; abort checked between assets/pages; SDKs: gemini `google.genai` v2 ✓, openai/groq
openai SDK, anthropic SDK.

**Verdict:** genuinely well-built — smart routing saves credits, failover+backoff, atomic writes,
honest error states, filename-sequence-wins fidelity, corrupt-asset isolation. This is tightening, not repair.

### Findings
| # | Sev | Finding |
|---|-----|---------|
| **G1** | **High** | ✅ **FIXED (2026-06-14) via modality-driven selection.** Was a Wave 2 regression: local fallback picked `models[0]` with no capability check, so OCR could land on a text model. Now selection is **modality-driven** — `providers.required_modality(role)` (OCR→image) is matched against the model's modalities (`providers.model_modalities`: Ollama-reported via `/api/show`, else inferred by general rule). Vision roles skip text-only models, cloud + local alike. **`_ROLE_RANKING` is now subordinate to a modality hard-gate** (no longer the gate). Proven by `test_local_ocr_picks_vision_skips_text`. |
| **G1b** | High | **Remaining for full-local OCR to *execute*:** `ai_engine._get_ai_client` only knows providers by name (gemini/openai/groq/anthropic) — it has **no `local`/`custom` branch**, so even after selecting `gemma4:e2b` the OCR call returns `client=None`. Needs: route `local`/`custom` (and any OpenAI-compatible base_url) through the OpenAI SDK with `base_url=`, and thread the resolved `url` from the router → `start_transcription_background` → `run_transcription_job` → `_call_ai_with_failover`. Invasive (touches the live OCR loop) — deferred to do carefully, not under time pressure. |
| G2 | Med | `anthropic` is imported by `ai_engine` (Claude vision path) but **not in `requirements.txt`** (present on this machine by luck). Clean install → ImportError if user picks Claude for OCR. Add it, or guard the import with an honest message. |
| G3 | Med | Router hardcodes the spectrum fallback as `groq` + `get_preferred_model("logic")` — a *logic* model id (often a gemini-flash id) handed to the **groq** provider. Fallback should resolve an actual groq **vision** model (or use the role ranking's own failover). |
| G6 | Low | OCR calls log `{"total_tokens": 0}` always — ledger undercounts OCR cost (latency only). Vision responses do carry usage (`usage_metadata` / `res.usage`); capture it (the 0425830 telemetry-honesty work fixed boardroom, not OCR). |
| G4 | Low | `ai_engine` prints "BOARDROOM PULSE / Spectrum…" inside the OCR engine — copy-paste from boardroom; misleading logs. |
| G5 | Info | `pytesseract` in requirements but unused in the loop — possibly dead/legacy, or an un-wired offline-OCR option. Confirm + drop or wire. |
| G7 | Info | Vision path never run against a real API (standing blocker). The **smart-text-parse path is offline-testable now** (sample .docx/text-PDF, no key) — free coverage. |

### Implementation plan
1. **G1 ✅ DONE** — modality-driven selection (`providers.required_modality` / `model_modalities` / modality gate in `_resolve_auto_model` + `_resolve_local_or_custom_endpoint`). Docs: `LOCAL_SOVEREIGNTY.md` (hardware tiers + how selection works); CLAUDE.md links it.
2. **G1b (next):** thread `base_url` so `ai_engine` can actually *call* a local/custom OpenAI-compatible vision model — without this, full-local OCR selects but can't execute.
3. **Cloud `_ROLE_RANKING` retirement (agreed):** modality is now the gate; ranking is a subordinate tiebreak. End state = user-pin-or-first-modality-capable (no name list at all). Sequenced after G1b; ideally verified with a cloud key since it changes tested cloud-pick behavior.
4. G2: add `anthropic` to requirements (or guard import).
5. G3: resolve a real groq vision model for the fallback (or drop the hardcoded groq path).
6. G6: capture real vision token usage into the ledger.
7. G4/G5: fix misleading logs; confirm/remove `pytesseract`.

**Modality work tests (offline):** `test_required_modality_map`, `test_infer_modalities`,
`test_local_ocr_picks_vision_skips_text`, `test_local_text_role_takes_first_text`,
`test_cloud_auto_excludes_non_vision_for_ocr`, `test_cloud_auto_keeps_vision_for_ocr`. Suite: **63 green.**

### Testing plan
- **Now (offline, no key):** `is_parseable_document` classification (.docx→True, scanned-PDF→False via text-layer threshold, image→False); `parse_text_docx`/`parse_text_pdf` emit `<page>` tags from a sample file; the `<page><number><text>` extraction regex; vision guard skips non-vision models; **G1 guard** (OCR never selects a non-vision engine).
- **Later (live key):** one scanned page → vision OCR → RTF + stitched manuscript; failover (kill primary) → groq vision; abort mid-job.

---

## Licensing / activation (fixed 2026-06-14)
- **Root cause of "reverted to new install":** `LICENSE_FILE` was a **relative path**, so `is_activated()` read `tome_master.lic` from whatever dir the app launched from. A stale `.lic` (old machine_id `de16c29f…`) sat at the project root while the correct one (`4d04765d…`) was in `backend/` → root launches looked unactivated.
- **Fix:** `license_service._resolve_license_path()` — absolute anchor (frozen → next to the .exe; source → project root). Stale root `.lic` re-synced to the current machine_id; orphan `backend/tome_master.lic` removed. `is_activated() → True`.
- **Activation paths:** (1) machine key from `get_key.py` (`TOME-XXXX-…`, this machine = `TOME-FFF3-A7A4-A980`); (2) **universal master code** = the `TOME_MASTER_KEY` env var (no hardcoded value by design). Set to `BENNETT-TOME-MASTER-2026` (User scope) — change to a private secret; takes effect on app restart.

## Standing security / hygiene state (verified 2026-06-14)
- Git history, dangling blobs, current tree: **clean of provider key patterns**. Prior scrub held; flagged keys since expired. No live exposure.
- Branch pushed to `origin` (github.com/saintbennett-art/TomeMaster) up to `c6284f1`; local ahead by 2 unpushed commits (`9440c16`, `4d4b533`). **OPEN: confirm repo public vs private.**
- Vault currently holds **no keys** (user deleted after GitSecure alert). Live tests await a fresh key.
- Untracked diagnostic artifacts present but **not committed** — keep out of staging (F9 adds ignore patterns).
