# 🏛️ SOVEREIGN ARCHITECTURE: ENGINEERING MANUAL v5.2

This manual documents the high-fidelity resilience systems and accounting protocols implemented as of April 2026. These systems ensure the application remains stable under extreme provider-side saturation and hardware constraints.

## 1. SPECTRUM FAILOVER PROTOCOL (1, 3, 4, 2)
To maintain continuous operation without user-facing errors, the system utilizes a **Silent Generational Cascade**. If an apex intelligence tier fails (due to Quota, Authorization, or API Outage), the **Sovereign Orchestrator** automatically re-routes the request.

### The Hierarchy
1.  **GEMINI 3.1 PRO (Apex)**: The high-fidelity anchor for narrative and structural audits.
2.  **GEMINI 3 FLASH (Stability)**: The secondary 3.x tier. Ultra-fast, zero-latency, and high rate limits.
3.  **GEMINI 2.1 PRO (Legacy)**: High-fidelity alternative if the 3.x generation is entirely saturated.
4.  **GEMINI 1.5 PRO (Bedrock)**: The absolute emergency anchor to prevent system blackout.

### Resilience Features
*   **Silent Rerouting**: All 404, 429, and 500 errors are caught and swallowed. The user only sees "Synthesizing...".
*   **Normalized Dispatcher**: Identifiers like `gemini-3-flash-preview` are standardized across the discovery engine and SDK to prevent naming drift.

## 2. CREDENTIAL CRUNCH ACCOUNTING
Transparency is maintained through a non-disruptive ledger system. While the failover is silent, the **Credit Impact** is recorded and reported post-analysis.

### Accounting Components
*   **Sovereign Accounting Seal**: A stylized UI element at the base of every specialist report identifying the successful model and credit cost.
*   **Credit Normalization**: Costs are calculated per 1M tokens based on actual model usage (e.g., Flash costs are ~16x lower than Pro costs).
*   **Persistent Usage Ledger**: Synchronized backend JSON logs (`api_usage_log.jsonl`) feed the "Ledger" tab in the Settings Command Center.

## 3. HARDWARE STEWARDSHIP & SAFETY
To prevent local mode from "bricking" user workstations, the system enforces strict hardware boundaries.

### Safety Framework
*   **Hardware Fidelity Audit**: Real-time evaluation of System RAM, CPU Cores, and logical percentage to determine "Local Mode Authorization."
*   **8GB/16GB Critical Thresholds**: The system warns against local inference on machines with less than 8GB of RAM.
*   **Emergency Kill Switch**: A global manual override that instantly terminates background local pathways while keeping the dashboard alive.

## 4. STANDALONE PRODUCTION GOAL
The application is designed to be an **Isolated Sovereign Entity**.

*   **Production Bundle**: `BoardroomIntelligence.exe`.
*   **Mechanism**: Bundles Python 3.1x, the FastAPI backend, and the React frontend into a signed, chromeless executable.
*   **No Dependency Leak**: The app runs entirely in its own sandbox, avoiding conflict with the user's operating system environment.

## 5. VISION-ONLY PROTOCOL (OCR INTEGRITY)
To prevent `400 Bad Request` crashes during transcription, the system enforces a strict Vision-capability filter on all OCR providers.
*   **Groq Pathway**: Exclusively locked to `llama-3.2-90b-vision-preview`. Never utilize text-only models (e.g., Llama 3.3) for image-based workflows.
*   **Gemini Pathway**: Locked to the `google-genai` (v2) SDK to ensure high-fidelity image handoffs without deprecation artifacts.

## 6. DIRECTORIAL ANCHORING & ANTI-NESTING
The manuscript work area must be protected from recursive directory growth during session stops/resumes.
*   **The Artifacts Anchor**: `_manuscript_source` is the Sovereign Ground Truth for raw assets.
*   **Ingestion Guard**: If a user anchors the project directly to an existing `_manuscript_source` folder, the engine must skip the "Migration" step to prevent recursive "Russian Doll" nesting.
*   **Ghost Error Transparency**: All background thread exceptions must be bubbled to the UI `status: "error"` state. The HUD is forbidden from spinning indefinitely on a crashed backend thread.

---
**AUTHOR**: Antigravity Sovereign AI
**STATUS**: Documentation Current as of Handshake 2026-04-24
**FILE**: CORE_ARCHITECTURE.md

