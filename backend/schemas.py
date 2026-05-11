from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChapterSchema(BaseModel):
    id: str
    title: str
    chapter_word_count: int
    startingWords: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = "draft"

class TranscriptionPageSchema(BaseModel):
    index: int
    text: str
    filename: Optional[str] = None

class TranscriptionStatusSchema(BaseModel):
    status: str
    processed_images: int
    total_images: int
    current_image_b64: Optional[str] = None
    current_extracted_text: Optional[str] = None
    new_pages: List[TranscriptionPageSchema] = []
    missing_pages_count: int = 0
    error_message: Optional[str] = None

class CheckpointSchema(BaseModel):
    activeFolderPath: str
    bookTitle: str
    authorName: str
    content: str
    htmlContent: str
    chapters: List[ChapterSchema]
    agentReports: Dict[str, Any]
    arcData: List[Any]

class TranscribeRequestSchema(BaseModel):
    folder_path: str
    mode: str = "live"
    provider: str = "gemini"
    model: str = "gemini-3-flash-preview"    # Vision-capable Flash model
    api_key: str = ""                # Passed from frontend vault; falls back to os.environ if empty
    fallback_provider: str = "groq"
    fallback_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    reset_cache: bool = False
