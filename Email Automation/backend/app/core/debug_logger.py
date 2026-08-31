"""Helper module for debug logging - Production mode: all logging disabled"""
from typing import Dict, Any, Optional

def write_debug_log(location: str, message: str, data: Optional[Dict[str, Any]] = None, hypothesis_id: Optional[str] = None):
    """Write a debug log entry - No-op in production"""
    # Debug logging disabled for production
    pass

