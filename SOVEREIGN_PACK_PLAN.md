# Sovereign AI Pack — Analysis & Implementation Plan

A separately-downloadable add-on that gives a non-technical author fully-offline AI in Tome-Master with near-zero decisions. Core app stays cloud-key based; the pack brings the local engine, models, and lifecycle management.

---

## 1. GAP ANALYSIS — what exists vs. what a novice needs

### What exists today (grounded)

| Capability | Where | Status |
|---|---|---|
| Localhost engine probe (Ollama 11434, LM Studio 1234, vLLM 8000, llama.cpp/BitNet 8080) | `backend/services/providers.py:90-95` (`LOCAL_ENGINES`), `providers.py:433-456` (`probe_local_engines`) | Works, cached 5 min (`settings_service.py:474-475`) |
| Modality-driven role→model selection; OCR requires a vision model, honest refusal otherwise | `providers.py:213-222` (`ROLE_REQUIRED_MODALITY`), `providers.py:248-273` (authoritative Ollama `/api/show` capabilities), `settings_service.py:454-481` (`_resolve_local_or_custom_endpoint`) | Works for **text** dispatch |
| Sovereign Lock (force local, honest `sovereign_blocked` error) | `settings_service.py:550-559`, error surfaced at `ai_service.py:201-207` | Works |
| Keyless fallback: cloud key missing → route role to a local engine | `settings_service.py:593-596` | Works |
| Single-flight local inference lock (thermal/RAM protection) | `ai_service.py:24-36` (`_LOCAL_INFERENCE_LOCK`) | Works for gateway path |
| Ollama/BitNet status endpoints | `backend/routers/ai.py:11-60` | Read-only status only |
| Hardware audit (RAM + CPU only) | `backend/routers/system.py:253-300` (`/system-audit`, psutil) | **No GPU/VRAM detection** |
| Settings UI: "Local & Exotic Engines" auto-detect + custom endpoints | `frontend/src/components/SettingsModal.tsx:434-526`; client at `apiClient.ts:904-915`, `952-969` | Detection only — no install/pull |
| Onboarding "Sovereign" path with engine scan | `frontend/src/components/OnboardingModal.tsx:84-132`, readiness gate at `:161-184` | **Tells the user to run `ollama pull moondream` in a terminal** (`CmdRow` at `:113-131`) — disqualifying for novices |
| Packaging: PyInstaller one-file exe, dynamic free port, `?api_port=` handshake | `build_exe.bat:46-72`, `backend/desktop_app.py:9-15,80-82`; dev handshake via `.sovereign_port` (`backend/run.py:23`) | No add-on concept |

### Gaps a novice-ready pack must close

1. **No installation path** — the app can only *detect* an engine the user installed themselves. The onboarding literally instructs terminal commands (`OnboardingModal.tsx:113-131`).
2. **No model download management** — no in-app pull, no progress, no size warning, no resume. `fetchLocalEngines` returns an empty list and the UI says "Start one" (`SettingsModal.tsx:468-472`).
3. **No engine lifecycle management** — nothing spawns, supervises, restarts, or stops a local engine. `desktop_app.py` manages only uvicorn. The BitNet policy doc explicitly says the engine is "a separate user-launched server… the app does not spawn it" (`LOCAL_AI_POLICY.md:67-70`).
4. **Local vision/OCR is broken end-to-end.** The boardroom text path dispatches to local engines via `_call_standard_gateway` (`ai_service.py:230-246`), but the OCR pipeline's client factory `_get_ai_client` (`backend/services/transcriber/ai_engine.py:63-76`) **returns `None` for any provider other than gemini/openai/groq/anthropic** — a local vision model can be *selected* by `_resolve_local_or_custom_endpoint` but the transcriber can never *call* it with an image. `LOCAL_SOVEREIGNTY.md:77-79` promises "OCR roles will route to a vision model automatically" — that promise is currently unfulfilled at the dispatch layer.
5. **Hardware tiering is half-built** — `/system-audit` measures RAM/CPU only (`system.py:269-273`); the tier table in `LOCAL_SOVEREIGNTY.md:39-44` keys on **VRAM**, which is never measured.
6. **No default-model policy for local** — `_ROLE_RANKING` (`settings_service.py:220-267`) is a cloud-model list; local selection takes "first model that satisfies the modality" (`settings_service.py:476-480`), which on a machine with several pulled models is arbitrary, and on a fresh machine there is nothing to select.
7. **Failure UX** — local failures today are either silent skips (`probe_local_engines` swallows everything, `providers.py:455`) or generic ("No local engine detected… Start one"). Governance requires specific, actionable errors.

---

