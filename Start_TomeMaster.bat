@echo off
title Tome-Master Server Launcher
echo Performing Surgical Sweep (Port 8080, 3000 and Language Server)...
:: taskkill /F /IM language_server_windows_x64.exe /T >nul 2>&1
:: powershell -Command "Get-NetTCPConnection -LocalPort 8080,3000 -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -ne 0) { Stop-Process -Id $_.OwningProcess -Force } }" >nul 2>&1

echo.
echo Starting Tome-Master Backend (Apex Engine on 8080)...
start "Tome-Master Backend" cmd /k "cd C:\Users\saint\.gemini\antigravity\playground\dark-schrodinger\backend && .\venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080 --timeout-keep-alive 300"

echo Starting Tome-Master Frontend (React UI)...
start "Tome-Master Frontend" cmd /k "cd C:\Users\saint\.gemini\antigravity\playground\dark-schrodinger\frontend && npm run dev"

echo.
echo ========================================================
echo Tome-Master is currently booting up!
echo.
echo 1. Keep the two black terminal windows open (they run the servers).
echo 2. Wait approximately 5 seconds for the servers to initialize.
echo 3. Open your web browser and navigate directly to:
echo    http://localhost:3000
echo.
echo ========================================================
echo.
pause
