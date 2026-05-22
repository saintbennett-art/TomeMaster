import os
import logging
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from services import document_parser, exporter, transcriber_service

logger = logging.getLogger(__name__)

def _safe_folder(folder_path: str) -> str:
    """Validates that folder_path resolves inside the user's home directory."""
    resolved = os.path.realpath(os.path.abspath(folder_path))
    home = os.path.realpath(os.path.expanduser("~"))
    if not resolved.startswith(home + os.sep) and resolved != home:
        raise HTTPException(status_code=403, detail="Path outside permitted directory.")
    return resolved

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), api_key: str = "", is_demo: bool = False, recovery: bool = False):
    """Receives a document (.txt, .docx, .pdf, or .epub for recovery), parses standard text and metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    content = await file.read()
    text = ""
    html = ""
    toc = []
    
    filename_lower = file.filename.lower()
    if filename_lower.endswith(".txt"):
        text = document_parser.parse_txt(content)
        html = f"<p>{text.replace(chr(10), '<br>')}</p>"
    elif filename_lower.endswith(".docx"):
        parsed = document_parser.parse_docx(content)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    elif filename_lower.endswith(".pdf"):
        # PDF Manuscripts are automatically routed through the fast Native OR slow OCR tracker
        parsed = document_parser.parse_pdf_smart(content, api_key)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    elif filename_lower.endswith(".epub"):
        if not recovery:
            raise HTTPException(
                status_code=403,
                detail="Sovereign Protocol Violation: Private EPUB recovery is locked. Standard users cannot load external EPUB books into the program."
            )
        parsed = document_parser.parse_epub(content)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format: '{file.filename}'. Tome-Master currently supports .txt, .docx, and .pdf. If you are using an older Word 97 (.doc) file, please 'Save As' .docx and try again."
        )
        
    if is_demo:
        truncated = document_parser.truncate_for_demo({"text": text, "html": html, "toc": toc})
        text = truncated["text"]
        html = truncated["html"]
        toc = truncated["toc"]

    word_count = len(text.split())
    
    return {
        "filename": file.filename,
        "word_count": word_count,
        "content_preview": text[:500] + "..." if len(text) > 500 else text,
        "content": html,
        "toc": toc,
        "raw_text": text
    }

@router.post("/upload/stream")
async def upload_document_stream(file: UploadFile = File(...), api_key: str = "", is_demo: bool = False):
    """Streams the parsed document live to the client as Ndjson."""
    import json
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    content = await file.read()
    
    # If it's a Txt or Docx we just return it immediately as a single 'done' packet because they resolve in milliseconds anyway!
    if not file.filename.lower().endswith(".pdf"):
        # We invoke standard handling, then yield the final state!
        if file.filename.lower().endswith(".txt"):
            text = document_parser.parse_txt(content)
            html = f"<p>{text.replace(chr(10), '<br>')}</p>"
            toc = []
        elif file.filename.lower().endswith(".docx"):
            parsed = document_parser.parse_docx(content)
            text = parsed["text"]
            html = parsed["html"]
            toc = parsed["toc"]
        
        if is_demo:
            truncated = document_parser.truncate_for_demo({"text": text, "html": html, "toc": toc})
            text = truncated["text"]
            html = truncated["html"]
            toc = truncated["toc"]

        def fake_stream():
            yield json.dumps({
                "type": "page",
                "page": 1,
                "total_pages": 1,
                "html": html,
                "text": text,
                "toc_item": None
            }) + "\n"
            yield json.dumps({"type": "done", "message": "File parsed instantly."}) + "\n"
        return StreamingResponse(fake_stream(), media_type="application/x-ndjson")
        
    return StreamingResponse(
        document_parser.stream_pdf_smart(content, api_key, is_demo=is_demo, folder_path=None), 
        media_type="application/x-ndjson"
    )


class ExportRequest(BaseModel):
    content: str
    chapters: list = []
    title: str = "Manuscript Title"
    author: str = "Author Name"
    format: str = "chicago"
    cover_image: Optional[str] = None

@router.post("/export/docx")
async def export_docx(req: ExportRequest):
    """Exports structured manuscript back to a Chicago Style DOCX."""
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")
        
    try:
        doc_stream = exporter.generate_docx(req.content, req.chapters, req.title, req.author, req.format, req.cover_image)
        safe_title = str(req.title).replace('"', '').replace('\n', '').replace('\r', '')
        
        return StreamingResponse(
            doc_stream, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'}
        )
    except Exception as e:
        logger.error("DOCX export error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/pdf")
async def export_pdf(req: ExportRequest):
    """Exports structured manuscript back to a Chicago Style PDF."""
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        pdf_stream = exporter.generate_pdf(req.content, req.chapters, req.title, req.author, req.format, req.cover_image)
        safe_title = str(req.title).replace('"', '').replace('\n', '').replace('\r', '')

        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'}
        )
    except Exception as e:
        logger.error("PDF export error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/epub")
async def export_epub(req: ExportRequest):
    """Exports structured manuscript back to a standard EPUB for Kindle."""
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        epub_stream = exporter.generate_epub(req.content, req.chapters, req.title, req.author, req.format, req.cover_image)
        safe_title = str(req.title).replace('"', '').replace('\n', '').replace('\r', '')

        return StreamingResponse(
            epub_stream,
            media_type="application/epub+zip",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.epub"'}
        )
    except Exception as e:
        logger.error("EPUB export error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

class TranscriptionRequest(BaseModel):
    api_key: str = ""
    provider: str = "gemini"
    folder_path: Optional[str] = None
    reset_cache: bool = False
    mode: str = "batch"
    model: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None

class AuditResolutionRequest(BaseModel):
    page_number: str
    apply_offset: bool = False

class OffsetRequest(BaseModel):
    delta: int

@router.post("/transcribe/start")
def start_transcription(req: TranscriptionRequest):
    """Drops a native folder picker over the browser and triggers the OCR background thread."""
    # Pass the AI key and provider explicitly provided by the React Settings modal
    success, used_folder = transcriber_service.start_transcription_background(
        req.api_key, req.provider, req.folder_path, req.reset_cache, req.mode, req.model,
        fallback_provider=req.fallback_provider, fallback_model=req.fallback_model
    )
    if not success:
        return {"status": "cancelled"}
    return {"status": "started", "folder_path": used_folder}

@router.post("/transcribe/clear")
def clear_transcription():
    """Wipes the current transcription state for a fresh project start."""
    transcriber_service.clear_transcription_state()
    return {"status": "cleared"}

@router.post("/transcribe/resolve")
def resolve_audit(req: AuditResolutionRequest):
    """Resumes a paused transcription after user input."""
    success = transcriber_service.resolve_audit_input(req.page_number, req.apply_offset)
    return {"status": "success" if success else "failed"}

@router.post("/transcribe/offset")
def set_offset(req: OffsetRequest):
    """Adjusts the global page numbering offset."""
    transcriber_service.set_transcription_offset(req.delta)
    return {"status": "offset_applied"}

@router.get("/transcribe/status")
async def get_transcription_status(summary: bool = False):
    """
    Polls the global state. 
    'summary=True' strips the massive 'text' and 'pages' fields for HUD performance,
    but includes 'new_pages' from the stream buffer for the editor.
    """
    with transcriber_service.TRANSCRIPTION_LOCK:
        state = dict(transcriber_service.TRANSCRIPTION_STATE)
        
        # [SMART STREAM]: Destructive fetch of the buffer
        buffer = state.get("stream_buffer", [])
        transcriber_service.TRANSCRIPTION_STATE["stream_buffer"] = []
        
        if summary:
            # Drop heavy data for lightweight polling
            state.pop("text", None)
            state.pop("pages", None)
            # Add the incremental updates
            state["new_pages"] = buffer
            
        return state

@router.post("/transcribe/resort")
async def resort_manuscript_post(req: TranscriptionRequest):
    """Triggers a physical re-sort of the manuscript from the cache."""
    safe_path = _safe_folder(req.folder_path) if req.folder_path else None
    success = transcriber_service.resort_from_cache(safe_path)
    if success:
        return {"status": "success"}
    return {"status": "failed", "message": "Cache not found or corrupt."}

@router.get("/target")
async def target_project_folder():
    """Directorial Target: Invokes the native folder picker and returns the selected path to the UI."""
    folder = transcriber_service.pick_directory()
    if not folder:
        return {"status": "cancelled", "folder_path": None}
    transcriber_service.ingest_project_baseline(folder)
    return {"status": "targeted", "folder_path": folder}

@router.get("/load")
async def load_manuscript_picker():
    """Manuscript Load: Invokes native file picker and targets project to its directory."""
    file_path = transcriber_service.pick_file()
    if not file_path:
        return {"status": "cancelled", "file_path": None}
    
    # Target to the directory containing the file
    folder = os.path.dirname(file_path).replace('\\', '/')
    transcriber_service.ingest_project_baseline(folder)
    
    # [SMART ROUTE]: Check if this file can be text-parsed (no OCR needed)
    from services.transcriber import vision_processor
    is_parseable = vision_processor.is_parseable_document(file_path)
    
    # Return both so the UI can update
    return {
        "status": "loaded", 
        "file_path": file_path, 
        "folder_path": folder,
        "filename": os.path.basename(file_path),
        "is_parseable": is_parseable  # Frontend uses this to skip "Click Transcribe" gate
    }

@router.get("/read")
async def read_local_file(path: str):
    """Reads a local file and returns its content (text or html)."""
    safe_path = _safe_folder(os.path.dirname(path))
    full_path = os.path.join(safe_path, os.path.basename(path))
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Basic heuristic: if it's .md or .txt, return as raw text and simple html
        if path.lower().endswith(".md") or path.lower().endswith(".txt"):
            return {
                "content": content,
                "html": f"<p>{content.replace(chr(10), '<br>')}</p>"
            }
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transcribe/ingest")
async def ingest_project_baseline(folder_path: str):
    """Ingests the project baseline."""
    safe_path = _safe_folder(folder_path)
    success = transcriber_service.ingest_project_baseline(safe_path)
    return {"status": "success" if success else "failed"}

@router.get("/transcribe/resort")
async def resort_manuscript_get(folder_path: str):
    """Triggers manuscript unification via GET (background thread)."""
    import glob
    import threading
    from services.transcriber_service import TRANSCRIPTION_STATE, TRANSCRIPTION_LOCK

    safe_path = _safe_folder(folder_path)

    rtfs = glob.glob(os.path.join(safe_path, "*.rtf"))
    src_subdir = os.path.join(safe_path, "_manuscript_source")
    if os.path.exists(src_subdir):
        rtfs.extend(glob.glob(os.path.join(src_subdir, "*.rtf")))
    count = len(rtfs)

    with TRANSCRIPTION_LOCK:
        TRANSCRIPTION_STATE["status"] = "stitching"
        TRANSCRIPTION_STATE["error_message"] = f"Assembling manuscript: {count} pages ready for unification..."

    if not transcriber_service._stitching_active.is_set():
        thread = threading.Thread(target=transcriber_service.resort_from_cache, args=(safe_path,))
        thread.daemon = True
        thread.start()
    return {"status": "stitching"}

@router.get("/photo")
async def get_project_photo(folder_path: str, filename: str):
    """Securely fetches a photo from the targeted project directory."""
    from fastapi.responses import FileResponse

    safe_base = _safe_folder(folder_path)
    # Prevent filename from escaping the safe base via traversal components
    safe_filename = os.path.basename(filename)
    photo_path = os.path.realpath(os.path.join(safe_base, safe_filename))

    if not photo_path.startswith(safe_base + os.sep):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not os.path.exists(photo_path):
        raise HTTPException(status_code=404, detail="Photo not found.")

    return FileResponse(photo_path)
