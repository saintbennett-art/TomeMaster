@echo off
title TomeMaster Sovereign Workstation
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "PORT_SIGNAL=%PROJECT_ROOT%.sovereign_port"
set "VENV_PY=%BACKEND_DIR%\venv\Scripts\python.exe"

:: ─── PHASE 0: Prerequisites (check, install if missing) ──────────────────────
echo [SOVEREIGN]: Verifying prerequisites...

if not exist "%VENV_PY%" (
    echo [SOVEREIGN]: Backend venv missing - creating and installing dependencies...
    pushd "%BACKEND_DIR%"
    python -m venv venv
    if errorlevel 1 (
        echo [SOVEREIGN ERROR]: Could not create venv. Is Python installed and on PATH?
        popd
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    popd
) else (
    echo [SOVEREIGN]: Backend venv present.
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [SOVEREIGN]: Frontend dependencies missing - running npm install...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
) else (
    echo [SOVEREIGN]: Frontend dependencies present.
)

:: ─── PHASE 1: Clean prior session ────────────────────────────────────────────
echo [SOVEREIGN]: Clearing prior session artifacts...
if exist "%PORT_SIGNAL%" del /f /q "%PORT_SIGNAL%"

:: ─── PHASE 2: Claim a free frontend port (zero hardcode) ──────────────────────
:: Same approach as the backend: ask the OS for a free port, no fixed number.
:: scripts\free_port.py prints a free port; we capture it via a temp signal file
:: (more robust than for/f, which mangles quoted paths). Mirrors .sovereign_port.
set "FE_PORT_SIGNAL=%PROJECT_ROOT%.frontend_port"
"%VENV_PY%" "%PROJECT_ROOT%scripts\free_port.py" > "%FE_PORT_SIGNAL%" 2>nul
set /p FRONTEND_PORT=<"%FE_PORT_SIGNAL%"
del /f /q "%FE_PORT_SIGNAL%" 2>nul
if "%FRONTEND_PORT%"=="" (
    echo [SOVEREIGN ERROR]: Failed to claim a frontend port.
    pause
    exit /b 1
)
echo [SOVEREIGN]: Frontend port claimed: %FRONTEND_PORT%

:: ─── PHASE 3: Start backend (claims its own free port via run.py) ─────────────
echo [SOVEREIGN]: Starting Intelligence Engine (dynamic port handshake)...
start "TomeMaster Backend" cmd /k "cd /d "%BACKEND_DIR%" && venv\Scripts\activate.bat && python run.py"

:: ─── PHASE 4: Wait for backend port signal ───────────────────────────────────
echo [SOVEREIGN]: Awaiting backend port handshake...
set /a WAIT_COUNT=0
:WAIT_BACKEND
    timeout /t 1 /nobreak >nul
    set /a WAIT_COUNT+=1
    if exist "%PORT_SIGNAL%" goto BACKEND_READY
    if !WAIT_COUNT! GEQ 30 goto BACKEND_TIMEOUT
goto WAIT_BACKEND

:BACKEND_READY
set /p BACKEND_PORT=<"%PORT_SIGNAL%"
echo [SOVEREIGN]: Backend anchored on port !BACKEND_PORT!

:: ─── PHASE 5: Start frontend on the claimed port ──────────────────────────────
echo [SOVEREIGN]: Starting Narrative Interface on port %FRONTEND_PORT%...
start "TomeMaster Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- -p %FRONTEND_PORT%"

:: ─── PHASE 6: Wait until the frontend is ACTUALLY serving ─────────────────────
:: First-run Turbopack compile can take a while; poll the port instead of a fixed
:: sleep so the browser never opens onto a dead page.
echo [SOVEREIGN]: Waiting for the interface to compile (first run can take a minute)...
where curl >nul 2>&1
if errorlevel 1 (
    echo [SOVEREIGN]: curl unavailable - using a fixed warm-up wait.
    timeout /t 20 /nobreak >nul
    goto FRONTEND_READY
)
set /a FE_WAIT=0
:WAIT_FRONTEND
    timeout /t 2 /nobreak >nul
    set /a FE_WAIT+=2
    curl -s -o nul "http://127.0.0.1:%FRONTEND_PORT%" && goto FRONTEND_READY
    if !FE_WAIT! GEQ 120 goto FRONTEND_TIMEOUT
goto WAIT_FRONTEND

:FRONTEND_READY
echo [SOVEREIGN]: Interface ready.

:: ─── PHASE 7: Open the browser ONLY now, backend port injected ────────────────
echo [SOVEREIGN]: Opening workstation...
start "" "http://localhost:%FRONTEND_PORT%/?api_port=!BACKEND_PORT!"

echo.
echo ================================================================
echo  TomeMaster Sovereign Workstation - OPERATIONAL
echo ================================================================
echo  Backend:   http://127.0.0.1:!BACKEND_PORT!/api/v1
echo  Frontend:  http://localhost:%FRONTEND_PORT%
echo  Handshake: ?api_port=!BACKEND_PORT! (injected)
echo ================================================================
echo.
echo  Keep both terminal windows open.
echo  Close this window when done - port signal auto-cleans on exit.
echo.
goto END

:BACKEND_TIMEOUT
echo.
echo [SOVEREIGN ERROR]: Backend did not broadcast its port within 30 seconds.
echo  Check the Backend terminal window for startup errors.
goto END

:FRONTEND_TIMEOUT
echo.
echo [SOVEREIGN WARNING]: Frontend did not respond within 120s.
echo  Opening anyway - if the page is blank, give it a moment and refresh.
start "" "http://localhost:%FRONTEND_PORT%/?api_port=!BACKEND_PORT!"

:END
pause
endlocal
