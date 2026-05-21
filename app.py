import os
import glob
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, listen, start
from crewai_files import ImageFile

# Define what data travels through the boardroom
class TomeMasterState(BaseModel):
    raw_manuscript: str = ""
    chapterized_book: str = ""
    marketing_blurb: str = ""
    pacing_report: str = ""

class TomeMasterPipeline(Flow[TomeMasterState]):

    @start()
    def transcribe_pages(self):
        print("🔍 Phase 1: Initiating Asynchronous Batch Transcription...")
        
        scribe = Agent(
            role="Senior Manuscript Transcriber",
            goal="Accurately transcribe handwritten text into clean digital text.",
            backstory="Archivist specialized in reading cursive. You preserve the raw voice.",
            multimodal=True,
            allow_delegation=False
        )

        image_files = sorted(glob.glob("./raw_pages/*.jpg"))
        tasks = []

        for file_path in image_files:
            filename = os.path.basename(file_path)
            page_task = Task(
                description=f"Verbatim transcription of {filename}. Fix spelling, keep grammar.",
                expected_output="Clean plain text.",
                agent=scribe,
                async_execution=True, # Parallel execution
                input_files={"page_image": ImageFile(source=file_path)}
            )
            tasks.append(page_task)

        # Synchronous anchor task that gathers all parallel inputs
        compile_task = Task(
            description="Combine all previous task transcriptions sequentially.",
            expected_output="The full raw text manuscript.",
            agent=scribe,
            context=tasks,
            output_file="./output/raw_manuscript.txt"
        )
        tasks.append(compile_task)

        # Cap the parallel engine requests to stay within API rate limits
        Crew(agents=[scribe], tasks=tasks, max_rpm=30).kickoff()
        
        with open("./output/raw_manuscript.txt", "r") as f:
            self.state.raw_manuscript = f.read()
        return self.state.raw_manuscript

    @listen(transcribe_pages)
    def compile_book(self, raw_text):
        print("📖 Phase 2: Structural Chapterization and Formatting...")
        
        editor = Agent(
            role="Structural Book Editor",
            goal="Organize a continuous manuscript into a cohesive, chapterized book structure.",
            backstory="Expert publisher who defines layouts, chapter hooks, and structural flows."
        )

        chapter_task = Task(
            description="Analyze the raw manuscript text. Insert clean Markdown chapter breaks and titles.",
            expected_output="A structured markdown manuscript.",
            agent=editor,
            output_file="./output/compiled_book.md"
        )

        Crew(agents=[editor], tasks=[chapter_task]).kickoff()
        
        with open("./output/compiled_book.md", "r") as f:
            self.state.chapterized_book = f.read()
        return self.state.chapterized_book

    # --- THE BOARDROOM FAN-OUT (Parallel Execution) ---

    @listen(compile_book)
    def run_marketing_analysis(self, compiled_book):
        print("📢 Phase 3A: Launching Marketing Strategy Loop...")
        director = Agent(role="Marketing Director", goal="Create back-cover blurbs and campaign specs.", backstory="Retail book seller.")
        task = Task(description="Write a book blurb from the text.", expected_output="Text asset.", agent=director, output_file="./output/marketing_report.txt")
        Crew(agents=[director], tasks=[task]).kickoff()

    @listen(compile_book)
    def run_pacing_analysis(self, compiled_book):
        print("📈 Phase 3B: Launching Emotional Pacing Review...")
        analyst = Agent(role="Pacing Analyst", goal="Map emotional beats and narrative arc.", backstory="Literary theorist.")
        task = Task(description="Analyze narrative speed.", expected_output="Pacing matrix.", agent=analyst, output_file="./output/pacing_report.txt")
        Crew(agents=[analyst], tasks=[task]).kickoff()

if __name__ == "__main__":
    pipeline = TomeMasterPipeline()
    pipeline.kickoff()
    print("✨ TomeMaster execution successfully completed.")