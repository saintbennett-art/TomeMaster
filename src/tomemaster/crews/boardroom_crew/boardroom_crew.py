"""
BoardroomCrew — CrewAI-native replacement for the raw httpx specialist calls.

Eliminates the facade chain:
  OLD: analysis.py → ai_service wrapper → _call_standard_gateway → httpx
  NEW: analysis.py → BoardroomCrew.dispatch() → CrewAI agent → LiteLLM

Each dispatch creates a single-task Crew with the right agent and kicks it off.
Multi-persona /convene creates a multi-task Crew with parallel execution.

Model resolution is fully dynamic via settings_service.get_model_for_role().
"""

import os
import sys
import asyncio
from typing import Optional

from crewai import Agent, Crew, Process, Task

# Ensure backend services are importable
_backend_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend")
)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


def _resolve_llm(role: str) -> str:
    """Resolve the LiteLLM model string for an Industrial Role.

    CrewAI agents accept a `llm` string in LiteLLM format:
      - "gemini/gemini-3.1-pro-preview"
      - "openai/gpt-4o"
      - "anthropic/claude-3-5-sonnet-20241022"

    We pull the model + provider from the encrypted vault via
    settings_service.get_model_for_role() and format accordingly.
    """
    try:
        from services.settings_service import get_model_for_role

        config = get_model_for_role(role)
        if not config:
            return "gemini/gemini-2.5-flash"

        provider = config.get("provider", "gemini")
        model = config.get("model", "gemini-2.5-flash")

        # LiteLLM format: provider/model
        # Gemini uses "gemini/" prefix in LiteLLM
        return f"{provider}/{model}"
    except Exception as e:
        print(f"BOARDROOM: Model resolution failed for {role}: {e}")
        return "gemini/gemini-2.5-flash"


def _inject_api_keys():
    """Ensure API keys from the vault are in env vars for LiteLLM/CrewAI.

    CrewAI uses LiteLLM under the hood, which reads keys from env vars:
      GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY
    The vault hydration in main.py already does this at startup, but we
    double-check here for safety when BoardroomCrew is used standalone.
    """
    try:
        from services.settings_service import get_api_key

        key_map = {
            "GEMINI_API_KEY": "gemini",
            "OPENAI_API_KEY": "openai",
            "ANTHROPIC_API_KEY": "anthropic",
            "GROQ_API_KEY": "groq",
        }
        for env_var, provider in key_map.items():
            if not os.environ.get(env_var):
                key = get_api_key(provider)
                if key:
                    os.environ[env_var] = key
    except Exception:
        pass  # Keys should already be hydrated from vault at startup


def _get_style_prefix() -> str:
    """Pull the Style Mirror DNA prefix for prose refinement."""
    try:
        from services.style_mirror import MIRROR

        return MIRROR.get_muse_prompt_prefix()
    except Exception:
        return ""


def _robust_parse_json(raw: str) -> dict:
    """Parse JSON from agent output, tolerating markdown fences."""
    try:
        from services.ai.json_steward import robust_parse

        return robust_parse(raw)
    except Exception:
        import json

        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except Exception:
            return {"feedback": raw}


