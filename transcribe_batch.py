# 2. Define the Task (The "What")
transcribe_batch = Task(
    description=(
        "Review the provided batch of photographic image files containing handwritten pages. "
        "Extract all text verbatim. Fix clear spelling mistakes, but leave the grammar exactly as written."
    ),

    expected_output="A clean, plain-text document of the transcribed pages with clear paragraph breaks.",

    agent=scribe_agent
)