## 2. RUNTIME CHOICE — bundle and manage **Ollama (portable zip distribution)**

### Evaluation

| Option | Pros | Cons | License |
|---|---|---|---|
| **Ollama** (recommended) | Already first-class in the codebase (`LOCAL_ENGINES[0]`, authoritative `/api/show` capability reporting at `providers.py:248-273`, `/ollama-status` router); automatic GPU dispatch (CUDA, AMD ROCm, CPU fallback) with zero user decisions; **HTTP model-pull API (`POST /api/pull`) that streams progress and resumes interrupted downloads** — solves the entire download-manager problem; registry-hosted quantized models; single `ollama.exe` + runners in the zip release | ~1.5–2.5 GB of runtime payload (CUDA/ROCm runner DLLs); server holds models in its own store | **MIT** — redistribution of the binary in our installer is clean |
| llama.cpp / llamafile embedded | Smallest footprint; total control; MIT | We own everything Ollama gives free: GPU build matrix (CUDA vs Vulkan vs CPU exe variants), model download/resume/verify, multimodal `mmproj` pairing for vision, capability metadata (our `/api/show` integration would be dead code), process supervision | MIT |
| LM Studio | Nice GUI | **Proprietary; no redistribution license**; GUI-first conflicts with "zero decisions"; its CLI/service mode is not redistributable either | Closed |

**Decision: Ollama, shipped as the official portable zip (`ollama-windows-amd64.zip`) inside the pack installer**, not the interactive `OllamaSetup.exe`:

- Portable-module principle: the pack is one self-contained folder — `ollama.exe`, runners, a `models/` store (`OLLAMA_MODELS` env var), and a `pack.json` manifest. Reusable by any other app that speaks OpenAI-compatible + `/api/pull`.
- No conflict with a user-installed Ollama: **detect-and-adopt first** — if `probe_local_engines()` already finds Ollama on 11434, the pack manages models on that instance instead of spawning a second one. If the pack must spawn its own and 11434 is taken by a non-Ollama process, spawn on a free port (`OLLAMA_HOST=127.0.0.1:<free>`) and register it as the pack endpoint — the code already supports non-default bases via custom endpoints (`settings_service.py:462-469`).
- **GPU/CPU detection strategy:** two layers.
  - *Coarse (for tier choice, before anything is installed):* new `hardware_service.py` — RAM/CPU via psutil (already a dependency, `system.py:22`); NVIDIA VRAM via `nvidia-smi --query-gpu=memory.total,name --format=csv,noheader` (present iff driver installed); AMD/Intel via registry `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-…}\000X\HardwareInformation.qwMemorySize` (the QWORD field — do **not** use WMI `AdapterRAM`, a 32-bit field that caps at 4 GB). Read-only, no driver installs, honest "GPU: not detected — CPU mode" when probes fail.
  - *Authoritative (after engine runs):* Ollama itself decides GPU vs CPU per model; we surface what it reports (`/api/ps` shows `size_vram`) rather than pretending we know better.

**Model licenses are separate from the runtime** and are handled by *downloading at first run from the Ollama registry* (user pulls to their own machine — we never redistribute weights). See §7 for per-family license notes; the default manifest prefers Apache-2.0 families.

---

## 3. HARDWARE TIERING — auto-detect → LOCAL_SOVEREIGNTY tiers → per-role defaults

Map the probe onto the existing tier table (`LOCAL_SOVEREIGNTY.md:39-44`). The defaults live in the **pack manifest (`pack.json`), not in code** — preserving the "no hardcoded model names in code" law (`LOCAL_SOVEREIGNTY.md:13`); selection is still verified by modality via `/api/show` (`providers.py:248-273`) before any role is routed.

| Detected | Tier | Text roles (structure/copy/boardroom) | Vision/OCR role | Approx. download |
|---|---|---|---|---|
| < 4 GB RAM | **Below minimum** | — | — | — (honest refusal) |
| 4–8 GB RAM, any CPU | **Featherweight (BitNet, M6 — see §8)** | `BitNet-b1.58-2B-4T` — continuity/consistency/summary roles ONLY, chapter-scoped (§8.2) | **None — OCR stays cloud** | ~1.2 GB |
| 8–12 GB RAM, no usable GPU | Text-only (Ollama) | `qwen3:4b` (Apache-2.0) or `gemma3:1b` | **None — OCR stays cloud** (declared honestly) | ~2.5 GB |
| 12–16 GB RAM or 4–6 GB VRAM | OCR entry | `qwen3:4b` | `granite3.2-vision:2b` (Apache-2.0, built for document OCR) | ~5 GB |
| 16–24 GB RAM or 8–12 GB VRAM | Comfortable | `qwen3:8b` | `qwen2.5vl:7b` (Apache-2.0) | ~10 GB |
| 32 GB+ RAM or 16 GB+ VRAM | Best local | `qwen3:14b`+ | `gemma3:27b` or `qwen2.5vl:32b` | 20 GB+ |

