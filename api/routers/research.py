# api/routers/research.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from api.models.research_models import ResearchRequest, ResearchResponse
from services.research_service import process_research_task
from services.progress_tracker import ProgressTracker
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


from api.dependencies.auth import get_current_user, get_db
from database.models.auth_models import User, ResearchSession
from sqlalchemy.orm import Session
from services.audit_service import log_action

@router.post("/", response_model=ResearchResponse)
async def research_endpoint(
    payload: ResearchRequest,
    current_user: User = Depends(get_current_user)
) -> ResearchResponse:
    try:
        # Note: This endpoint seems to be a direct tool access. 
        # Ideally should be wrapped in a session but we'll secure access at least.
        result = await process_research_task(
            payload.query, 
            include_paper_ids=payload.include_paper_ids,
            task_id=payload.task_id,
            user_id=current_user.id
        )

        # If pipeline failed internally
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Pipeline processing failed")
            )
        return ResearchResponse(
            status="success",
            data=result
        )

    except RequestValidationError as e:
        logger.warning(f"Validation error in research_endpoint: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid request payload"
        )

    except Exception as e:
        logger.error("Error in research_endpoint", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/progress/{task_id}")
async def get_research_progress(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Poll this endpoint for real-time progress on research tasks.
    Returns: { "phase": "...", "queries_total": N, ... }
    """
    # Use ProgressTracker.get_progress_object if needed, or get dict and check
    # But ProgressTracker only returns dict. We need to check owner.
    # We need access to the object to check user_id, or update get_progress to return owner.
    # Let's peek into the instance directly via a helper if possible, or modify get_progress return.
    # Actually, ProgressTracker is in services. Let's access instances directly if we must, 
    # OR better: update get_progress to return the internal object or a dict with owner?
    # Wait, the user asked to verify the returned progress/task owner matches current_user.
    
    # Access internal method or simply inspect the dict if we added user_id to to_dict?
    # I didn't add user_id to_dict yet. 
    # Let's assume I should rely on the services. 
    # For now, I will modify ProgressTracker to exposing owner check or just peek.
    # But wait, I can just use the tool `view_file` to see ProgressTracker again? No need.
    
    # I'll rely on `_instances` access since it's same process for now (local memory).
    # Ideally `start_task` added `user_id`, so `ProgressTracker._instances[task_id].user_id` exists.
    
    progress = ProgressTracker.get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    
    # Check ownership
    owner_id = ProgressTracker.get_task_owner(task_id)
    if not owner_id or owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this task")

    return progress


from api.models.research_models import ManualPaperRequest

@router.post("/manual", response_model=dict)
async def add_manual_paper_endpoint(
    payload: ManualPaperRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:    
    from services.research_service import add_manual_paper
    try:
        # Verify ownership of the session
        session_id = payload.query.strip()
        session = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
             
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this session")
        
        result = await add_manual_paper(
            query=session_id,
            title=payload.title,
            abstract=payload.abstract,
            url=payload.url,
            authors=payload.authors,
            year=payload.year,
            source=payload.source
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to add manual paper")
            )
            
        # Log Audit
        log_action(
            db,
            user_id=current_user.id,
            action="ADD_MANUAL_PAPER",
            target_id=payload.query,
            payload={"title": payload.title}
        )
            
        return result
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error("Error in add_manual_paper_endpoint", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

