import os
from fastapi import HTTPException

def validate_project_path(folder_path: str) -> str:
    """
    [SOVEREIGN GUARDRAIL]: Resolves and validates that a path stays within 
    the user's home directory tree. Required for Government/Educational security compliance.
    """
    if not folder_path:
        raise HTTPException(status_code=400, detail="Folder path is required.")
        
    try:
        # Resolve to absolute path
        resolved = os.path.realpath(os.path.abspath(folder_path))
        
        # Determine the user's home root
        home = os.path.realpath(os.path.expanduser("~"))
        
        # SECURITY GATE: Path must be sub-directory of Home
        if not resolved.startswith(home + os.sep) and resolved != home:
            print(f"SECURITY ALERT: Unauthorized path access attempted: {resolved}")
            raise HTTPException(status_code=403, detail="Path outside permitted directory.")
            
        return resolved
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Path Validation Failure: {str(e)}")
