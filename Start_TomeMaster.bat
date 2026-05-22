@echo off
title TomeMaster Sovereign Workstation
setlocal

set PROJECT_ROOT=%~dp0
set BACKEND_DIR=%PROJECT_ROOT%backend
set PORT_SIGNAL=%PROJECT_ROOT%.sovereign_port

:: ─── PHASE 1: Clean Prior Session ────────────────────────────────────────────
echo [SOVEREIGN]: Clearing prior session artifacts...
if exist "%PORT_SIGNAL%" del /f /q "%PORT_SIGNAL%"

:: ─── PHASE 2: Start Backend (Claims Free OS Port Automatically) ───────────────
echo [SOVEREIGN]: Starting Intelligence Engine (Dynamic Port Handshake)...
start "TomeMaster Backend" cmd /k "cd /d "%BACKEND_DIR%" && venv\Scripts\activate.bat && python run.py"

:: ─── PHASE 3: Wait for Port Signal (Backend Broadcasts Its Port) ──────────────
echo [SOVEREIGN]: Awaiting port handshake signal...
set /a WAIT_COUNT=0
:WAIT_LOOP
    timeout /t 1 /nobreak >nul
    set /a WAIT_COUNT+=1
    if exist "%PORT_SIGNAL%" goto PORT_FOUND
    if %WAIT_COUNT% GEQ 20 goto TIMEOUT_ERROR
goto WAIT_LOOP

:PORT_FOUND
:: Read the port from the signal file
set /p BACKEND_PORT=<"%PORT_SIGNAL%"
echo [SOVEREIGN]: Handshake confirmed — Backend anchored on port %BACKEND_PORT%

:: ─── PHASE 4: Start Frontend (Dev Mode) ──────────────────────────────────────
echo [SOVEREIGN]: Starting Narrative Interface...
start "TomeMaster Frontend" cmd /k "cd /d "%PROJECT_ROOT%frontend" && npm run dev"

:: ─── PHASE 5: Wait for Frontend to Initialize ─────────────────────────────────
echo [SOVEREIGN]: Waiting for frontend initialization...
timeout /t 6 /nobreak >nul

:: ─── PHASE 6: Open Browser WITH Port Handshake Injected ───────────────────────
echo [SOVEREIGN]: Opening workstation at http://localhost:3333?api_port=%BACKEND_PORT%
start "" "http://localhost:3333?api_port=%BACKEND_PORT%"

echo.
echo ================================================================
echo  TomeMaster Sovereign Workstation — OPERATIONAL
echo ================================================================
echo  Backend:   http://127.0.0.1:%BACKEND_PORT%/api/v1
echo  Frontend:  http://localhost:3333
echo  Handshake: ?api_port=%BACKEND_PORT% (injected)
echo ================================================================
echo.
echo  Keep both terminal windows open.
echo  Close this window when done — port signal auto-cleans on exit.
echo.
goto END

:TIMEOUT_ERROR
echo.
echo [SOVEREIGN ERROR]: Backend did not broadcast its port within 20 seconds.
echo  Check the Backend terminal window for startup errors.
echo.

:END
pause
