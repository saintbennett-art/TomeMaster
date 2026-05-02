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

PORT = 8080 # Default Anchor

def start_server():
    global PORT
    import main
    import uvicorn
    # [APEX HANDSHAKE]: Attempt to bind to the preferred port, fallback if blocked
    success = False
    for i in range(5):
        try:
            print(f"BOARDROOM: Attempting to anchor Engine on 127.0.0.1:{PORT} (Attempt {i+1})...")
            # Log setup
            config = uvicorn.Config(main.app, host="127.0.0.1", port=PORT, log_level="info")
            server = uvicorn.Server(config)
            success = True
            server.run()
            break
        except Exception as e:
            print(f"BOARDROOM: Port {PORT} occupied or blocked: {e}")
            PORT = get_free_port()
            print(f"BOARDROOM: Diverting Handshake to Port {PORT}...")
            time.sleep(0.5)
    
    if not success:
        print("BOARDROOM FATAL: All handshake attempts failed. Engine remains offline.")
        os._exit(1)

if __name__ == '__main__':
    # Boot the FastAPI architecture silently in the background
    # [SOVEREIGN PRIORITY]: Ensure the server thread is launched with high responsiveness
    t = threading.Thread(target=start_server, name="TomeMaster-Engine", daemon=True)
    t.start()
    
    # Wait for server to initialize
    time.sleep(3)
    
    # Launch the Chromium-based Director's Viewport with the discovered API port
    target_url = f'http://127.0.0.1:3000?api_port={PORT}'
    window = webview.create_window('Tome-Master Boardroom', target_url, width=1400, height=900)
    
    # [SOVEREIGN BRIDGE]: Link the window to the services for native dialog support
    import services.transcriber_service as ts
    ts.UI_WINDOW = window
    
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
