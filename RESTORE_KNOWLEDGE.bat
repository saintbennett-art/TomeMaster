@echo off
echo ========================================================
echo TOME-MASTER: KNOWLEDGE BASE RESURRECTION PROTOCOL
echo ========================================================
echo.
echo WARNING: This will overwrite the current Antigravity knowledge base 
echo with the backed-up rules from this project repository.
echo.
pause

echo Restoring Secure Coding Directive, Master Directive, and ZAP protocols...
xcopy /E /Y /I "%~dp0knowledge_backup" "C:\Users\saint\.gemini\antigravity\knowledge"

echo.
echo Resurrection Complete.
echo Next Step: Tell Antigravity to "Read your knowledge base."
echo.
pause
