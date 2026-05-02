import sys
import os
import subprocess

import threading

# [SOVEREIGN ENGINE]: Standard initialization sequence
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import analysis, document, license, ai, transcribe, settings

app = FastAPI(
    title="tome_master API",
    description="Backend API for the tome_master Manuscript Formatting SaaS",
    version="1.0.0"
)

# Configure CORS: Hyper-Permissive Anchor for development stability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
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
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"status": "ok", "message": "tome_master API is running, but static frontend was not found."}

