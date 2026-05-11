@echo off
title Antigravity Surgical UI Reset
echo 1. Closing all Antigravity processes...
taskkill /F /IM Antigravity.exe /T >nul 2>&1
timeout /t 2 >nul

echo 2. Clearing Zombie Workspace Cache...
set "WORKSPACE_CACHE=C:\Users\saint\AppData\Roaming\xAntigravity\User\workspaceStorage\83ff5d1531fdf14643c757dfb55c1496"
if exist "%WORKSPACE_CACHE%" (
    rmdir /S /Q "%WORKSPACE_CACHE%"
)

echo 3. Re-initializing Project Root...
mkdir "%WORKSPACE_CACHE%"
echo { "folder": "file:///c%%3A/Users/saint/.gemini/antigravity/playground/dark-schrodinger" } > "%WORKSPACE_CACHE%\workspace.json"

echo 4. Restarting Antigravity...
start "" "C:\Users\saint\AppData\Local\Programs\Antigravity\Antigravity.exe" "C:\Users\saint\.gemini\antigravity\playground\dark-schrodinger"

echo Reset Complete. Please wait for the window to open.
pause
