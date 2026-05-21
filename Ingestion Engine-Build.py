import os
import glob
from crewai import Agent, Task, Crew, Process
from crewai_files import ImageFile

# 1. Define the Scribe
scribe_agent = Agent(
    role="Senior Manuscript Transcriber",
    goal="Accurately transcribe handwritten pages into clean digital text.",
    backstory="You are an expert at reading difficult, cursive handwriting.",
    multimodal=True,
    allow_delegation=False,
    verbose=True
)

# 2. Build the Task Loop from the Directory
# Using sorted() ensures page_01.jpg comes before page_02.jpg
directory_path = "./raw_pages"
image_files = sorted(glob.glob(f"{directory_path}/*.jpg"))

tasks_array = []

for file_path in image_files:
    filename = os.path.basename(file_path)
    
    # Create an independent, asynchronous task for each file
    page_task = Task(
        description=f"Read the attached image ({filename}). Extract all text verbatim. Fix clear spelling mistakes but leave grammar exactly as written.",
        expected_output=f"Clean plain-text transcription of {filename}.",
        agent=scribe_agent,
        async_execution=True,  # <-- This forces parallel background processing
        input_files={"page_image": ImageFile(source=file_path)}
    )
    tasks_array.append(page_task)

# 3. Create the Synchronization Task
# This runs synchronously at the very end, waiting for all async tasks to finish.
compile_task = Task(
    description="Review the transcriptions from all previous tasks. Compile them into a single, cohesive document in chronological order. Do not change any of the text.",
    expected_output="A single text string containing the full transcribed manuscript.",
    agent=scribe_agent,
    context=tasks_array, # <-- This tells CrewAI to wait for the async tasks to finish
    output_file="./output/raw_manuscript.txt" # Automatically saves the compiled result
)

# Add the compile task to the very end of our task list
tasks_array.append(compile_task)

# 4. Execute the Pipeline
batch_crew = Crew(
    agents=[scribe_agent],
    tasks=tasks_array,
    process=Process.sequential 
max_rpm=30 # Throttles the async execution to stay under API limits)

print(f"Starting async batch processing for {len(image_files)} pages...")
batch_crew.kickoff()
print("Batch transcription complete! Output saved to ./output/raw_manuscript.txt")