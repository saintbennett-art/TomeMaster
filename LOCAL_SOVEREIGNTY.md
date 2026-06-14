# Local Sovereignty — Running Tome-Master Fully Offline

Tome-Master can run **100% locally** — no cloud keys, no data leaving the
machine — by serving every AI role from a local engine (Ollama, LM Studio, vLLM,
llama.cpp / BitNet). This is *sovereign mode*: your manuscript never touches a
third party. This document explains how selection works and **what hardware you
actually need**, because that's the deciding factor.

---

## How the app selects a local model

Selection is **modality-driven** — never a hardcoded list of model names:

1. The app **auto-detects** running local engines on localhost (Settings →
   "Local & Exotic Engines" → it scans on open).
2. Each role declares the **modality** it requires:
   - **Transcription / OCR → `image`** (must be a *vision* model — it has to see the page).
   - Structure, copy-edit, grammar, boardroom → `text`.
3. For each role, the app picks a local model that **supports the required
   modality** (queried directly from the engine — e.g. Ollama reports `vision`).
   A text-only model is **never** handed an OCR job; if no local model satisfies
   the modality, the app fails honestly rather than pretending.

You can also **pin** a specific local model per role in Settings; otherwise the
first capable model is used.

> **The hard rule:** OCR needs a **vision** model. A text-only model
> (e.g. `deepseek-r1`, `llama-3.x` text) physically cannot transcribe a scan.

---

## Hardware requirements

These are realistic working figures for the **active inference footprint** (not
disk size). Quantized (Q4) models; "effective-parameter" models such as Gemma 3n
(`e2b`/`e4b`) run lighter than their raw parameter count suggests.

| Tier | What runs | RAM (CPU-only) | GPU VRAM | Notes |
|------|-----------|----------------|----------|-------|
| **Text roles only** (structure, copy, grammar, boardroom) | 2–4B text model (Q4) | **8 GB** | optional | CPU-only is fine. **No OCR.** |
| **OCR-capable (entry)** | small vision model, ~2–4B effective (e.g. Gemma 3n `e2b`) | **12–16 GB** | **4–6 GB** | CPU-only *works* but is slow per page; GPU strongly recommended for multi-page manuscripts. |
| **Comfortable** | 7–8B vision (e.g. Gemma 3n `e4b`, Llama-3.2-11B-Vision) | **16–24 GB** | **8–12 GB** | Good speed + noticeably better OCR quality. |
| **Best local quality** | 11B+ vision, larger context | 32 GB+ | **16–24 GB** | Approaches usable manuscript fidelity; still below cloud. |

**GPU vs CPU:** a CUDA (NVIDIA) or Metal (Apple Silicon) GPU is *dramatically*
faster for vision OCR — often the difference between seconds and minutes per
page. CPU-only is viable for text roles and small test batches, but transcribing
a 300-page manuscript on CPU vision is impractical.

**Rule of thumb:** if a model strained your machine when you `ollama run` it
interactively, it will strain OCR too. Drop to the next-smaller vision model.

---

## Honest quality expectations

Local vision OCR is **meaningfully weaker than cloud** (e.g. Gemini Flash):

- ✅ Good on **clean printed text**.
- ⚠️ Weaker on **handwriting**, dense layout, and the prompt's nuanced rules
  (page-number isolation, highlighter "deletion zones").
- For publisher-grade manuscript fidelity, **cloud vision remains the real
  engine**; local is for privacy-critical work, offline use, or testing.

A sensible hybrid (see the project notes): **local for retrieval/consistency
work** the system feeds it; **cloud for OCR and nuanced creative judgment.**

---

## Setup (Ollama example)

1. Install Ollama (`https://ollama.com`).
2. Pull a **vision** model sized to your hardware, e.g. a small Gemma 3n vision
   build for entry tier.
3. Ensure the server is running (`ollama serve`, default `:11434`).
4. In Tome-Master → Settings → "Local & Exotic Engines" → **Rescan localhost**.
   The engine and its models appear; OCR roles will route to a vision model
   automatically.

Non-default ports or a model on another machine: add it as a custom
OpenAI-compatible endpoint (label + base URL) in the same panel.
