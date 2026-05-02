@echo off
echo ===================================================
echo   ANTIGRAVITY WORKSPACE RESTORATION (OFFLINE MODE)
echo ===================================================
echo.
echo 1. Stopping trashing processes (CPU Cleanup)...
taskkill /F /IM Antigravity.exe /T >nul 2>&1
timeout /t 2 >nul

echo 2. Clearing corrupted workspace cache...
echo Removing session 83ff...
rmdir /S /Q "C:\Users\saint\AppData\Roaming\Antigravity\User\workspaceStorage\83ff5d1531fdf14643c757dfb55c1496" >nul 2>&1
echo Removing session 643d...
rmdir /S /Q "C:\Users\saint\AppData\Roaming\Antigravity\User\workspaceStorage\643d006ff228bd050220adeb09d93217" >nul 2>&1

echo 3. Resetting UI state database...
:: del /Q "C:\Users\saint\AppData\Roaming\Antigravity\User\globalStorage\state.vscdb" >nul 2>&1
echo [SKIPPED] state.vscdb preserved for login persistence.

echo 4. Sovereign Extension Purge (Removing Redundant Tools)...
:: Removing process-heavy or redundant extensions
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\meta.pyrefly-0.63.0-win32-x64" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\ms-edgedevtools.vscode-edge-devtools-2.1.10-universal" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\golang.go-0.52.2-universal" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\redhat.java-1.54.0-win32-x64" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\shopify.ruby-lsp-0.10.3-universal" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\llvm-vs-code-extensions.vscode-clangd-0.4.0-universal" >nul 2>&1
rmdir /S /Q "C:\Users\saint\.antigravity\extensions\devsense.phptools-vscode-1.70.18740-win32-x64" >nul 2>&1
:: Clean up Java dependencies
for /d %%i in ("C:\Users\saint\.antigravity\extensions\vscjava.*") do rmdir /S /Q "%%i" >nul 2>&1

echo 5. Launching Clean ProEditor Workspace...
start "" "C:\Users\saint\AppData\Local\Programs\Antigravity\Antigravity.exe" "C:\Users\saint\.gemini\ProEditor.code-workspace"

echo.
echo ===================================================
echo   RESTORE COMPLETE. Please wait for the window.
echo ===================================================
pause
