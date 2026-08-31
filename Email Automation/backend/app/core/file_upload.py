import os
import uuid
import json
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta
import logging
import tempfile

logger = logging.getLogger(__name__)

# Get the backend directory (where this file is located)
# Goes up from app/core/file_upload.py to backend/
BACKEND_DIR = Path(__file__).parent.parent.parent

# Try to use backend directory first, fallback to system temp if that fails
try:
    # Use backend/temp_attachments directory
    UPLOAD_DIR = BACKEND_DIR / "temp_attachments"
    UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Test write permissions
    test_file = UPLOAD_DIR / ".write_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
        logger.info(f"Using upload directory: {UPLOAD_DIR}")
    except (OSError, PermissionError) as e:
        logger.warning(f"Cannot write to {UPLOAD_DIR}, falling back to system temp: {e}")
        # Fallback to system temp directory
        UPLOAD_DIR = Path(tempfile.gettempdir()) / "wolfassistants_attachments"
        UPLOAD_DIR.mkdir(exist_ok=True)
        logger.info(f"Using fallback upload directory: {UPLOAD_DIR}")
except Exception as e:
    logger.warning(f"Error creating upload directory in backend, using system temp: {e}")
    # Fallback to system temp directory
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "wolfassistants_attachments"
    UPLOAD_DIR.mkdir(exist_ok=True)
    logger.info(f"Using system temp upload directory: {UPLOAD_DIR}")

# Maximum file size: 10MB per file, 25MB total
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25MB

# Allowed file types
ALLOWED_EXTENSIONS = {
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf',
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg',
    # Archives
    '.zip', '.rar', '.7z',
    # Other
    '.csv', '.json', '.xml'
}

def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return Path(filename).suffix.lower()

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS

def get_content_type(filename: str) -> str:
    """Get MIME type for file."""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or 'application/octet-stream'

async def save_uploaded_file(file: UploadFile) -> Dict[str, any]:
    """
    Save uploaded file to temporary storage.
    Returns metadata dict with filename, path, content_type, size.
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_ext = get_file_extension(file.filename)
    stored_filename = f"{file_id}{original_ext}"
    file_path = UPLOAD_DIR / stored_filename
    
    # Save file
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Return metadata
    return {
        "id": file_id,
        "filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "content_type": get_content_type(file.filename),
        "size": file_size
    }

def validate_total_size(attachments: List[Dict]) -> None:
    """Validate total size of all attachments."""
    total_size = sum(att.get('size', 0) for att in attachments)
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Total attachment size exceeds {MAX_TOTAL_SIZE / (1024*1024):.1f}MB"
        )

def get_file_content(file_path: str) -> bytes:
    """Read file content from temporary storage."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(path, 'rb') as f:
        return f.read()

def delete_file(file_path: str) -> None:
    """Delete file from temporary storage."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
    except Exception as e:
        logger.warning(f"Error deleting file {file_path}: {e}")

def cleanup_old_files(max_age_hours: int = 720) -> None:  # 30 days = 720 hours
    """Clean up files older than max_age_hours."""
    if not UPLOAD_DIR.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    deleted_count = 0
    
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error cleaning up file {file_path}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old attachment files")

