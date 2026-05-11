import io
import base64
import os
import shutil
import fitz # PyMuPDF
from PIL import Image
from typing import List, Tuple

def process_asset(f_path: str, folder_path: str) -> List[Tuple[Image.Image, str]]:
    """
    [VISION PROCESSOR]: Converts a manuscript asset (PDF or Image) into 
    processable high-fidelity image buffers.
    """
    images_to_process = []
    
    if f_path.lower().endswith(".pdf"):
        try:
            pdf_doc = fitz.open(f_path)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images_to_process.append((img, f"{f_path}_p{page_num+1}"))
            pdf_doc.close()
        except Exception as e:
            print(f"VISION ERROR: Failed to unpack PDF {f_path}: {e}")
    else:
        try:
            with Image.open(f_path) as img_check:
                img_check.verify()
            with Image.open(f_path) as img:
                img.load() 
                images_to_process.append((img.copy(), f_path))
        except Exception as e:
            print(f"VISION ERROR: Asset Corruption Detected: {os.path.basename(f_path)}. Isolating...")
            failed_dir = os.path.join(folder_path, "Failed_Assets")
            os.makedirs(failed_dir, exist_ok=True)
            try:
                shutil.move(f_path, os.path.join(failed_dir, os.path.basename(f_path)))
            except: pass
            
    return images_to_process

def generate_telemetry(img: Image.Image) -> str:
    """Generates a base64 encoded thumbnail for frontend streaming."""
    buffered = io.BytesIO()
    with img.copy() as thumb:
        thumb.thumbnail((512, 512)) 
        thumb.save(buffered, format="JPEG", quality=60)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')
