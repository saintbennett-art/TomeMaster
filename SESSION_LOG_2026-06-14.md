# Session Log — 2026-06-14

Tome-Master · branch `fix/p0-direct-gateway` · model: Opus 4.8
Outcome: **Module 0 (key/model substrate) Wave 1 + Wave 2 — code-complete, 50 tests green, committed `ab78fa0`.**

---

## 1. Context at start

- Resuming the recovery branch. A prior session had completed the direct-gateway recovery backlog (10 commits) plus two later commits (dynamic launcher, lazy-load PII).
- User flagged: Fable 5 removed from public access (US Gov / jailbreak concern); now working on Opus 4.8.
- Goal for the session: a **verify-and-test pass** across 6 modules in manuscript-data-flow order:
  0. Key/Model substrate → 1. OCR/PDF → 2. Chapter structure + TOC → 3. Spellcheck + persistent dictionary → 4. Grammar accept/reject → 5. Boardroom (publisher-ready).
- Hard constraints (user + governance): literal accuracy over cleverness; don't break out-of-scope code; lock each module down as a **portable, transferable** unit; `google-genai` v2 only; every path-accepting endpoint guarded.

## 2. Discussions that shaped the work

These conversations drove the architecture — recorded because the *reasoning* matters as much as the code.

- **Jailbreaks (conceptual):** mechanism-level taxonomy (role-play, hypothetical framing, encoding, crescendo, refusal-suppression, many-shot) vs. **prompt injection** (third-party instructions hidden in processed content). Noted the latter is the one directly relevant to Tome-Master (manuscripts feed the AI), which is why the **payload-purity** governance rule is a security control.
- **"Why maintain a provider list on every user's machine?"** Separated two things: (a) **model lists** — should NOT be local; discovered live from each provider's `/models` (the key determines availability); (b) **connection metadata** (URL + auth per provider) — small, near-static, irreducible; *something* must hold it. Rejected LiteLLM (heavy dep, violates SDK-sovereignty) and OpenRouter (routes private manuscripts through a third party) in favor of a tiny local registry.
- **"Surely the URL is discernible from the key?"** Honest answer: **no** for the exotic/clone ecosystem — Kimi/DeepSeek/etc. deliberately mimic OpenAI's `sk-…` format, so the key is ambiguous. But you don't *need* to derive it: everything exotic is OpenAI-compatible, so the user supplies the one fact a key can't carry — the **base URL** — and one generic adapter handles all of them.
- **"Does the dev update the table once a year?"** Realistically less — base URLs have been stable 2–3 years. Changes are **event-driven** (you choose to add a provider) not calendar-driven. Made it **user-extensible** so the dev basically never has to.
- **Local engines (Ollama/LM Studio/vLLM/BitNet):** the *easiest* case — keyless, well-known localhost ports, safe to auto-probe (localhost, no key leaves the box). User enters nothing unless non-default.
- **Decision (locked):** **self-service only** — no hosted config, no purchase-email onboarding refresh. Every rung degrades to user self-service, so **zero forced developer updates**. A clean seam was left if the refresh is ever wanted.
- **BitNet viability:** corrected an oversimplification. A small local model is more than a spellchecker *when the system carries the load* — web research (fetch+summarize) and character-consistency (bible + retrieval + diff) are tooling problems the model reasons over. It stays weak on nuanced prose/voice critique and **cannot** do OCR (not multimodal). Design toward: **local = retrieval/consistency, cloud = creative judgment.**

## 3. Security / hygiene verification

- User had deleted keys after a GitGuardian/GitSecure alert (keys once in the repo).
- Swept full git history, dangling/unreachable blobs, current tree → **clean of provider key patterns**. Prior scrub held; flagged keys since expired → no live exposure.
- **Correction:** branch was believed unpushed; reflog showed it **was pushed to `origin`** (github.com/saintbennett-art/TomeMaster) up to `c6284f1`; local was ahead by 2. **OPEN: confirm repo public vs private.**
- Vault currently holds **no keys** (deliberate) — substrate work done code-only; live handshake deferred.

## 4. Module 0 — discernment findings (F1–F10)

