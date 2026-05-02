@echo off
echo =======================================
echo PRoeditor `.exe` Standalone Compiler
echo =======================================

echo.
echo [0/4] Security Audit: Purging secrets and local environment files...
if exist backend\.env del /f /q backend\.env
if exist frontend\.env del /f /q frontend\.env
if exist frontend\.env.local del /f /q frontend\.env.local
if exist backend\api_usage_log.jsonl del /f /q backend\api_usage_log.jsonl
echo [OK] All developer-side secrets and historical logs have been stripped.
echo.
echo [1/4] Building Next.js Frontend into Static HTML...
cd frontend
call npm install
call npm run build

echo.
echo [2/4] Merging Frontend into Python Backend...
cd ..\backend
if exist static rmdir /s /q static
xcopy /s /e /y ..\frontend\out\* static\

echo.
echo [3/4] Installing Required Python Dependencies...
call .\venv\Scripts\activate.bat
pip install pywebview pyinstaller
pip install -r requirements.txt
pip install beautifulsoup4 reportlab python-docx google-generativeai fastapi uvicorn pydantic python-multipart ebooklib pillow

echo.
echo [4/4] Executing PyInstaller to compile PRoeditor.exe...
pyinstaller --onefile --noconsole --name PRoeditor --add-data "static;static" desktop_app.py

echo.
echo =======================================
echo SUCCESS! Your executable is ready!
echo Moving PRoeditor.exe to the main folder...
move dist\PRoeditor.exe ..\PRoeditor.exe
echo =======================================
pause
