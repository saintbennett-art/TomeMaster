import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class PublishingCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def editor(self) -> Agent:
        return Agent(config=self.agents_config['editor'], llm=os.environ.get('EDITOR_MODEL', 'gemini/gemini-3.1-pro'), verbose=True)

    @agent
    def director(self) -> Agent:
        return Agent(config=self.agents_config['director'], llm=os.environ.get('DIRECTOR_MODEL', 'anthropic/claude-3-5-sonnet-20241022'), verbose=True)

    @agent
    def analyst(self) -> Agent:
        return Agent(config=self.agents_config['analyst'], llm=os.environ.get('ANALYST_MODEL', 'openai/gpt-4o'), verbose=True)

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
        # We process the editor first, then fan out marketing and pacing in parallel
        # CrewAI supports hierarchical or sequential.
        # However, the blueprint specified the parallel fanout happens using CrewAI *Flows*
        # "@listen(compile_book) - Parallel Fan-Out".
        # If we use a single crew for publishing, we'd need them as separate Crews if we want Flow fan-out.
        # But wait, in the Flow blueprint we saw:
        # PublishingCrew().crew().kickoff(inputs={"text": self.state.raw_manuscript})
        # If we do it inside a single Crew, we can just run them synchronously, or set Process.hierarchical.
        # Let's run them sequentially here for simplicity, or we can just use Process.sequential.
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
