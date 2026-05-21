---
description: TomeMaster Automation Upgrade
---

# Workflow: TomeMaster Automation Upgrade

**Goal:** Analyze the existing TomeMaster directory, identify legacy sequential execution or opaque "black box" logic, and completely rewire the application into an asynchronous, multi-agent CrewAI Flow.

## Phase 1: Index and Analyze

1. Scan the current project directory and identify the ingestion scripts, formatting tools, and any existing AI tool calls.
2. Map the current "black boxes"—specifically looking for where image processing happens, how text is compiled, and where the process bottlenecks sequentially.
3. Generate an Antigravity Artifact (Task List) mapping out how these legacy scripts map to CrewAI Agents.

## Phase 2: Dependency & Integration Upgrade

1. Update the environment using `uv add crewai crewai-tools pydantic`.
2. Delete legacy OCR or sequential LLM API loops.
3. Ensure all external API keys (Gemini, Claude, etc.) are securely routed from the `.env` file to the CrewAI agent configurations.

## Phase 3: The Flow Implementation

Rewrite the core execution logic into a unified `Flow` class with the following stateful architecture:

1. **@start - The Ingestion Engine:** Build an asynchronous directory loop that fires `Task(async_execution=True)` for every image using a Multimodal Scribe agent.
2. **@listen(ingestion) - The Compiler:** A synchronous step that waits for all pages, passes them to a Structural Editor agent, and saves `compiled_book.md`.
3. **@listen(compiler) - The Fan-Out:** Create parallel triggers for a Marketing Director agent (to write blurbs) and a Pacing Analyst agent (to write emotional pacing reports).

## Execution Rules

- Do not use legacy third-party vision tools; use CrewAI's native `multimodal=True` and `crewai_files` for the Scribe.
- Retain the exact persona guardrails for the Scribe: "never change the style, tone, phrasing, or sentence structure of the original work."
- Run tests on the Flow initialization to ensure the `@listen` decorators are properly wired before requesting human approval via an Artifact Code Diff.
