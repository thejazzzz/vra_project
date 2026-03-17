# File: api/routers/reporting.py
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from api.dependencies.auth import get_current_user
from database.models.auth_models import User, UserRole
from services.reporting.reporting_service import InteractiveReportingService
from services.reporting.export_service import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)

class InitReportRequest(BaseModel):
    session_id: str
    confirm: bool = False

class ReviewRequest(BaseModel):
    session_id: str
    accepted: bool
    feedback: Optional[str] = None

class FinalizeRequest(BaseModel):
    session_id: str
    confirm: bool = False

class ExportRequest(BaseModel):
    session_id: str
    format: str # pdf, docx, markdown

@router.post("/init")
async def initialize_report(
    payload: InitReportRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        state = InteractiveReportingService.initialize_report(
            session_id=payload.session_id,
            user_id=current_user.id,
            confirm=payload.confirm
        )
        return {"report_state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Init report failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")

class ResetSectionRequest(BaseModel):
    session_id: str
    force: bool = False

@router.post("/section/{section_id}/reset")
async def reset_section(
    section_id: str,
    payload: ResetSectionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    # Auth Check: Only Admins can force reset
    # Auth Check: Only Admins can force reset
    if payload.force:
        # Role-based permission check
        # Explicitly check for 'role' attribute existence (though model guarantees it)
        if not hasattr(current_user, "role") or current_user.role != UserRole.ADMIN:
             logger.warning(f"Unauthorized force reset attempt by user {current_user.id}")
             raise HTTPException(
                 status_code=403, 
                 detail="Insufficient permissions. Force reset requires admin privileges."
             )

    try:
        section_state = InteractiveReportingService.reset_section(
            session_id=payload.session_id,
            user_id=current_user.id,
            section_id=section_id,
            force=payload.force
        )
        return {"section": section_state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Reset section failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/state/{session_id}")
async def get_report_state(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        state = InteractiveReportingService.get_report_state(session_id, current_user.id)
        if not state:
            raise HTTPException(status_code=404, detail="Report state not found")
        return {"report_state": state}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get report state failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/section/{section_id}/generate")
def generate_section(
    section_id: str,
    payload: Dict[str, str] = Body(...), # Expects {"session_id": "..."}
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    try:
        section_state = InteractiveReportingService.generate_section(
            session_id=session_id,
            user_id=current_user.id,
            section_id=section_id
        )
        return {"section": section_state}
    except ValueError as e:
        msg = str(e)
        if "locked" in msg.lower() or "generating" in msg.lower():
             # Return HTTP 423 Locked for concurrency constraints
             raise HTTPException(
                 status_code=423, # Locked
                 detail={
                     "message": msg,
                     "retry_after": 30
                 }
             )
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        logger.error(f"Generate section failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal generation error")

@router.post("/generate_batch")
async def generate_batch_report(
    payload: Dict[str, str] = Body(...),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Phase 11 triggers. Kicks off the parallel Celery worker to orchestrate the entire
    report generation process in completely backgrounded fashion.
    """
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
        
    from services.state_service import load_state_for_query
    state = load_state_for_query(session_id, current_user.id)
    if not state:
        raise HTTPException(status_code=403, detail="Forbidden or session not found")
        
    try:
        from worker import generate_report_task
        task = generate_report_task.delay(session_id, current_user.id)
        
        from services.infrastructure.redis_pool import get_redis_client
        redis_client = get_redis_client()
        if not redis_client:
            logger.error("Redis connection unavailable; cannot enqueue batch job.")
            raise HTTPException(status_code=503, detail="Service unavailable: Database connection failed.")
            
        try:
            redis_client.setex(f"job_owner:{task.id}", 86400, str(current_user.id))
        except Exception as e:
            logger.error(f"Failed to record job owner in Redis: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize job state.")

        return {"status": "processing", "job_id": task.id, "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue batch report task: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue report generation.")

@router.get("/batch_status/{job_id}")
async def get_batch_status(job_id: str, current_user: User = Depends(get_current_user)):
    """Check the status of a background report generation job."""
    from services.infrastructure.redis_pool import get_redis_client
    redis_client = get_redis_client()
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection failed")
        
    owner = redis_client.get(f"job_owner:{job_id}")
    
    owner_id = None
    if isinstance(owner, bytes):
        owner_id = owner.decode("utf-8")
    elif isinstance(owner, str):
        owner_id = owner
    elif owner is not None:
        owner_id = str(owner)
    
    if not owner_id or owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized or job not found")
        
    from worker import celery_app
    import kombu.exceptions
    import celery.exceptions
    
    try:
        task = celery_app.AsyncResult(job_id)
        celery_status = task.status
        
        # Map Celery internal states to frontend-friendly structured states
        normalized_status = "processing"
        error_msg = None
        
        if celery_status == 'SUCCESS':
            normalized_status = 'success'
        elif celery_status == 'FAILURE':
            error_msg = str(task.info).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                normalized_status = "timeout"
            elif "429" in error_msg or "rate limit" in error_msg:
                normalized_status = "rate_limited"
            else:
                normalized_status = "failed"
        elif celery_status in ('REVOKED', 'REJECTED'):
            normalized_status = "failed"
            error_msg = "Task was cancelled or rejected by the system."
            
        response = {
            "job_id": job_id,
            "status": normalized_status,
        }
        
        if normalized_status == 'success':
            response["result"] = task.result
        elif normalized_status in ('failed', 'timeout', 'rate_limited'):
            response["error"] = error_msg or str(task.info)
            
        return response
    except (kombu.exceptions.OperationalError, kombu.exceptions.ConnectionError, celery.exceptions.CeleryError, Exception) as e:
        logger.error(f"Failed to retrieve task status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Task state unavailable")

@router.post("/section/{section_id}/review")
async def review_section(
    section_id: str,
    payload: ReviewRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        section_state = InteractiveReportingService.submit_review(
            session_id=payload.session_id,
            user_id=current_user.id,
            section_id=section_id,
            accepted=payload.accepted,
            feedback=payload.feedback
        )
        return {"section": section_state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Review failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Review processing failed")

@router.post("/finalize")
async def finalize_report(
    payload: FinalizeRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        report_state = InteractiveReportingService.finalize_report(
            session_id=payload.session_id,
            user_id=current_user.id,
            confirm=payload.confirm
        )
        return {"report_state": report_state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Finalize report failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/export")
async def export_report(
    payload: ExportRequest,
    current_user: User = Depends(get_current_user)
):
    from services.state_service import load_state_for_query
    
    # Load FULL state (including query, report_state, etc.)
    state = load_state_for_query(payload.session_id, current_user.id)
    if not state or not state.get("report_state"):
        raise HTTPException(status_code=404, detail="Report state not found")

    if state["report_state"]["report_status"] != "completed":
        raise HTTPException(status_code=400, detail="Report must be finalized before export")

    if payload.format.lower() not in {"pdf", "docx", "markdown"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {payload.format}")

    # Real Export Implementation
    from fastapi.responses import StreamingResponse
    import io

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "markdown": "text/markdown",
        "latex": "application/x-latex"
    }

    try:
        content_bytes = ExportService.export_report(state, payload.format)
        media_type = media_types.get(payload.format.lower(), "application/octet-stream")
        
        # Stream the binary content to optimize memory usage for large reports
        file_stream = io.BytesIO(content_bytes)
        return StreamingResponse(file_stream, media_type=media_type)
        
    except Exception as e:
        logger.error(f"Export generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export generation failed: {str(e)}")
