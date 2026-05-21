import os
import glob
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_files import ImageFile

import sys

def ui_sync_callback(task_output):
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend")))
        from services import transcriber_service
        from services import settings_service
        
        output_text = task_output.raw
        
        # [FERPA COMPLIANCE]: Only scrub PII when the user has explicitly enabled it
        prefs = settings_service.load_settings().get("preferences", {})
        if prefs.get("pii_scrub", False):
            from services.pii_scrubber import pii_scrubber
            output_text = pii_scrubber.anonymize_text(output_text)
        
        with transcriber_service.TRANSCRIPTION_LOCK:
            transcriber_service.TRANSCRIPTION_STATE["processed_images"] += 1
            transcriber_service.TRANSCRIPTION_STATE["stream_buffer"].append({
                "text": output_text,
                "preview": output_text[:50] + "..."
            })
    except Exception as e:
        print("UI Sync Error:", e)

@CrewBase
class TranscriptionCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def scribe(self) -> Agent:
        return Agent(
            config=self.agents_config['scribe'],
            llm=os.environ.get('SCRIBE_MODEL', 'gemini/gemini-3.1-pro'),
            multimodal=True,
            allow_delegation=False,
            verbose=True
        )

    @task
    def compile_manuscript(self) -> Task:
        return Task(
            config=self.tasks_config['compile_manuscript'],
            agent=self.scribe(),
            output_file="./output/raw_manuscript.txt"
        )

    @crew
    def crew(self) -> Crew:
        scribe_agent = self.scribe()
        
        # We will pull the folder path from kickoff inputs dynamically
        return Crew(
            agents=[scribe_agent],
            tasks=[], # Tasks will be generated dynamically based on inputs
            process=Process.sequential,
            max_rpm=15 # Throttle to prevent rate limit spikes
        )

    def _generate_dynamic_tasks(self, folder_path: str):
        scribe_agent = self.scribe()
        # Fallback to test_batch if no folder provided
        target_folder = folder_path if folder_path else "./test_batch"
        image_files = sorted(glob.glob(f"{target_folder}/*.jpg")) + sorted(glob.glob(f"{target_folder}/*.png"))
        
        tasks_array = []
        # Dynamically spawn an async task for every image
        for file_path in image_files:
            filename = os.path.basename(file_path)
            page_task = Task(
                description=self.tasks_config['transcribe_page']['description'].format(filename=filename),
                expected_output=self.tasks_config['transcribe_page']['expected_output'],
                agent=scribe_agent,
                async_execution=True,
                input_files={"page_image": ImageFile(source=file_path)},
                callback=ui_sync_callback
            )
            tasks_array.append(page_task)

        # Append the synchronous compile task at the end with context
        compile_task = self.compile_manuscript()
        compile_task.context = tasks_array
        tasks_array.append(compile_task)
        return tasks_array
