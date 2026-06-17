@echo off
echo ===========================================================
echo  TomeMaster - Sovereign Standalone Desktop Build (Windows)
echo ===========================================================
setlocal
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"

:: ─── [0/5] Strip developer secrets / local logs ────────────────────────────
echo [0/5] Stripping developer secrets and local logs...
if exist "%BACKEND%\.env"               del /f /q "%BACKEND%\.env"
if exist "%ROOT%frontend\.env"          del /f /q "%ROOT%frontend\.env"
if exist "%ROOT%frontend\.env.local"    del /f /q "%ROOT%frontend\.env.local"
if exist "%BACKEND%\api_usage_log.jsonl" del /f /q "%BACKEND%\api_usage_log.jsonl"

:: ─── [1/5] Build the Next.js frontend (static export) ──────────────────────
echo [1/5] Building frontend static export...
pushd "%ROOT%frontend"
call npm install
call npm run build
if not exist "out\index.html" (
    echo [BUILD ERROR]: frontend\out was not produced. Aborting.
    popd & pause & exit /b 1
)
popd

:: ─── [2/5] Merge frontend into backend\static (what main.py serves frozen) ──
echo [2/5] Merging frontend into backend\static...
if exist "%BACKEND%\static" rmdir /s /q "%BACKEND%\static"
xcopy /s /e /y /i "%ROOT%frontend\out\*" "%BACKEND%\static\" >nul

:: ─── [3/5] Build dependencies (NO legacy google-generativeai v1) ───────────
echo [3/5] Installing build dependencies...
pushd "%BACKEND%"
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install pyinstaller pywebview
pip install -r requirements.txt

:: ─── [4/5] Compile the standalone executable ───────────────────────────────
:: Bundles: static frontend, get_key.py (machine fingerprint) and src\ (vault
:: loader) at the bundle root so runtime imports resolve. Hidden-imports cover
:: uvicorn's lazily-loaded protocol modules and the AI SDKs imported inside
:: functions. Heavy/optional stacks are excluded to keep the binary lean.
echo [4/5] Compiling TomeMaster.exe (PyInstaller)...
pyinstaller --noconfirm --clean --onefile --noconsole ^
  --name TomeMaster ^
  --paths "%ROOT%" ^
  --add-data "static;static" ^
  --add-data "%ROOT%get_key.py;." ^
  --add-data "%ROOT%src;src" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import google.genai ^
  --hidden-import openai ^
  --hidden-import anthropic ^
  --exclude-module presidio_analyzer ^
  --exclude-module presidio_anonymizer ^
  --exclude-module spacy ^
  --exclude-module celery ^
  --exclude-module redis ^
  --exclude-module torch ^
  --exclude-module crewai ^
  desktop_app.py
if not exist "dist\TomeMaster.exe" (
    echo [BUILD ERROR]: PyInstaller did not produce dist\TomeMaster.exe.
    popd & pause & exit /b 1
)
popd

:: ─── [5/5] Place the executable at the project root ─────────────────────────
echo [5/5] Finalizing...
move /y "%BACKEND%\dist\TomeMaster.exe" "%ROOT%TomeMaster.exe" >nul
echo.
echo ===========================================================
echo  SUCCESS - standalone app at: %ROOT%TomeMaster.exe
echo  No Python, Node, or browser required to run it.
echo  (Windows needs the Edge WebView2 runtime; ships with Win11.)
echo ===========================================================
pause
endlocal
