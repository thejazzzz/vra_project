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
    state = InteractiveReportingService.get_report_state(payload.session_id, current_user.id)
    if not state:
        raise HTTPException(status_code=404, detail="Report state not found")

    if state["report_status"] != "completed":
        raise HTTPException(status_code=400, detail="Report must be finalized before export")

    if payload.format.lower() not in {"pdf", "docx", "markdown"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {payload.format}")

    # TODO: Stream response
    # For now, just a stub
    try:
        # We might call ExportService here actually generating it
        # content = ExportService.export_report(..., payload.format)
        return {"message": f"Export to {payload.format} triggered (Stub)", "status": "success"}
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Export failed")
