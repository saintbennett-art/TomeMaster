import os
import logging
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from services import exporter, transcriber_service
from services import export_fountain, export_fdx, export_odt
from services.parsers import (
    parse_txt,
    parse_docx,
    parse_pdf_smart,
    stream_pdf_smart,
    parse_epub,
    truncate_for_demo,
)

logger = logging.getLogger(__name__)

# [SHARED GUARDRAIL]: One canonical path validator + upload-size guard for every router.
from services.security import (
    validate_project_path as _safe_folder,
    read_upload_capped,
    read_upload_capped_sync,
    MAX_UPLOAD_BYTES,
)

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), api_key: str = "", is_demo: bool = False, recovery: bool = False):
    """Receives a document (.txt, .docx, .pdf, or .epub for recovery), parses standard text and metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    content = await read_upload_capped(file)
    text = ""
    html = ""
    toc = []
    
    filename_lower = file.filename.lower()
    if filename_lower.endswith(".txt"):
        text = parse_txt(content)
        html = f"<p>{text.replace(chr(10), '<br>')}</p>"
    elif filename_lower.endswith(".docx"):
        parsed = parse_docx(content)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    elif filename_lower.endswith(".pdf"):
        # PDF Manuscripts are automatically routed through the fast Native OR slow OCR tracker
        parsed = parse_pdf_smart(content, api_key)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    elif filename_lower.endswith(".epub"):
        if not recovery:
            raise HTTPException(
                status_code=403,
                detail="Sovereign Protocol Violation: Private EPUB recovery is locked. Standard users cannot load external EPUB books into the program."
            )
        parsed = parse_epub(content)
        text = parsed["text"]
        html = parsed["html"]
        toc = parsed["toc"]
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format: '{file.filename}'. Tome-Master currently supports .txt, .docx, and .pdf. If you are using an older Word 97 (.doc) file, please 'Save As' .docx and try again."
        )
        
    if is_demo:
        truncated = truncate_for_demo({"text": text, "html": html, "toc": toc})
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
    
    content = await read_upload_capped(file)

    # If it's a Txt or Docx we just return it immediately as a single 'done' packet because they resolve in milliseconds anyway!
    if not file.filename.lower().endswith(".pdf"):
        # We invoke standard handling, then yield the final state!
        if file.filename.lower().endswith(".txt"):
            text = parse_txt(content)
            html = f"<p>{text.replace(chr(10), '<br>')}</p>"
            toc = []
        elif file.filename.lower().endswith(".docx"):
            parsed = parse_docx(content)
            text = parsed["text"]
            html = parsed["html"]
            toc = parsed["toc"]
        else:
            # [FIX]: Anything else previously fell through with text/html/toc
            # unassigned -> UnboundLocalError -> raw 500. Mirror /upload's
            # friendly rejection instead.
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: '{file.filename}'. Streaming upload supports .txt, .docx, and .pdf. "
                       "If you are using an older Word 97 (.doc) file, please 'Save As' .docx and try again."
            )

        if is_demo:
            truncated = truncate_for_demo({"text": text, "html": html, "toc": toc})
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
        stream_pdf_smart(content, api_key, is_demo=is_demo, folder_path=None), 
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


# ─── Lightweight text formats: Markdown / RTF / HTML / Plain text ─────────────
# Same ExportRequest payload as docx/pdf/epub; each delegates to exporter.generate_*.
# A small table keeps the route bodies identical so adding a format is one entry.
_TEXT_EXPORTS = {
    "md":   (lambda req: exporter.generate_markdown(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "text/markdown; charset=utf-8", "md", "Markdown"),
    "html": (lambda req: exporter.generate_html(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "text/html; charset=utf-8", "html", "HTML"),
    "rtf":  (lambda req: exporter.generate_rtf(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "application/rtf", "rtf", "RTF"),
    "txt":  (lambda req: exporter.generate_txt(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "text/plain; charset=utf-8", "txt", "Plain text"),
    "fountain": (lambda req: export_fountain.generate_fountain(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "text/plain; charset=utf-8", "fountain", "Fountain"),
    "fdx":  (lambda req: export_fdx.generate_fdx(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "application/xml; charset=utf-8", "fdx", "Final Draft"),
    "odt":  (lambda req: export_odt.generate_odt(req.content, req.chapters, req.title, req.author, req.format, req.cover_image),
             "application/vnd.oasis.opendocument.text", "odt", "OpenDocument"),
}


def _run_text_export(kind: str, req: "ExportRequest"):
    if not req.content:
        raise HTTPException(status_code=400, detail="Content is required")
    generate, media_type, ext, label = _TEXT_EXPORTS[kind]
    try:
        stream = generate(req)
        safe_title = str(req.title).replace('"', '').replace('\n', '').replace('\r', '')
        return StreamingResponse(
            stream,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.{ext}"'},
        )
    except Exception as e:
        logger.error("%s export error:\n%s", label, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/md")
async def export_md(req: ExportRequest):
    """Exports the manuscript to CommonMark Markdown (.md)."""
    return _run_text_export("md", req)


@router.post("/export/html")
async def export_html(req: ExportRequest):
    """Exports the manuscript to a self-contained HTML file (.html)."""
    return _run_text_export("html", req)


@router.post("/export/rtf")
async def export_rtf(req: ExportRequest):
    """Exports the manuscript to Rich Text Format (.rtf)."""
    return _run_text_export("rtf", req)


@router.post("/export/txt")
async def export_txt(req: ExportRequest):
    """Exports the manuscript to plain UTF-8 text (.txt)."""
    return _run_text_export("txt", req)


@router.post("/export/fountain")
async def export_fountain_route(req: ExportRequest):
    """Exports the manuscript to Fountain screenplay plain text (.fountain)."""
    return _run_text_export("fountain", req)


@router.post("/export/fdx")
async def export_fdx_route(req: ExportRequest):
    """Exports the manuscript to Final Draft XML (.fdx)."""
    return _run_text_export("fdx", req)


@router.post("/export/odt")
async def export_odt_route(req: ExportRequest):
    """Exports the manuscript to OpenDocument Text (.odt)."""
    return _run_text_export("odt", req)

# ─────────────────────────────────────────────────────────────────────────────
# [CONSOLIDATED]: The /transcribe/* endpoints that used to live here (start,
# clear, resolve, offset, status, resort, ingest) were duplicates of
# routers/transcribe.py with drifted behavior — notably, two status endpoints
# destructively drained the same stream_buffer, losing pages for whichever
# poller arrived second. The canonical surface is /api/v1/transcribe/*.
# This router keeps document concerns only: upload, export, target, load,
# read, photo.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/target")
def target_project_folder():
    """Directorial Target: Invokes the native folder picker and returns the selected path to the UI.

    SYNC def (not async): pick_directory() opens a BLOCKING native dialog. As an
    async endpoint it would freeze the whole event loop (backend appears to
    'disconnect' / picker never reopens). FastAPI runs sync defs in a threadpool.
    """
    folder = transcriber_service.pick_directory()
    if not folder:
        return {"status": "cancelled", "folder_path": None}
    transcriber_service.ingest_project_baseline(folder)
    return {"status": "targeted", "folder_path": folder}

@router.get("/load")
def load_manuscript_picker():
    """Manuscript Load: Invokes native file picker and targets project to its directory.

    SYNC def (not async): pick_file() opens a BLOCKING native dialog; as an async
    endpoint it freezes the event loop (blank screen, picker won't reopen, backend
    'disconnects'). FastAPI runs sync defs in a threadpool so the loop stays free.
    """
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

@router.post("/upload-to-project")
def upload_to_project(file: UploadFile = File(...)):
    """[BROWSER LOAD — FULL FIDELITY]: Saves an uploaded manuscript to a real
    on-disk project folder and returns the SAME shape as /document/load, so
    browser mode reuses the *entire* native load+transcribe pipeline — every
    format the desktop picker supported (.txt/.md/.doc/.docx/.wpd/.wps/.odt/.pdf,
    incl. legacy Word/WordPerfect via legacy_parser) — with no capability loss.

    SYNC def (not async): the file write + parseable probe are blocking, so they
    run in FastAPI's threadpool, never freezing the event loop. The frontend's
    invokeTranscription does the actual ingestion/parsing afterward.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    base = os.path.join(os.path.expanduser("~"), "TomeMaster", "Uploads")
    os.makedirs(base, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    dest = os.path.join(base, safe_name)

    data = read_upload_capped_sync(file)   # sync, size-capped read of the spooled upload
    with open(dest, "wb") as fh:
        fh.write(data)

    dest_norm = dest.replace("\\", "/")
    from services.transcriber import vision_processor
    is_parseable = vision_processor.is_parseable_document(dest_norm)

    return {
        "status": "loaded",
        "file_path": dest_norm,
        "folder_path": base.replace("\\", "/"),
        "filename": safe_name,
        "is_parseable": is_parseable,
    }

class ProjectSaveRequest(BaseModel):
    state: dict
    project_path: Optional[str] = None


@router.post("/project/save")
def save_project(req: ProjectSaveRequest):
    """[FILES-ONLY PERSISTENCE]: Saves the full manuscript document (draft html/text,
    TOC, analysis artifacts, metadata) to tome_master_project.json in the project
    folder — replacing browser IndexedDB. Falls back to ~/TomeMaster/Workspace for
    drafts with no active folder yet. Every path goes through the home-dir guard."""
    from services import persistence_service

    target = req.project_path or persistence_service.default_workspace_dir()
    safe = _safe_folder(target)
    ok = persistence_service.save_project_state(safe, req.state or {})
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write project state.")
    return {"status": "saved", "folder_path": safe.replace("\\", "/")}


@router.get("/project/load")
def load_project(project_path: Optional[str] = None):
    """[FILES-ONLY PERSISTENCE]: Reads the manuscript document back from the project
    folder (or the default workspace). Returns {} when nothing is stored yet."""
    from services import persistence_service

    target = project_path or persistence_service.default_workspace_dir()
    safe = _safe_folder(target)
    return {"state": persistence_service.load_project_state(safe), "folder_path": safe.replace("\\", "/")}


# [READ GUARD]: /read is a text-file viewer, not a general file-read primitive.
# Session auth (main.py) already gates it against other local processes; this
# also confines it to the manuscript/text formats it actually serves so it can't
# be used to siphon arbitrary files under $HOME.
_READABLE_EXTS = {".txt", ".md", ".rtf", ".html", ".htm", ".json", ".fountain"}


@router.get("/read")
async def read_local_file(path: str):
    """Reads a local text/manuscript file and returns its content (text or html)."""
    safe_path = _safe_folder(os.path.dirname(path))
    full_path = os.path.join(safe_path, os.path.basename(path))

    ext = os.path.splitext(full_path)[1].lower()
    if ext not in _READABLE_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext or '(none)'}'. /read serves text formats only: "
                   f"{', '.join(sorted(_READABLE_EXTS))}.",
        )

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.getsize(full_path) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB read limit.",
        )

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
