from crewai import Agent

scribe_agent = Agent(
    role="Senior Manuscript Transcriber",
    goal="Accurately transcribe handwritten pages into clean, readable digital text.",
    backstory="You are an expert at reading difficult, cursive handwriting.",
    multimodal=True,  # <-- This single line gives the agent vision capabilities
    allow_delegation=False,
    verbose=True
)
