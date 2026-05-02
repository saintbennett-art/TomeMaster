# Ground Truth: AI Engine Standards (March 2026)

**Directive:** For all development and analysis tasks within the PRoeditor ecosystem, **Gemini 3 Flash** is the absolute baseline engine.

## Standard Model Mapping
- **Default / Low Latency / Programming:** `Gemini 3 Flash`
- **Elite / Reasoning / Multi-Step Agentic:** `Gemini 3.1 Pro`

## Technical Guardrails
- **Prompting:** AI Directors/Agents should be prompted to utilize the increased output token capacity (64k+) of Gemini 3.1.
- **Connectivity:** All frontend and backend components must dynamically detect these models from the unified `proeditor_provider` and `proeditor_model` settings.
- **Context:** Always assume a 2026 high-fidelity AI environment. Skip all legacy bridge code or "simulated" delays from previous generations.

## Reference Sources
- User Directive: "Gemini 3.1 is the brain from the beginning. Update yourself for all future projects."
- Current System Date: 2026-03-31
