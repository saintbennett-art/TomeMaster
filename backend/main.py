import sys
import os
import subprocess
import threading

# [WINDOWS CONSOLE GUARD]: cp1252 consoles crash print() on em-dashes/arrows in
# log lines, and those UnicodeEncodeErrors have aborted worker pipelines
# (e.g. post-stitch cleanup Phase 2). Make stdout/stderr tolerant once, here,
# so no print anywhere can kill a job.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


# [SOVEREIGN ENGINE]: Standard initialization sequence
# [KEY PERSISTENCE]: Hydrate env vars from encrypted vault at startup.
# Keys saved via Settings → Seal Vault are written to settings.enc (Fernet AES).
# This ensures they survive application restarts without re-entry.
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from src.tomemaster.vault_loader import inject_keys_to_env
    if inject_keys_to_env():
        print("[VAULT HYDRATION]: API keys restored from encrypted vault.")
    else:
        print("[VAULT HYDRATION]: No saved keys found — enter them in Settings.")
except Exception as e:
    print(f"[VAULT HYDRATION WARNING]: Could not restore keys: {e}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from routers import boardroom, vault, system, document, license, ai, transcribe, settings

app = FastAPI(
    title="tome_master API",
    description="Backend API for the tome_master Manuscript Formatting SaaS",
    version="1.0.0"
)

# Configure CORS: Allow any localhost/127.0.0.1 port (desktop app — frontend port varies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boardroom.router, prefix="/api/v1/analysis", tags=["AI Boardroom"])
app.include_router(vault.router, prefix="/api/v1/analysis", tags=["Vault & Settings"])
app.include_router(system.router, prefix="/api/v1/analysis", tags=["System & Telemetry"])
app.include_router(document.router, prefix="/api/v1/document", tags=["Document Processing"])
app.include_router(license.router, prefix="/api/v1/license", tags=["License"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Status"])
app.include_router(transcribe.router, prefix="/api/v1/transcribe", tags=["Transcription"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])

# PyInstaller static file hosting
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    static_dir = os.path.join(sys._MEIPASS, "static")
else:
    static_dir = "static"

if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.exception_handler(404)
    async def custom_404_handler(request, exc):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"detail": "Not Found", "message": "Static frontend not found at /static/index.html"})
else:
    @app.get("/")
    def read_root():
        return {"status": "ok", "message": "tome_master API is running, but static frontend was not found."}

