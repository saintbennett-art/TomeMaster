"""
[SOVEREIGN PORT HANDSHAKE]: Dynamic Port Assignment Engine
----------------------------------------------------------
1. Asks the OS for a free port (zero hardcoding).
2. Writes that port to `.sovereign_port` in the project root.
3. Starts uvicorn on that port.
4. On shutdown, cleans up the port signal file.

The frontend reads `?api_port=` from its launch URL (injected by
Start_TomeMaster.bat after reading `.sovereign_port`), completing the
two-way handshake with zero assumptions about port numbers.
"""

import socket
import os
import sys
import secrets
import uvicorn

# ─── Locate Project Root ──────────────────────────────────────────────────────
# run.py lives in /backend — project root is one level up
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
PORT_SIGNAL_FILE = os.path.join(PROJECT_ROOT, ".sovereign_port")
SESSION_SIGNAL_FILE = os.path.join(PROJECT_ROOT, ".sovereign_session")


def _claim_free_port() -> int:
    """
    [SOVEREIGN CLAIM]: Asks the OS for an available port.
    Binding to port 0 causes the OS to assign a free port atomically.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _write_port_signal(port: int) -> None:
    """Broadcasts the claimed port so the startup script can inject it into the browser URL."""
    with open(PORT_SIGNAL_FILE, "w") as f:
        f.write(str(port))
    print(f"[SOVEREIGN HANDSHAKE]: Port {port} broadcast to {PORT_SIGNAL_FILE}")


def _cleanup_port_signal() -> None:
    """Removes the port/session signals on clean shutdown to prevent stale reads."""
    for f in (PORT_SIGNAL_FILE, SESSION_SIGNAL_FILE):
        if os.path.exists(f):
            os.remove(f)
    print("[SOVEREIGN HANDSHAKE]: Port + session signals cleaned up.")


if __name__ == "__main__":
    # Change working directory to /backend so all relative paths in the app work
    os.chdir(BACKEND_DIR)

    port = _claim_free_port()
    _write_port_signal(port)

    # [SESSION AUTH]: Mint a per-launch token, hand it to the backend via env
    # (main.py reads it and locks /api/v1/*), and broadcast it beside the port so
    # a launcher can inject it into the UI URL as it already does with the port.
    session_token = secrets.token_urlsafe(32)
    os.environ["TOME_SESSION_TOKEN"] = session_token
    with open(SESSION_SIGNAL_FILE, "w") as f:
        f.write(session_token)

    print(f"[SOVEREIGN ENGINE]: Starting TomeMaster on http://127.0.0.1:{port}")

    try:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=port,
            reload=False,           # reload=False for stable production run
            timeout_keep_alive=300,
            log_level="warning",    # Suppress INFO noise; errors still surface
        )
    finally:
        _cleanup_port_signal()
