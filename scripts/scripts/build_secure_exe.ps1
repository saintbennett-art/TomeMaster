<#
.SYNOPSIS
Builds the TomeMaster CrewAI application into a secure, standalone executable.
Uses Nuitka to translate Python to C and compile to native machine code.
#>

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " TomeMaster: Secure Build Pipeline (Nuitka) " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check if uv is installed
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: 'uv' package manager not found. Make sure you install dependencies first." -ForegroundColor Yellow
}

# Install compilation dependencies
Write-Host "`n[1/4] Installing Compilation Toolchain (Nuitka)..." -ForegroundColor Yellow
python -m pip install --upgrade nuitka setuptools

# Define the source file and output directory
$MAIN_SCRIPT = "backend\desktop_app.py"
$OUTPUT_DIR = "build_output"
$FRONTEND_DIR = "frontend"
$WEB_DIST = "backend\web_dist"

Write-Host "`n[2/4] Synthesizing React Frontend..." -ForegroundColor Yellow
Set-Location $FRONTEND_DIR
npm install
npm run build
Set-Location ..

Write-Host "`n[3/4] Copying Static Assets to Web Dist..." -ForegroundColor Yellow
if (Test-Path $WEB_DIST) { Remove-Item -Recurse -Force $WEB_DIST }
Copy-Item -Path "$FRONTEND_DIR\out" -Destination $WEB_DIST -Recurse -Force

if (!(Test-Path $MAIN_SCRIPT)) {
    Write-Host "ERROR: Could not find $MAIN_SCRIPT. Are you running this from the project root?" -ForegroundColor Red
    exit 1
}

# Run Nuitka
# --standalone: Creates a self-contained folder with the exe and python DLLs.
# --onefile: Packages everything into a single .exe (slower startup, but easier to distribute).
# --include-package=crewai: Explicitly includes the dynamic CrewAI packages.
# --windows-disable-console: Hides the CMD window for a seamless GUI experience.
Write-Host "`n[4/4] Compiling Application to C and Building Native Desktop Executable..." -ForegroundColor Yellow
python -m nuitka --onefile --standalone --windows-disable-console --include-package=crewai --include-package=pydantic --include-package=presidio_analyzer --include-package=presidio_anonymizer --include-package=cryptography --include-data-dir=$WEB_DIST=web_dist --output-dir=$OUTPUT_DIR $MAIN_SCRIPT

Write-Host "`nBuild Complete!" -ForegroundColor Green
Write-Host "Your standalone, encrypted executable is located in: $OUTPUT_DIR" -ForegroundColor Green
Write-Host "Distribute this executable along with your config_wizard.py." -ForegroundColor Cyan
