# api/routers/upload.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from api.dependencies.auth import get_current_user, get_db
from database.models.auth_models import User
from services.research_service import ingest_local_file
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=dict)
async def upload_paper(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)  # Dependency ensuring DB is alive
):
    """
    Uploads a local PDF file, extracts text, and stores it as a 'local_file' paper.
    Returns the canonical_id and paper_id for use in research tasks.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check simple size limit (10MB)
    # Note: We read into memory. For production with huge load, stream processing is better.
    # But for a research assistant app, this is acceptable.
    MAX_SIZE = 10 * 1024 * 1024
    
    try:
        # Check size before reading entire file into memory
        chunk_size = 8192
        content = bytearray()
        total_size = 0
        
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_SIZE:
                raise HTTPException(status_code=413, detail="File too large (limit 10MB)")
            content.extend(chunk)
        
        content = bytes(content)
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        result = await ingest_local_file(content, file.filename, current_user.id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed"))
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during upload")
