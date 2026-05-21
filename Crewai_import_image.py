from crewai import Task
from crewai_files import ImageFile

transcribe_task = Task(
    description=(
        "Review the attached handwritten manuscript page in {page_image}. "
        "Extract all text verbatim. Fix clear spelling mistakes, but leave the grammar exactly as written."
    ),
    expected_output="A clean, plain-text document of the transcribed page with clear paragraph breaks.",
    agent=scribe_agent,

    # Pass the actual image file directly into the task context
    input_files={
        "page_image": ImageFile(source="./raw_pages/page_01.jpg")
    }
)
