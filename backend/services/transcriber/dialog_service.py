"""
[DIALOG SERVICE]: Native OS file/folder picker dialogs.

Isolated from backend AI logic. Falls back gracefully
when running in headless mode (FastAPI without desktop shell).
"""
import os

try:
    import webview
except ImportError:
    webview = None


# Global window foundation for native dialogs
UI_WINDOW = None


def pick_file(title="Select Manuscript File", extensions=None) -> str:
    """Summons the native Windows file picker with corrected extension handling."""
    global UI_WINDOW

    if not extensions:
        extensions = [
            ("Manuscript Files", "*.pdf;*.docx;*.txt;*.rtf;*.md;*.markdown"),
            ("All Files", "*.*"),
        ]

    if UI_WINDOW and webview:
        try:
            wv_types = [f"{desc} ({patt})" for desc, patt in extensions]
            result = UI_WINDOW.create_file_dialog(
                webview.OPEN_DIALOG, directory="", allow_multiple=False, file_types=wv_types
            )
            if result and len(result) > 0:
                return os.path.abspath(result[0]).replace("\\", "/")
            return None
        except Exception as e:
            print(f"Native Viewport File Picker Failure: {e}")

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        tk_types = [(desc, patt.replace(";", " ")) for desc, patt in extensions]
        file_path = filedialog.askopenfilename(title=title, filetypes=tk_types)
        root.destroy()
        if file_path and os.path.exists(file_path):
            return os.path.abspath(file_path).replace("\\", "/")
        return None
    except Exception as e:
        print(f"Native File Picker Failure: {e}")
        return None


def pick_directory() -> str:
    """Summons the native Windows folder picker via the Boardroom Viewport or Tkinter."""
    global UI_WINDOW

    if UI_WINDOW and webview:
        try:
            result = UI_WINDOW.create_file_dialog(
                webview.FOLDER_DIALOG, directory="", save_filename=""
            )
            if result and len(result) > 0:
                folder = result[0]
                if folder and os.path.exists(folder):
                    return os.path.abspath(folder).replace("\\", "/")
            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"BOARDROOM CRITICAL: {str(e)}")
            print(f"Native Viewport Picker Failure: {e}")

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select TomeMaster Project Folder")
        root.destroy()
        if folder and os.path.exists(folder):
            return os.path.abspath(folder).replace("\\", "/")
        return None
    except Exception as e:
        print(f"BOARDROOM CRITICAL: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"Native Picker Failure: {e}")
        return None