class BoardroomCrew:
    """Factory that dispatches manuscript analysis tasks to CrewAI agents.

    Usage from router endpoints:

        crew = BoardroomCrew()
        result = await crew.structural_analysis(text, user_chapters=[...])
        result = await crew.emotional_arc(text)
        result = await crew.convene(text, personas=["Copy Editor", "Marketing Executive"])
    """

    # ─── Agent Factories ──────────────────────────────────────────────────

    def _make_narrative_architect(self, override_llm: str = None) -> Agent:
        llm = override_llm or _resolve_llm("NARRATIVE_ARCHITECT")
        return Agent(
            role="Disruptive Narrative Architect",
            goal=(
                "Perform deep structural analysis of manuscripts — chapter breaks, "
                "emotional arcs, pacing heatmaps, and dynamic arc adjustments."
            ),
            backstory=(
                "You are an elite structural editor with decades of experience "
                "deconstructing bestsellers and literary masterworks. You think in "
                "narrative geometry — tension curves, beat frequencies, chapter cadence. "
                "You see what other editors miss: the invisible architecture that makes "
                "a reader unable to put a book down."
            ),
            llm=llm,
            verbose=True,
        )

    def _make_copy_editor(self, override_llm: str = None) -> Agent:
        llm = override_llm or _resolve_llm("COPY_EDITOR")
        return Agent(
            role="Master Copy Editor & Continuity Sentinel",
            goal=(
                "Audit prose for grammar, style, narrative flow, and internal "
                "consistency. Detect continuity errors and refine dictated prose."
            ),
            backstory=(
                "You are a legendary copy editor who has polished Pulitzer-winning "
                "manuscripts. Your eye catches what spell-checkers miss — rhythm breaks, "
                "tonal shifts, subtle contradictions. You are also the Continuity "
                "Sentinel: no detail contradicts itself on your watch."
            ),
            llm=llm,
            verbose=True,
        )

    def _make_marketing_analyst(self, override_llm: str = None) -> Agent:
        llm = override_llm or _resolve_llm("MARKETING_ANALYST")
        return Agent(
            role="Publishing Marketing Executive",
            goal=(
                "Generate pitch hooks, audience demographics, back-cover blurbs, "
                "and atmospheric moodboards for scenes."
            ),
            backstory=(
                "You are a veteran retail book seller turned marketing strategist. "
                "You know exactly what hooks readers, what sells copies, and what makes "
                "a book cover stop someone mid-scroll."
            ),
            llm=llm,
            verbose=True,
        )

    def _make_sovereign_liaison(self, override_llm: str = None) -> Agent:
        llm = override_llm or _resolve_llm("SOVEREIGN_LIAISON")
        return Agent(
            role="Sovereign Liaison & World-Bible Keeper",
            goal=(
                "Extract and maintain the World Bible — characters, locations, "
                "timelines, relationships, cultural context. Perform cultural audits."
            ),
            backstory=(
                "You are a world-building specialist and cultural consultant. You track "
                "every character, every location, every timeline thread. Nothing escapes "
                "your ledger."
            ),
            llm=llm,
            verbose=True,
        )

    # ─── Persona → Agent Mapping ─────────────────────────────────────────

    # Maps specialist_registry persona names to (agent_factory, industrial_role)
    _PERSONA_MAP = {
        "Developmental Editor": ("_make_narrative_architect", "NARRATIVE_ARCHITECT"),
        "Copy Editor": ("_make_copy_editor", "COPY_EDITOR"),
        "Marketing Executive": ("_make_marketing_analyst", "MARKETING_ANALYST"),
        "Sovereign Liaison": ("_make_sovereign_liaison", "SOVEREIGN_LIAISON"),
        # Aliases used by various endpoints
        "Editor-in-Chief": ("_make_copy_editor", "COPY_EDITOR"),
        "Narrative Architect": ("_make_narrative_architect", "NARRATIVE_ARCHITECT"),
    }

    def _agent_for_persona(self, persona: str, override_llm: str = None) -> Agent:
        """Resolve a persona name to a CrewAI Agent instance."""
        factory_name, _role = self._PERSONA_MAP.get(
            persona, ("_make_sovereign_liaison", "SOVEREIGN_LIAISON")
        )
        factory = getattr(self, factory_name)
        return factory(override_llm)

    # ─── Dispatch Helpers ─────────────────────────────────────────────────

    async def _run_single_task(
        self,
        agent: Agent,
        description: str,
        expected_output: str,
        is_json: bool = True,
    ) -> dict:
        """Create a single-task Crew, kick off, and return parsed result."""
        _inject_api_keys()

        task = Task(
            description=description,
            expected_output=expected_output,
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        # CrewAI kickoff is synchronous — run in executor to not block the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: crew.kickoff())

        raw = str(result)
        if is_json:
            return _robust_parse_json(raw)
        return {"feedback": raw}

    # ─── Public Endpoint Methods ──────────────────────────────────────────

    async def structural_analysis(
        self,
        text: str,
        user_chapters: list = None,
        provider: str = None,
        api_key: str = None,
        model: str = None,
        **kwargs,
    ) -> dict:
        """Replaces: ai_service.run_structural_analysis_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None

        # Build the branch instruction (from prompt_orchestrator logic)
        branch_instruction = ""
        if not user_chapters or len(user_chapters) == 0:
            branch_instruction = (
                "[MANUSCRIPT HAS NO EXISTING STRUCTURE - BLANK STATE] "
                "You ARE the first architect. Identify natural narrative pauses "
                "and suggest a FULL, balanced Chapter structure from scratch."
            )
        else:
            chap_summary = "\n".join(
                [
                    f"- Chapter {c.get('chapter_number', i+1)}: "
                    f"'{c.get('suggested_title', 'Untitled')}'"
                    for i, c in enumerate(user_chapters)
                ]
            )
            branch_instruction = (
                f"[DISRUPTIVE NARRATIVE AUDIT - EXISTING STRUCTURE DETECTED]\n"
                f"Current Chapter Pacing:\n{chap_summary}\n"
                f"DIAGNOSTIC TASK: Identify all chapters exceeding 20 minutes as "
                f"'Rhythm Violations.'\n"
                f"ARCHITECTURAL TASK: You are NOT bound by the author's current "
                f"chapter breaks. If a chapter is too long, suggest new breaks."
            )

        safe_text = text[:30000]
        description = (
            f"Analyze the following manuscript text and identify natural chapter breaks.\n\n"
            f"CRITICAL FORMATTING: Use standard straight apostrophes (') and straight "
            f'double quotes (") exclusively.\n\n'
            f"MANDATORY METADATA: For EVERY chapter, provide:\n"
            f"1. 'emotional_intensity' (1-10).\n"
            f"2. 'suggested_title': A compelling, professional title.\n"
            f"3. 'reasoning': Brief explanation of the break's effectiveness.\n"
            f"4. 'starting_words': EXACTLY 10 to 15 unique, consecutive words of the "
            f"paragraph where this chapter begins.\n\n"
            f"{branch_instruction}\n\n"
            f"Manuscript Text:\n{safe_text}"
        )

        return await self._run_single_task(
            agent=self._make_narrative_architect(override_llm),
            description=description,
            expected_output=(
                'A strict JSON object: {"chapters": [{"chapter_number": 1, '
                '"suggested_title": "...", "emotional_intensity": 5, '
                '"reasoning": "...", "starting_words": "..."}]}'
            ),
        )

    async def emotional_arc(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.analyze_emotional_arc_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:10000]
        return await self._run_single_task(
            agent=self._make_narrative_architect(override_llm),
            description=(
                f"Analyze the emotional arc of the following manuscript text. Map "
                f"emotional intensity across the narrative, identifying peaks, valleys, "
                f"turning points, and the overall emotional trajectory.\n\nText:\n{safe_text}"
            ),
            expected_output=(
                "A JSON object with emotional arc data: intensity_curve, turning_points, "
                "overall_trajectory, and narrative_beats."
            ),
        )

    async def pacing_heatmap(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.run_heatmap_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:10000]
        return await self._run_single_task(
            agent=self._make_narrative_architect(override_llm),
            description=(
                f"Calculate a pacing density and narrative tension heatmap for the "
                f"following text. Identify sections of high tension, lulls, action "
                f"sequences, and reflective passages. Rate each section's pacing "
                f"velocity.\n\nText:\n{safe_text}"
            ),
            expected_output=(
                "A JSON heatmap object with sections, each containing position, "
                "pacing_score, tension_level, and classification."
            ),
        )

    async def dynamic_arc(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.run_dynamic_arc_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:10000]
        return await self._run_single_task(
            agent=self._make_narrative_architect(override_llm),
            description=(
                f"Perform an interactive emotional arc adjustment with plot-point "
                f"recommendations. Identify key plot points and suggest arc "
                f"modifications for stronger narrative impact.\n\nText:\n{safe_text}"
            ),
            expected_output=(
                "A JSON object with plot_points[] and arc_curve[] showing the "
                "adjusted emotional trajectory."
            ),
        )

    async def continuity_sentinel(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.run_sentinel_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:10000]
        return await self._run_single_task(
            agent=self._make_copy_editor(override_llm),
            description=(
                f"Perform a continuity audit on the following manuscript text. Check "
                f"for logical inconsistencies, character drift, timeline contradictions, "
                f"factual errors, and any details that contradict earlier "
                f"sections.\n\nText:\n{safe_text}"
            ),
            expected_output=(
                "A JSON object with continuity findings: inconsistencies array, "
                "character_drift_warnings, and timeline_issues."
            ),
        )

    async def refine_prose(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: the /refine-prose endpoint's ai_service.run_boardroom_parallel() call."""
        override_llm = f"{provider}/{model}" if provider and model else None
        style_prefix = _get_style_prefix()
        return await self._run_single_task(
            agent=self._make_copy_editor(override_llm),
            description=(
                f"{style_prefix}\n\n"
                f"REWRITE THIS DICTATION FOR FLOW AND FIDELITY. MAINTAIN ALL CORE "
                f"MEANING BUT SMOOTH THE TRANSCRIPTION ARTIFACTS:\n\n{text}"
            ),
            expected_output="A JSON object with a 'refined' field containing the smoothed prose.",
            is_json=True,
        )

    async def moodboard(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.generate_moodboard_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:5000]
        return await self._run_single_task(
            agent=self._make_marketing_analyst(override_llm),
            description=(
                f"Generate an atmospheric visual and auditory moodboard for the "
                f"following scene. Include color palette, lighting mood, ambient "
                f"sounds, musical references, and visual composition "
                f"suggestions.\n\nScene text:\n{safe_text}"
            ),
            expected_output=(
                "A JSON moodboard object with visual_palette, lighting, "
                "ambient_sounds, music_references, and composition_notes."
            ),
        )

    async def world_bible(
        self, text: str, provider: str = None, api_key: str = None,
        model: str = None, **kwargs
    ) -> dict:
        """Replaces: ai_service.analyze_world_bible_async()"""
        override_llm = f"{provider}/{model}" if provider and model else None
        safe_text = text[:10000]
        return await self._run_single_task(
            agent=self._make_sovereign_liaison(override_llm),
            description=(
                f"Extract all characters, locations, timeline events, and relationships "
                f"from the following text. Build a comprehensive World Bible "
                f"entry.\n\nText:\n{safe_text}"
            ),
            expected_output=(
                "A JSON World Bible object with characters array, locations array, "
                "timeline_events, and relationships map."
            ),
        )

    async def convene(
        self,
        text: str,
        personas: list,
        provider: str = None,
        api_key: str = None,
        model: str = None,
        user_chapters: list = None,
        custom_prompt: str = None,
        **kwargs,
    ) -> dict:
        """Replaces: ai_service.run_boardroom_parallel()

        Multi-persona dispatch. Creates one task per persona, runs them
        concurrently via asyncio.gather (each in its own single-task Crew
        to allow different models per agent).
        """
        _inject_api_keys()

        override_llm = f"{provider}/{model}" if provider and model else None

        async def _run_persona(persona: str) -> tuple:
            try:
                agent = self._agent_for_persona(persona, override_llm)

                # Build prompt using orchestrator for full template support
                try:
                    from services.ai.prompt_orchestrator import build_industrial_prompt

                    prompt, is_json, _role = build_industrial_prompt(
                        text, persona, user_chapters
                    )
                except Exception:
                    # Fallback: simple prompt
                    prompt = (
                        f"As a {persona} specialist, analyze this manuscript:\n\n"
                        f"{custom_prompt or ''}\n\n{text[:15000]}"
                    )
                    is_json = True

                task = Task(
                    description=prompt,
                    expected_output=(
                        'A JSON object with "feedback" (markdown report) and '
                        'optional "suggestions" array.'
                    ),
                    agent=agent,
                )

                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=True,
                )

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: crew.kickoff())
                raw = str(result)
                parsed = _robust_parse_json(raw) if is_json else {"feedback": raw}
                return persona, parsed

            except Exception as e:
                return persona, {"feedback": f"Expert {persona} Offline: {str(e)}"}

        # Fan out all personas concurrently
        tasks = [_run_persona(p) for p in personas]
        completed = await asyncio.gather(*tasks)

        result = {persona: response for persona, response in completed}
        if not result:
            raise ValueError(
                "All requested Board Members failed to respond. "
                "Please check your credentials and model availability."
            )
        return result