| # | Sev | Finding | Resolution |
|---|-----|---------|-----------|
| F1 | High | Live key-save used the deprecated **plaintext-`.env`** writer (`vault_steward`); root `.env` not ignored | ✅ encrypted-vault only; `vault_steward` deleted; root `.env` ignored |
| F2 | High | **Three** divergent model-discovery impls | ✅ unified via the registry; one discovery per lane |
| F3 | Med | Stale, inconsistent hardcoded Anthropic lists (×3) | ✅ single `ANTHROPIC_STATIC_PORTFOLIO`; live `/v1/models` + fallback |
| F4 | Med | "Parse key → provider" not implemented | ✅ `detect_provider_from_key` |
| F5 | Low | Model cache thrashed across providers | ✅ per-provider cache |
| F6 | Low | `validate-key` timeout message lied | ✅ honest message |
| F7 | Low | Ranking/fallbacks go stale | 🟡 by design — preference order intersected with live discovery |
| F8 | Info | `slot_primary/specialist/velocity` half-implemented | ⬜ **user decision: keep or drop** |
| F9 | Low | Diagnostic artifacts not gitignored | ✅ patterns added |
| F10 | Low | `inject_keys_to_env` prints "restored" with no keys | ⬜ noted, not fixed |

## 5. What was built

### Wave 1 — substrate hardening
- `routers/vault.py`: `/vault-save` + `/vault-sync` rewritten onto the encrypted vault; `vault_steward.py` deleted.
- `services/settings_service.py`: single Anthropic portfolio (live-queried), per-provider cache, refreshed Claude ids, `detect_provider_from_key`.
- `services/ai_service.py`: Anthropic discovery kept honest (bad key fails, no silent fallback).
- `.gitignore`: root `.env`/`.env.*` + diagnostic artifact patterns.

### Wave 2 — universal endpoint resolution (the "ladder")
- **NEW `services/providers.py`** (imports only `os` — portable drop-in): the single connection registry; `resolve_endpoint` ladder (`base_url > seed > provider > key-prefix`); `probe_local_engines` (localhost auto-detect); convenience seeds (Kimi/DeepSeek/Together/…). The ~6 scattered URL tables now source from it — **pin tests** guard byte-identical URLs so the live gateway is provably unchanged.
- Custom OpenAI-compatible endpoints: vault storage + sanitize + **key masking**; `GET /analysis/local-engines`; `/list-models` honors `custom_url`.
- **Frontend** `SettingsModal.tsx`: "Local & Exotic Engines" panel — auto-scans localhost on open, lists detected engines, "Add OpenAI-compatible endpoint" form (label + URL + key) that validates live and persists. `apiClient.ts`: `fetchLocalEngines`, `fetchCustomProviders`, `saveCustomProviders`, `validateCustomEndpoint`.
- `get_model_for_role`: **falls back to a custom/local engine when no cloud key is present** (`_resolve_local_or_custom_endpoint`, cached probe) → keyless local model can drive analysis offline; cloud key always wins when present.

## 6. Tests & verification

- `backend/tests/test_substrate.py` (36 tests) + existing suite → **50 passed**.
- Coverage: key-format detection, role resolution (ranking/fuzzy/first-available/no-key), per-provider cache, single Anthropic source, vault round-trip + masking, registry URL pins, the 4-rung ladder, local-probe (mocked), custom-provider round-trip, and the local/custom-drives-analysis fallback (+ cloud-wins).
- Frontend: `tsc --noEmit` → **0 errors**. Contract test (frontend↔backend route parity) green.
- Real `settings.enc` never touched by tests (vault + network stubbed).

## 7. Commit

- **`ab78fa0`** — `feat(P3): provider registry + endpoint ladder; harden key/model substrate` — 11 files, +1110/−200.
- Scoped to Wave 1+2 only. **Deliberately NOT committed** (left in working tree): build refactor (`build_exe.bat`, `build_native.py` deletion, `TomeMaster.spec`), `backend/static/`, `.claude/`, diagnostic artifacts (now gitignored).
- **Not pushed** (standing user decision).

## 8. Open items / next forks

1. **Gate Module 0:** a live handshake — now achievable **keyless** by standing up bitnet.cpp / Ollama on `:8080` (doubles as the BitNet viability test), or with a fresh cloud key.
2. **F8** — keep or drop the `slot_primary/specialist/velocity` concept.
3. Confirm the **GitHub repo is public vs private**.
4. Decide next: **Module 1 (OCR)** vs. stand up a local engine vs. the build/exe work.
5. Minor: F10 honesty nit; the build refactor in the working tree is unfinished.

## 9. Artifacts produced this session
- `RECOVERY_TRACKER.md` — living one-page dashboard (per-module ritual + findings + status).
- `backend/services/providers.py` — portable provider registry + ladder.
- `backend/tests/test_substrate.py` — offline substrate test suite.
- This log.
- Memory: `portable-module-principle.md`; updated `tomemaster-recovery-state.md`.
