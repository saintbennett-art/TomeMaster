@echo off
title TomeMaster Sovereign Workstation
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "VENV_PY=%BACKEND_DIR%\venv\Scripts\python.exe"
set "BACKEND_PORT=8090"
set "FRONTEND_PORT=3000"

:: ─── PHASE 0: Prerequisites ──────────────────────────────────────────────────
echo [SOVEREIGN]: Verifying prerequisites...
if not exist "%VENV_PY%" (
    echo [SOVEREIGN]: Backend venv missing - creating and installing dependencies...
    pushd "%BACKEND_DIR%"
    python -m venv venv
    if errorlevel 1 ( echo [ERROR]: Could not create venv. Is Python on PATH? & popd & pause & exit /b 1 )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    popd
) else ( echo [SOVEREIGN]: Backend venv present. )

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [SOVEREIGN]: Frontend dependencies missing - running npm install...
    pushd "%FRONTEND_DIR%" & call npm install & popd
) else ( echo [SOVEREIGN]: Frontend dependencies present. )

:: ─── PHASE 1: Surgical sweep — kill any stale servers on our fixed ports ──────
:: Restores the original PRoeditor model: FIXED ports + auto-reload. Stale
:: backends fighting over a port were the cause of the "backend disconnects" bug.
echo [SOVEREIGN]: Stopping any stale backend (uvicorn/run.py) and freeing ports %BACKEND_PORT% / %FRONTEND_PORT%...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and ($_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*run.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %BACKEND_PORT%,%FRONTEND_PORT% -State Listen -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -ne 0) { Stop-Process -Id $_.OwningProcess -Force } }" >nul 2>&1
if exist "%PROJECT_ROOT%.sovereign_port" del /f /q "%PROJECT_ROOT%.sovereign_port"

:: ─── PHASE 2: Start backend (FIXED port + --reload) ───────────────────────────
echo [SOVEREIGN]: Starting Intelligence Engine on http://127.0.0.1:%BACKEND_PORT% (auto-reload)...
start "TomeMaster Backend" cmd /k "cd /d "%BACKEND_DIR%" && venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 127.0.0.1 --port %BACKEND_PORT% --timeout-keep-alive 300"

:: ─── PHASE 3: Wait for backend health ─────────────────────────────────────────
echo [SOVEREIGN]: Awaiting backend health on port %BACKEND_PORT%...
set /a WAIT=0
:WAIT_BACKEND
    timeout /t 1 /nobreak >nul
    set /a WAIT+=1
    curl -s -o nul "http://127.0.0.1:%BACKEND_PORT%/api/v1/ai/status" && goto BACKEND_READY
    if !WAIT! GEQ 40 ( echo [WARNING]: Backend slow to respond - continuing anyway. & goto BACKEND_READY )
goto WAIT_BACKEND
:BACKEND_READY
echo [SOVEREIGN]: Backend anchored on port %BACKEND_PORT%.

:: ─── PHASE 4: Start frontend (FIXED port) ─────────────────────────────────────
echo [SOVEREIGN]: Starting Narrative Interface on http://localhost:%FRONTEND_PORT%...
start "TomeMaster Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- -p %FRONTEND_PORT%"

:: ─── PHASE 5: Wait until the frontend is actually serving ─────────────────────
echo [SOVEREIGN]: Waiting for the interface to compile (first run can take a minute)...
set /a FE=0
:WAIT_FRONTEND
    timeout /t 2 /nobreak >nul
    set /a FE+=2
    curl -s -o nul "http://127.0.0.1:%FRONTEND_PORT%" && goto FRONTEND_READY
    if !FE! GEQ 120 ( echo [WARNING]: Frontend slow - opening anyway. & goto FRONTEND_READY )
goto WAIT_FRONTEND
:FRONTEND_READY

:: ─── PHASE 6: Open the browser with the fixed backend port injected ───────────
echo [SOVEREIGN]: Opening workstation...
start "" "http://localhost:%FRONTEND_PORT%/?api_port=%BACKEND_PORT%"

echo.
echo ================================================================
echo  TomeMaster Sovereign Workstation - OPERATIONAL
echo  Backend:   http://127.0.0.1:%BACKEND_PORT%/api/v1   (auto-reload)
echo  Frontend:  http://localhost:%FRONTEND_PORT%
echo  Open:      http://localhost:%FRONTEND_PORT%/?api_port=%BACKEND_PORT%
echo ================================================================
echo  Keep the two terminal windows open. Code changes auto-reload.
echo.
pause
endlocal
