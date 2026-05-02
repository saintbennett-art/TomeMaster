import os
import glob
import re
import json

def analyze_terrain():
    # Detect active project folder
    # We'll assume the one from the user's logs
    folder = r"C:/Users/saint/OneDrive/Documents/This Close/Demo/This Close"
    if not os.path.exists(folder):
        print(f"Error: Folder {folder} not found.")
        return

    print(f"Terrain Analysis for: {folder}")
    
    images = sorted(glob.glob(os.path.join(folder, "*.[jJ][pP][gG]")))
    rtfs = glob.glob(os.path.join(folder, "*.rtf"))
    # Also check _manuscript_source
    subdir = os.path.join(folder, "_manuscript_source")
    if os.path.exists(subdir):
        rtfs.extend(glob.glob(os.path.join(subdir, "*.rtf")))
        
    rtf_basenames = [os.path.basename(r).lower() for r in rtfs]
    
    print(f"Total Images: {len(images)}")
    print(f"Total RTFs: {len(rtfs)}")
    
    missing = []
    for img in images:
        img_basename = os.path.basename(img).lower()
        img_stem = os.path.splitext(img_basename)[0]
        
        # Check if any RTF matches
        match = False
        for r in rtf_basenames:
            if img_stem in r:
                match = True
                break
            
            # Numeric match
            num_match = re.search(r'(\d+)', img_stem)
            if num_match:
                p_int = int(num_match.group(1))
                if f"page_{p_int}(\\D|$)" in r or f"page_{p_int}.rtf" == r:
                    match = True
                    break
                    
        if not match:
            missing.append(img_basename)
            
    print(f"Missing (Leapfrog failed): {len(missing)}")
    if missing:
        print("\nFirst 20 missing samples:")
        for m in missing[:20]:
            print(f"- {m}")

analyze_terrain()
