from pydantic import BaseModel

class TomeMasterState(BaseModel):
    raw_manuscript: str = ""
    chapterized_book: str = ""
    marketing_blurb: str = ""
    pacing_report: str = ""