import os
import subprocess
import shutil
import sys

# ─── SOVEREIGN BUILD CONFIGURATION ───────────────────────────────────────────
PROJ_NAME = "BoardroomIntelligence"
FRONTEND_DIR = "../frontend"
BACKEND_DIR = "."
DIST_DIR = "./dist"
BUILD_DIR = "./build"

def run_step(name, command, cwd="."):
    print(f"\n[BUILD-PROCESS]: {name}...")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {name} aborted with error: {e}")
        sys.exit(1)

def build_native():
    """
    Automates the high-fidelity synthesis of the Boardroom into a 
    chromeless, standalone Windows executable.
    """
    
    # Step 1: Frontend Production Synthesis
    print("Step 1: Building Frontend static assets...")
    # run_step("NPM Install", "npm install", cwd=FRONTEND_DIR)
    run_step("Next.js Export", "npm run build", cwd=FRONTEND_DIR)
    
    # Step 2: Asset Consolidation
    # We move the static 'out' folder into the backend directory for bundling
    out_dir = os.path.join(FRONTEND_DIR, "out")
    target_web_dir = os.path.join(BACKEND_DIR, "web_dist")
    
    if os.path.exists(target_web_dir):
        shutil.rmtree(target_web_dir)
    
    print(f"Step 2: Syncing web assets to {target_web_dir}...")
    shutil.copytree(out_dir, target_web_dir)

    # Step 3: PyInstaller Handshake
    # --onefile: Bundle into a single executable
    # --noconsole: Hide the standard CMD window (Native look)
    # --add-data: Include the web_dist (frontend) and other assets
    # --hidden-import: Ensure uvicorn and routers are included
    
    pyinstaller_cmd = (
        f"pyinstaller --onefile --noconsole "
        f"--name {PROJ_NAME} "
        f"--add-data \"web_dist;web_dist\" "
        f"--add-data \"tome_master.lic;.\" "
        f"--hidden-import uvicorn.logging "
        f"--hidden-import uvicorn.loops "
        f"--hidden-import uvicorn.loops.auto "
        f"--hidden-import uvicorn.protocols "
        f"--hidden-import uvicorn.protocols.http "
        f"--hidden-import uvicorn.protocols.http.auto "
        f"--hidden-import uvicorn.protocols.websockets "
        f"--hidden-import uvicorn.protocols.websockets.auto "
        f"--hidden-import fastapi "
        f"--hidden-import python-multipart "
        f"desktop_app.py"
    )
    
    print("Step 3: Initiating PyInstaller high-fidelity bundling...")
    run_step("PyInstaller Compilation", pyinstaller_cmd)

    # Step 4: Cleanup
    print("\n[BUILD COMPLETE]: Standalone binary detected in ./dist.")
    print("You can mission-dispatch BoardroomIntelligence.exe to the user's desktop.")

if __name__ == "__main__":
    build_native()
