import logging
import sys
from pythonjsonlogger import jsonlogger
import json
import os
from datetime import datetime

def setup_siem_logger(name: str = "tomemaster") -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Avoid attaching multiple handlers if already setup
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        logHandler = logging.StreamHandler(sys.stdout)
        
        # Strict Gov't Schema JSON format
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={"levelname": "level", "asctime": "timestamp"}
        )
        
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)
        logger.propagate = False
        
    return logger

siem_logger = setup_siem_logger()

def log_api_usage(event: str, provider: str, model: str, metrics: dict, folder_path: str = None, duration: float = 0.0):
    """[SOVEREIGN ACCOUNTING]: Tracks token consumption for billing and limits."""
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "provider": provider,
            "model": model,
            "metrics": metrics,
            "folder_path": folder_path,
            "duration": duration
        }
        with open("api_usage_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        siem_logger.error(f"Failed to write API ledger: {e}")
