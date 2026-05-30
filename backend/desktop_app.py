import webview
import threading
import sys
import os
import uvicorn
import time
import socket

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

# [ZERO HARDCODING]: The OS dictates the port at runtime.
PORT = get_free_port()

_server_ready = threading.Event()

def start_server():
    global PORT
    import main
    for i in range(5):
        try:
            print(f"BOARDROOM: Attempting to establish Engine on 127.0.0.1:{PORT} (Attempt {i+1})...")
            config = uvicorn.Config(main.app, host="127.0.0.1", port=PORT, log_level="info")
            server = uvicorn.Server(config)
            _server_ready.set()
            server.run()
            break
        except Exception as e:
            print(f"BOARDROOM: Port {PORT} occupied or blocked: {e}")
            PORT = get_free_port()
            print(f"BOARDROOM: Diverting Handshake to Port {PORT}...")
            time.sleep(0.5)
    else:
        print("BOARDROOM FATAL: All handshake attempts failed. Engine remains offline.")
        os._exit(1)

def _wait_for_server(timeout: int = 15) -> bool:
    """Polls the health endpoint until the server responds or timeout is reached."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/ai/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False

if __name__ == '__main__':
    t = threading.Thread(target=start_server, name="TomeMaster-Engine", daemon=True)
    t.start()

    # Wait for the server to signal it is about to start, then health-check it
    _server_ready.wait(timeout=10)
    if not _wait_for_server(timeout=15):
        print("BOARDROOM WARNING: Server did not respond within 15s. Launching viewport anyway.")

    # [UNIFIED ORIGIN]: Target the backend directly. The static frontend will be served from here.
    target_url = f'http://127.0.0.1:{PORT}'
    window = webview.create_window('Tome-Master Boardroom', target_url, width=1400, height=900)
    
    # [SOVEREIGN BRIDGE]: Link the window to the services for native dialog support
    import services.transcriber_service as ts
    ts._set_ui_window(window)
    
    def on_closing():
        """[SAFETY GUARD]: Prevents accidental shutdowns on touch devices."""
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        result = messagebox.askyesno("TomeMaster Boardroom", "Do you wish to terminate the Directorial Engine and close the Boardroom?")
        root.destroy()
        return result

    window.events.closing += on_closing
    
    webview.start()
    
    # [SOVEREIGN TERMINATION]: Forcibly kill the background engine thread on window close
    print("BOARDROOM: Director's Viewport closed. Terminating engine...")
    os._exit(0)
