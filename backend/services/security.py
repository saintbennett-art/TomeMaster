import os
from fastapi import HTTPException, UploadFile


# ─── Upload size guard ───────────────────────────────────────────────────────
# Cap client-supplied uploads so a huge or garbage file can't exhaust RAM
# (`await file.read()` materializes the whole payload) or fill the disk
# (/upload-to-project and /save-recording write it out). The default is generous
# — scanned image PDFs are legitimately large — but finite, and tunable via env.

def _max_upload_bytes() -> int:
    try:
        mb = int(os.environ.get("TOME_MAX_UPLOAD_MB", "500"))
    except (TypeError, ValueError):
        mb = 500
    return max(1, mb) * 1024 * 1024


MAX_UPLOAD_BYTES = _max_upload_bytes()
_UPLOAD_CHUNK = 1024 * 1024  # 1 MB


def _too_large(cap: int) -> HTTPException:
    return HTTPException(
        status_code=413,
        detail=f"File exceeds the {cap // (1024 * 1024)} MB upload limit.",
    )


def _precheck_declared_size(file: UploadFile, cap: int) -> None:
    """Fast reject when the size is already known (Content-Length / spooled file),
    before a single byte is read."""
    size = getattr(file, "size", None)
    if size is not None and size > cap:
        raise _too_large(cap)


async def read_upload_capped(file: UploadFile, max_bytes: int = None) -> bytes:
    """Read an UploadFile fully, aborting with HTTP 413 the moment it crosses the
    cap — bounds memory even when Content-Length is absent or spoofed. For async
    endpoints."""
    cap = max_bytes or MAX_UPLOAD_BYTES
    _precheck_declared_size(file, cap)
    chunks, total = [], 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise _too_large(cap)
        chunks.append(chunk)
    return b"".join(chunks)


def read_upload_capped_sync(file: UploadFile, max_bytes: int = None) -> bytes:
    """Sync variant for sync endpoints (FastAPI runs them in a threadpool)."""
    cap = max_bytes or MAX_UPLOAD_BYTES
    _precheck_declared_size(file, cap)
    chunks, total = [], 0
    while True:
        chunk = file.file.read(_UPLOAD_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise _too_large(cap)
        chunks.append(chunk)
    return b"".join(chunks)


def enforce_decoded_size(byte_len: int, max_bytes: int = None) -> None:
    """Guard for already-in-hand payloads (e.g. base64 data-URLs): raise 413 if
    the declared/decoded length exceeds the cap."""
    cap = max_bytes or MAX_UPLOAD_BYTES
    if byte_len > cap:
        raise _too_large(cap)


def validate_project_path(folder_path: str) -> str:
    """
    [SOVEREIGN GUARDRAIL]: Resolves and validates that a path stays within 
    the user's home directory tree. Required for Government/Educational security compliance.
    """
    if not folder_path:
        raise HTTPException(status_code=400, detail="Folder path is required.")
        
    try:
        # Resolve to absolute path
        resolved = os.path.realpath(os.path.abspath(folder_path))
        
        # Determine the user's home root
        home = os.path.realpath(os.path.expanduser("~"))
        
        # SECURITY GATE: Path must be sub-directory of Home
        if not resolved.startswith(home + os.sep) and resolved != home:
            print(f"SECURITY ALERT: Unauthorized path access attempted: {resolved}")
            raise HTTPException(status_code=403, detail="Path outside permitted directory.")
            
        return resolved
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Path Validation Failure: {str(e)}")