*(Until M6 ships, 4–8 GB machines keep the current honest refusal — the refusal message gains one line: "A Featherweight offline mode for smaller machines is planned; today this hardware requires cloud keys.")*

- **Below minimum:** per governance and the existing precedent at `system.py:279-282` ("CLOUD MODE MANDATORY"), the pack UI refuses to install models: *"This machine has 6.2 GB of RAM. Local AI needs at least 8 GB — running it here can freeze Windows. Tome-Master will keep using cloud keys; the Sovereign Pack cannot activate on this hardware."* No fake success, no degraded stealth mode.
- **Text-only tier is explicitly labeled:** *"Your machine can run all text analysis offline. Scanned-page transcription (OCR) still needs a cloud key or a GPU upgrade."* This mirrors the hard rule at `LOCAL_SOVEREIGNTY.md:28-29`.
- Tier result is written to vault `preferences` (files-only persistence, `settings_service.py:46-55` — extend `_PERMITTED_PREF_KEYS` with `sovereign_pack` keys) and re-checked on every pack start (RAM can change; eGPU appears/disappears).
- Role mapping: after models are pulled, the pack pins them per role via existing `preferred_models` (`settings_service.py:579-584` honors pinning) — or better, leaves "auto" and relies on `_resolve_local_or_custom_endpoint`, extended to **prefer the manifest's models over "first capable"** (fix for Gap 6: change `settings_service.py:476-480` to rank pack-manifest models first, then any modality-capable model).

---

## 4. PACKAGING — how it ships, how core links to it, downloads, updates

### Shape: a separate signed installer exe + a filesystem handshake

