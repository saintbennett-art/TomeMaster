"""
[PUBLISHING CREW]: CrewAI crew for post-transcription analysis.

Model selection is dynamic via settings_service.get_model_for_role() —
no hardcoded model names. Falls back to env vars, then safe defaults.
"""
import os
import sys
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Ensure backend is importable
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend"))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)


def _resolve_model(role: str, env_var: str, default: str) -> str:
    """Resolves model dynamically from settings → env var → default.

    Never hardcoded to a single provider. Honors user's Settings page choices.
    """
    try:
        from services.settings_service import get_model_for_role
        config = get_model_for_role(role)
        model = config.get("model") if config else None
        if model and model != "auto":
            provider = config.get("provider", "gemini")
            if "/" not in model:
                return f"{provider}/{model}"
            return model
    except Exception as e:
        print(f"[CREW]: Could not resolve dynamic model for {role}: {e}")

    return os.environ.get(env_var, default)


@CrewBase
class PublishingCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def editor(self) -> Agent:
        model = _resolve_model("NARRATIVE_ARCHITECT", "EDITOR_MODEL", "gemini/gemini-2.5-flash")
        print(f"[CREW]: Editor agent using model: {model}")
        return Agent(config=self.agents_config['editor'], llm=model, verbose=True)

    @agent
    def director(self) -> Agent:
        model = _resolve_model("MARKETING_ANALYST", "DIRECTOR_MODEL", "gemini/gemini-2.5-flash")
        print(f"[CREW]: Director agent using model: {model}")
        return Agent(config=self.agents_config['director'], llm=model, verbose=True)

    @agent
    def analyst(self) -> Agent:
        model = _resolve_model("COPY_EDITOR", "ANALYST_MODEL", "gemini/gemini-2.5-flash")
        print(f"[CREW]: Analyst agent using model: {model}")
        return Agent(config=self.agents_config['analyst'], llm=model, verbose=True)

    @task
    def chapterize_manuscript(self) -> Task:
        return Task(
            config=self.tasks_config['chapterize_manuscript'],
            agent=self.editor(),
            output_file="./output/compiled_book.md"
        )

    @task
    def marketing_analysis(self) -> Task:
        return Task(
            config=self.tasks_config['marketing_analysis'],
            agent=self.director(),
            output_file="./output/marketing_report.txt"
        )

    @task
    def pacing_review(self) -> Task:
        return Task(
            config=self.tasks_config['pacing_review'],
            agent=self.analyst(),
            output_file="./output/pacing_report.txt"
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
