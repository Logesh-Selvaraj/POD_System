import os
import uuid
from app.core.config import settings

def save_uploaded_file(file_bytes: bytes, filename_prefix: str, extension: str = ".jpg") -> str:
    """
    Save raw binary bytes to local storage folder and return file URL path.
    """
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    file_id = f"{filename_prefix}_{uuid.uuid4().hex[:8]}{extension}"
    file_path = os.path.join(settings.LOCAL_STORAGE_DIR, file_id)
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    return f"/static/uploads/{file_id}"