- **`TomeMaster-SovereignPack-Setup.exe`** (Inno Setup, ~1.5–2.5 GB because it embeds the Ollama portable zip; **zero model weights inside**). Installs to `%LOCALAPPDATA%\TomeMaster\SovereignPack\`:
  ```
  SovereignPack/
    pack.json            ← manifest: pack version, engine version, tier→role→model table, min hardware
    engine/ollama.exe + runners
    models/              ← OLLAMA_MODELS store (grows at first run)
    logs/
  ```
  Rejected alternatives: **zip** (novices mis-extract, no Start-menu/uninstall entry), **MSIX** (requires store/signing pipeline and fights the loopback + child-process model).
- **Handshake (same philosophy as `.sovereign_port`, `backend/run.py:23`):** core discovers the pack purely via the filesystem — a new `backend/services/sovereign_pack_service.py` looks for `pack.json` at the well-known path (plus `TOMEMASTER_PACK_DIR` env override). `%LOCALAPPDATA%` is under the user's home, so the path passes `security.validate_project_path` (`backend/services/security.py:14-24`) — route every pack path through it anyway, per constraint.
- **Core-side integration (all additive):**
  - `sovereign_pack_service.py`: `detect_pack()`, `start_engine()` (spawn `ollama serve` with `OLLAMA_MODELS`/`OLLAMA_HOST` env, below-normal priority — realizing the launch-side recipe of `LOCAL_AI_POLICY.md:66-73`), `stop_engine()`, `ensure_models(tier)` (drives `POST /api/pull`, relays streamed progress), `status()`.
  - New router `backend/routers/sovereign_pack.py` mounted in `main.py:53-60`: `GET /sovereign-pack/status`, `POST /sovereign-pack/activate` (tier-check → confirm → pull), `GET /sovereign-pack/progress` (poll or SSE, matching the existing `/transcribe/status` polling pattern, `apiClient.ts:536-548`), `POST /sovereign-pack/deactivate`.
  - `desktop_app.py`: start pack engine after backend health (`desktop_app.py:76-78`), stop it in the shutdown path (`desktop_app.py:103-105`).
  - Registering the engine: if on the default port, `probe_local_engines` already finds it; if on a custom port, write it into vault `custom_providers` (`settings_service.py:76-87`) labeled "Sovereign Pack" so the whole existing resolution ladder works unchanged.
- **First-run model download UX:** size warning with the exact GB figure from the manifest *before* anything downloads; progress bar fed by `/api/pull`'s streamed status (layer-by-layer, resumable across restarts — Ollama verifies digests, so interrupted pulls resume for free); pause/cancel; downloads land in `models/` (files-only, no browser storage anywhere).
- **Updates:** `pack.json` carries `pack_version` + `min_core_version`; core carries `min_pack_version`. Mismatch → specific message with the download link. Engine updates ship as a new pack installer (installs over the same dir, model store untouched). Model updates are just manifest bumps + a "pull update" button. No auto-update in v1 (unsigned auto-download of exes is an AV magnet).

---

## 5. NOVICE UX FLOW — happy path + failure matrix

### Happy path ("Download Sovereign Pack" → offline boardroom)

1. **In-app entry points:** Onboarding "Sovereign — Local" path (`OnboardingModal.tsx:257-266`) and a new "Sovereign AI Pack" card at the top of the *Local & Exotic Engines* section of the Intelligence tab (`SettingsModal.tsx:434-451`). If no pack and no engine detected: one button — **"Get the Sovereign AI Pack (free, ~2 GB)"** → opens the download page. The terminal-command `SovereignInstallGuide` (`OnboardingModal.tsx:84-132`) is demoted to an "advanced" link.
2. Author downloads, runs the installer: Next → Install → Finish (option "Open Tome-Master"). No choices beyond the install button.
3. Tome-Master (running or next launch) detects `pack.json`; the card flips to **"Sovereign Pack installed — Activate"**. Activation runs the hardware audit and shows one sentence: *"Your machine: 16 GB RAM, NVIDIA RTX 3060 (12 GB). Recommended: Comfortable tier — full offline analysis + page transcription. Download size: 9.8 GB. Continue?"* One confirm.
4. Progress UI (per model, resumable). On completion the backend verifies each role resolves: call `get_model_for_role` per role and show the result via the existing `/settings/resolved-models` endpoint (`backend/routers/settings.py:64-82`) — e.g. "Boardroom → qwen3:8b (local) / Transcription → qwen2.5vl:7b (local)".
5. Card offers **"Think Sovereign — keep everything on this machine"** toggle → sets `preferences.sovereign_lock` (`settings_service.py:34`, enforced at `settings_service.py:550-559`).
6. Author opens a manuscript → Boardroom → analysis runs; the existing HUD active-engine badge shows the local model. Wi-Fi off, everything still works.

### Failure states (each with its exact, actionable message — no generic errors)

| Failure | Detection point | Message (specific + action) |
|---|---|---|
| Below-minimum hardware | activation audit | "6.2 GB RAM found; 8 GB minimum. The pack cannot run here — Tome-Master will continue with cloud keys." (Refusal, per §3) |
| Text-only hardware, user starts OCR | `sovereign_blocked` path (`ai_service.py:201-207`), message extended | "Transcription needs a vision model and your hardware tier is text-only. Use a cloud key for scanning, or upgrade to 12 GB+ RAM / a 4 GB+ GPU." |
| Download interrupted / offline mid-pull | pull stream errors | "Download paused at 43% — connection lost. It will resume from where it stopped; press Resume when you're back online." |
| Disk full during pull | check free space vs manifest before start + on pull error | "Needs 9.8 GB free on C:; 4.1 GB available. Free up space or choose the smaller Entry tier (4.9 GB)." |
| Port 11434 occupied by non-Ollama | spawn failure probe | "Another program is using port 11434. The pack switched to port {n} automatically — no action needed." (auto-heal + inform) |
| Engine crashes mid-analysis | supervisor detects exit; gateway `ConnectError` (`ai_service.py:304-305`) | "The local AI engine stopped unexpectedly (see logs/engine.log). Restarting it now — the last request will be retried once." One auto-restart; second crash → "restarted twice and failed; likely a GPU-driver issue — click to run in CPU mode (slower) or view the log." |
| Model gives empty/garbled JSON | existing robust-extract path (`ai_service.py:274-293`) | Keep the existing honest surface; append "This local model may be too small for structured analysis — the pack recommends {manifest model} for your tier." |
| User-installed Ollama already present | detect-and-adopt | Not a failure: "Found your existing Ollama with {n} models — the pack will manage models there instead of installing a second engine." |
| Pack too old / core too old | manifest version gate | "Sovereign Pack 1.2 requires Tome-Master 2.4+ — update the app / download the new pack:" + link |
| AV/SmartScreen blocks engine spawn | spawn timeout + exe missing/quarantined | "Windows or your antivirus blocked engine\ollama.exe. Restore it from quarantine or re-run the pack installer; details: {path}." |

---

## 6. PHASED IMPLEMENTATION

**M0 — Local vision dispatch fix (S, prerequisite, ships value alone).** Extend `_get_ai_client` / `_call_ai_with_failover` (`transcriber/ai_engine.py:63-76, 81-169`) so provider `local`/`custom` builds an OpenAI-compatible client against the engine's base URL and sends the existing `image_url` payload (`ai_engine.py:144-153` already speaks the right dialect — Ollama accepts it). Without this, "sovereign OCR" is fiction.

**M1 — MVP slice: detect existing Ollama + one-click in-app model pull (M).** `sovereign_pack_service.ensure_models()` + `/sovereign-pack/*` router + progress UI; hardware audit extended with VRAM (`hardware_service.py`); tier recommendation + honest refusal; onboarding Sovereign path replaces `CmdRow` terminal commands with the pull button. **No installer yet — works for anyone who has Ollama, and is the exact engine-management layer the pack reuses.** Parallelizable: backend service ∥ frontend card/progress ∥ hardware probe.

**M2 — Pack installer + lifecycle (M/L).** Inno Setup bundling the Ollama zip; `pack.json` manifest; `detect_pack()` handshake; spawn/supervise/stop wired into `desktop_app.py`; detect-and-adopt; port fallback. Parallel with M3.

**M3 — Manifest-first local selection + role pinning (M).** Rank pack-manifest models ahead of "first capable" in `_resolve_local_or_custom_endpoint` (`settings_service.py:454-481`); post-pull verification via `/settings/resolved-models`; "Think Sovereign" toggle surface.

**M4 — Failure-matrix hardening + docs (M).** Every row of §5's table implemented and tested (kill the engine mid-run, fill the disk, block the port); LOCAL_SOVEREIGNTY.md updated; pack README for non-Tome-Master reuse (portable-module deliverable).

**M5 — Signing + distribution + updates (M, mostly ops).** Code-sign both exes; version-gate handshake; download page.

**M6 — BitNet Featherweight tier (L).** CI build pipeline for a signed `bitnet-server.exe` (TL1/TL2 kernels, AVX2 + fallback variants); HTTPS downloader with Range-resume + SHA-256 verify for the MIT-licensed 2B4T GGUF; second-engine supervision in `sovereign_pack_service` using the `LOCAL_AI_POLICY.md:71-73` launch recipe (below-normal priority, thread cap); manifest role-eligibility gating per §8.2 + `local_policy.py` job gate (LOCAL_AI_POLICY phase C); featherweight UI card + extended `sovereign_blocked` messaging. Depends on M2 (supervisor), M3 (manifest ranking), M4 (failure matrix). Parallelizable internally: binary CI ∥ downloader ∥ role gating.

**Out of scope (explicit):** bundling model weights in the installer; managing LM Studio/vLLM (remain detect-only); macOS/Linux packs; GPU driver installation; auto-updating the engine; fine-tuning; CrewAI pipeline changes; any change to cloud routing (`_ROLE_RANKING` untouched). Managed BitNet is **in scope as M6**; detect-only BitNet (user-launched on 8080) remains supported throughout, unchanged.

## 7. RISKS & MITIGATIONS

1. **SmartScreen/AV on an unsigned multi-GB installer.** Highest-probability failure for novices. Mitigate: OV (ideally EV) code-signing cert for both `TomeMaster.exe` and the pack installer; the bundled `ollama.exe` is already signed by Ollama Inc. — don't strip or repack it; installer download page shows the SHA-256 and a "More info → Run anyway" walkthrough as fallback; longer term winget manifest.
2. **Multi-GB model downloads.** Mitigate: weights never in the installer; Ollama `/api/pull` gives resume + digest verification for free; explicit size + free-disk check before starting; tier choice caps size; pause/cancel.
3. **GPU driver hell.** Mitigate: never install drivers; Ollama falls back to CPU automatically; surface *its* decision honestly ("running on CPU — a page takes minutes, not seconds", matching `LOCAL_SOVEREIGNTY.md:46-49`); crash-twice → offer forced CPU mode (`OLLAMA_NUM_GPU=0` relaunch — mirrors the existing kill-switch philosophy, `system.py:303-319`).
4. **Model licensing.** Runtime is MIT (Ollama). Weights: default manifest prefers **Apache-2.0** families (Qwen3, Qwen2.5-VL-7B, Granite-3.2-vision); **Gemma** (Gemma Terms of Use — fine for user-side download, avoid redistribution) and **Llama** (community license, "Built with Llama" attribution) only as user-visible alternates, never silently defaulted; pulls come from the registry to the user's machine, so we distribute no weights; manifest records each model's license and shows it in the UI.
5. **Port/instance conflicts with user-installed Ollama.** Detect-and-adopt first; free-port spawn + custom-provider registration as fallback (both paths already supported by `providers.py:433-456` and `settings_service.py:462-469`).
6. **Low-end machines melting.** Existing single-flight lock (`ai_service.py:24`) + below-normal spawn priority + the `LOCAL_AI_POLICY.md` gate + hard refusal below 8 GB.
7. **Overselling local OCR quality.** Governance risk. Mitigate: tier card repeats the honest-expectations language of `LOCAL_SOVEREIGNTY.md:56-67` ("good on clean print, weaker on handwriting — cloud remains the quality ceiling") at activation time, not buried in docs.
8. **We become maintainers of a bitnet.cpp Windows build (M6).** No upstream prebuilts means our CI compiles a fork; upstream breakage or CVEs are ours to track. Mitigate: pin a vetted upstream commit in the pack manifest; rebuild only on deliberate pack releases; keep the engine behind the same OpenAI-compatible seam (`providers.py:94`) so it is swappable if upstream ever ships official binaries.
9. **AV heuristics on a self-built, low-reputation inference exe (M6).** A freshly compiled `llama-server` derivative with no download reputation is prime SmartScreen/Defender bait. Mitigate: sign it with the same cert as the pack installer; submit to Microsoft for reputation scanning before release; the §5 failure row for quarantined engine binaries applies verbatim.
10. **Overselling a 2B ternary model (M6).** A "fully offline AI" badge on a featherweight machine implies boardroom parity. Mitigate: role-eligibility gating enforced in the resolver (not just UI copy); the featherweight card enumerates exactly what runs locally; non-eligible roles fail with the named-tier `sovereign_blocked` message (§8.2) — consistent with `LOCAL_AI_POLICY.md:38-40` ("Never silent-fail, never silently spend cloud tokens").
11. **HuggingFace download path reliability (M6).** Unlike the Ollama registry, we own resume/verify; a moved/renamed repo breaks the manifest. Mitigate: SHA-256 pin + mirror URL field in `pack.json`; checksum mismatch is a hard, specific error ("downloaded file failed verification — the download source may have changed; update the Sovereign Pack").

---

## 8. BITNET EXTENSION

### 8.1 Where BitNet fits

**What exists today (grounded):** BitNet is already a first-class *detected* citizen — but with the same "detect-only, user-launches-it" limitation as everything else local:

- Probe/endpoint plumbing: `providers.py:26-28` (`bitnet_host()`, `BITNET_HOST` env, default `http://localhost:8080`), `providers.py:94` (the `llamacpp` entry in `LOCAL_ENGINES` covers bitnet.cpp's port 8080, noted "llama.cpp / bitnet.cpp default"), `providers.py:117-122` (`provider_base("bitnet")` resolves live), pinned by test `backend/tests/test_substrate.py:148-150`.
- Status surface: `backend/routers/ai.py:32-60` (`/ai/bitnet-status`, OpenAI-compatible `/v1/models` + optional `/health`), `apiClient.ts:677-683` and `:994-998` (health panel probes 8080 directly), provider card in `frontend/src/lib/ai_config.ts:87-94`.
- Dispatch: keyless sentinel `"local-bitnet-cpu"` (`settings_service.py:165-168`), model-id→provider inference for `bitnet`/`1.58` ids (`settings_service.py:526-528`), and the single-flight local lock already covers it (`ai_service.py:26-28`: `_is_local_target` returns true for `provider == "bitnet"` or any localhost URL).
- Install story: `scripts/bitnet_setup.sh` — git clone + huggingface-cli + a 2–5-minute local **compile** (`bitnet_setup.sh:138-141`). That is the opposite of novice-ready and is bash, not Windows.
- Integration wrinkle worth fixing regardless of packaging: `_resolve_auto_model` only consults BitNet if the vault's `bitnet` "key" slot is non-blank (`settings_service.py:371-374` reads `api_keys` directly, and the default is `""` — `settings_service.py:17`), so today BitNet is realistically reached via the *probe* path (`_resolve_local_or_custom_endpoint`, `settings_service.py:474-480`), which sees it as the anonymous `llamacpp` engine on 8080.

**Does it change the tier table? Yes, for one population.** bitnet.cpp (Microsoft, MIT) runs 1.58-bit ternary models on pure CPU with a ~400 MB inference footprint for BitNet b1.58 2B4T — `LOCAL_AI_POLICY.md:13-14` already establishes "BitNet b1.58 2B is the ceiling on 8 GB… In production there is ~3–4 GB headroom, so the model fits." That means the **"below minimum" refusal tier and the 8 GB text-only tier gain a text-analysis option Ollama cannot offer** — because Ollama/mainline llama.cpp cannot execute ternary models efficiently (bitnet.cpp is a fork with the TL1/TL2 CPU kernels; running the same weights through Ollama would be dequantized/slow or unsupported). The cost of that option is structural: **the pack would ship and supervise a second, different engine binary** — Ollama for ≥8 GB tiers, bitnet.cpp for the featherweight tier. The two never need to run simultaneously (tiering is exclusive), and the existing global local-inference lock (`ai_service.py:24`) already serializes across both since it keys on localhost targets, not engine identity.

### 8.2 Honest quality assessment — what a 2B ternary model can and cannot do here

The project has already litigated this and the plan must not walk it back:

- `LOCAL_AI_POLICY.md:22-26` classifies local-eligible jobs as "background, structured, retrieval: continuity sentinel, research-summarize, character-bible/consistency checks," and cloud-only as "OCR/vision (BitNet can't) and nuanced creative/voice critique (boardroom prose)."
- `SESSION_LOG_2026-06-14.md:26` records the corrected position: a small local model is useful **when the system carries the load** (retrieval + scoped context), "stays weak on nuanced prose/voice critique and cannot do OCR… local = retrieval/consistency, cloud = creative judgment."

Concrete constraints that bound role routing:

1. **No vision, ever.** The modality gate already enforces this mechanically: `bitnet` model ids match no `_VISION_HINTS` pattern, so `infer_modalities` returns `{"text"}` (`providers.py:236-245`) and `TRANSCRIBER_LEAD`/`OCR_ENGINE` (`providers.py:213-217`) can never resolve to it. No new code needed — just never claim otherwise in UI.
2. **Small context (~4k tokens for 2B4T).** The boardroom callers send up to 10,000 chars per call (`ai_service.py:555, 560, 568, 575, 585` — `content[:10000]`) which fits, but whole-manuscript structural passes do not. BitNet jobs must be **chapter-scoped** — the same "scoped context" rule already written in `LOCAL_AI_POLICY.md:52`.
3. **Fragile structured output.** Most dispatches demand JSON (`_call_standard_gateway` sets `response_format: json_object`, `ai_service.py:236-238`); a 2B ternary model will miss that bar regularly. `json_steward.robust_parse` (`ai_service.py:17`) absorbs some of it, but BitNet-routed roles should prefer prose-shaped prompts or tolerate parse retries.

**Recommended role routing (quality framework):**

| Role | Route to BitNet? | Rationale |
|---|---|---|
| `SOVEREIGN_LIAISON` (continuity audit `ai_service.py:554-556`, world-bible extraction `:584-586`) | **Yes** — chapter-scoped | Exactly the retrieval/consistency class blessed by `LOCAL_AI_POLICY.md:23-24` |
| `MARKETING_ANALYST` (moodboard `:579-581`) | Acceptable, labeled "draft quality" | Short-form, low-stakes |
| `COPY_EDITOR`, `NARRATIVE_ARCHITECT` (boardroom structural/prose) | **No** — chapter-level "hints" at most, clearly labeled | Nuanced judgment class; overselling violates governance |
| `TRANSCRIBER_LEAD` / `OCR_ENGINE` | **Never** (modality gate blocks it mechanically) | Text-only engine |

**UI when BitNet is the ONLY option** (the featherweight card, honest by construction): *"Featherweight offline mode — your machine (6 GB RAM) can run continuity checks, chapter summaries, and consistency audits fully offline using Microsoft BitNet (CPU-only). Full boardroom-grade structural and prose analysis, and page transcription (OCR), still need a cloud key — or a machine with 8 GB+ RAM / a GPU."* When a user on this tier invokes a non-eligible role under Sovereign Lock, the existing honest-block path fires (`sovereign_blocked`, `settings_service.py:554-559` → `ai_service.py:201-207`) with the message extended to name the tier: *"…this role needs more model than the Featherweight tier can run. Use a cloud key for this feature, or turn off Sovereign Lock."* No fake success, no silently-degraded boardroom reports.

### 8.3 Packaging/lifecycle delta — what a managed BitNet actually costs

1. **We become the Windows binary vendor.** microsoft/BitNet publishes no official prebuilt Windows releases — the current path is compile-from-source (`scripts/bitnet_setup.sh:138-141`, "takes 2-5 minutes", requires clang toolchain). The pack must ship our own CI-built `bitnet-server.exe` (llama-server-style, TL1/TL2 kernels). MIT permits redistribution, but we own the build matrix (AVX2 baseline + a fallback for older CPUs), security patching, and code-signing of a binary AV engines have never seen (risk register #8–9).
2. **We own model download/verify/resume for this path.** The weights (`microsoft/BitNet-b1.58-2B-4T-gguf`, i2_s GGUF, ~1.2 GB download / ~400 MB runtime footprint — `bitnet_setup.sh:128-133` fetches it via huggingface-cli) come from HuggingFace, not the Ollama registry, so none of Ollama's `/api/pull` resume/digest machinery applies. New code: plain HTTPS download with `Range` resume + SHA-256 verification against `pack.json`, into `SovereignPack/models-bitnet/` (files-only; path through `security.validate_project_path` like everything else). The model itself is MIT-licensed — the cleanest weights license in the whole plan.
3. **Lifecycle = the promotion LOCAL_AI_POLICY already anticipated.** `LOCAL_AI_POLICY.md:69-70`: thread-cap/priority "would only become app-controlled if the app ever spawns bitnet.cpp itself." A managed pack does exactly that: `sovereign_pack_service` spawns the documented recipe (`LOCAL_AI_POLICY.md:71-73`: `llama-server -m <bitnet-2B>.gguf -t 4 --port <port>` at below-normal priority) as a second supervised child, reusing the same supervisor class as the Ollama engine. Integration points that already exist and are reused unchanged: the 8080 probe (`providers.py:94`), `/ai/bitnet-status` (`ai.py:32-60`), `BITNET_HOST` (`providers.py:26-28`) for non-default ports (8080 is heavily contested on dev machines — spawn on a free port and set `BITNET_HOST`, or register it in vault `custom_providers` labeled "Sovereign Pack — Featherweight").
4. **Selection wiring fix (small, needed):** make the managed BitNet reachable through the normal ladder without the user typing anything — either seed the `custom_providers` entry at activation, or teach `_resolve_local_or_custom_endpoint` to rank the pack's BitNet model per the manifest's role-eligibility table (extension of the manifest-first ranking already planned in M3). Also apply LOCAL_AI_POLICY phase C's job gate (`local_policy.py`: RAM headroom, battery, single-flight — `LOCAL_AI_POLICY.md:28-40`) since featherweight machines are precisely the hardware that doc protects.

### 8.4 Recommendation: **(b) — BitNet as M6, after the Ollama-based MVP ships** (with detect-only preserved in v1, which costs nothing)

- **The MVP population is ≥8 GB machines, and Ollama fully serves them.** Shipping v1 with two engines doubles the supervision surface, adds a from-source build pipeline we don't have, and adds a bespoke download manager — all before a single novice has used the one-engine flow. The riskiest novice failure modes (SmartScreen, download UX, GPU drivers) are all exercised by the Ollama path first.
- **Detect-only BitNet already works today and keeps working untouched:** a user-launched bitnet.cpp on 8080 is found by the probe and drives keyless analysis (`_resolve_local_or_custom_endpoint`, `settings_service.py:474-480`). Choosing (b) loses nothing for current power users.
- **But detect-only-forever would abandon the sub-8 GB novice**, for whom the current answer is a hard refusal (`system.py:279-282`) and whose only alternative is a bash compile script (`bitnet_setup.sh`). The featherweight tier is real value — continuity/consistency offline on a 6 GB laptop — and it is honest value *only if* the role-gating and labeling of §8.2 ship with it. That labeling work is why it deserves its own milestone rather than being rushed into v1.

---

## Critical files for implementation

- `backend/services/settings_service.py` — local/custom resolution (`_resolve_local_or_custom_endpoint`), sovereign lock, `_PERMITTED_PREF_KEYS` extension, manifest-first ranking
- `backend/services/providers.py` — `LOCAL_ENGINES`, `probe_local_engines`, Ollama `/api/show` modality authority (the pack builds on all three)
- `backend/services/transcriber/ai_engine.py` — the local-vision dispatch gap (`_get_ai_client` lines 63-76) that blocks sovereign OCR
- `backend/desktop_app.py` — engine spawn/supervise/stop insertion points for the packaged app
- `frontend/src/components/OnboardingModal.tsx` — the novice-facing Sovereign path that must lose its terminal commands (with `SettingsModal.tsx:434-526` as the second UI surface)

**BitNet delta (M6):**
- `LOCAL_AI_POLICY.md` — the job-gate/launch-recipe contract M6 implements
- `scripts/bitnet_setup.sh` — the current from-source install story the pack replaces (source of model repo, build steps, port)
- `backend/services/providers.py` — 8080 probe, `BITNET_HOST`, modality gate that mechanically blocks BitNet from OCR
- `backend/services/settings_service.py` — bitnet sentinel key, provider inference, and the `_resolve_auto_model` wiring wrinkle (`:371-374`) to fix
- `backend/routers/ai.py` — `/ai/bitnet-status` surface reused by the featherweight card
