# api/routers/graph_approval.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from services.memory_service import MemoryService
from services.graph_persistence_service import load_graphs
from database.db import SessionLocal
from sqlalchemy.orm import Session
from api.dependencies.auth import get_current_user, get_db
from database.models.auth_models import ResearchSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ApprovalRequest(BaseModel):
    user_id: str
    run_id: Optional[str] = None # To verify we are approving the correct version? 
    # For now, just query/user_id is unique enough if we approve LATEST.

@router.post("/graphs/{query}/approve")
async def approve_graph(
    query: str, 
    request: ApprovalRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Research-Grade Approval Gate.
    Triggers:
    1. Global Memory Update (Longitudinal Tracking).
    2. Locking of the run (optional).
    """
    # Resolve Session ID to Actual Query if possible
    # 'query' param here is likely the session_id/task_id from frontend
    actual_query = query
    session_record = db.query(ResearchSession).filter(ResearchSession.session_id == query).first()
    if session_record:
        actual_query = session_record.query # The natural language query
    
    # 1. Load the Graph
    # We load the stored graph using the ACTUAL query string
    data = load_graphs(actual_query, current_user.id)
    if not data or not data.get("knowledge_graph"):
        raise HTTPException(status_code=404, detail=f"Graph not found for approval (ID: {query}).")
    
    kg = data["knowledge_graph"]
    run_meta = kg.get("graph", {}).get("meta", {})
    
    # Verify Run ID matches if provided
    # Prevents approving stale or different runs
    if request.run_id:
        stored_run = run_meta.get("run_id")
        if stored_run and stored_run != request.run_id:
            logger.warning(f"Approval Rejected: Run ID Mismatch. Request={request.run_id}, Stored={stored_run}")
            raise HTTPException(status_code=409, detail="Run ID mismatch. Please refresh.")
    
    # 2. Update Global Memory (THE GATE)
    try:
        MemoryService.update_global_stats(kg, approved=True)
    except Exception as e:
        logger.error(f"Memory Update Critical Failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Memory update failed.")
        
    # 3. Update Workflow State to Unblock Process
    # We must load the state using the SESSION ID (which is the key for workflow state)
    # The 'query' param here is confirmed to be the session_id/task_id
    from services.state_service import load_state_for_query, save_state_for_query
    
    try:
        current_state = load_state_for_query(query, current_user.id)
        if current_state:
            # Set the approval flag
            current_state["graph_approved"] = True
            
            # FORCE TRANSITION: 
            # run_until_interaction in workflow.py stops immediately if it sees 'awaiting_graph_review'.
            # We must manually push it past this state so the loop can pick it up.
            if current_state.get("current_step") == "awaiting_graph_review":
                current_state["current_step"] = "awaiting_gap_analysis"
                
            save_state_for_query(query, current_state, current_user.id)
            logger.info(f"✅ Workflow State updated: graph_approved=True & advanced to Gap Analysis for session {query}")
        else:
            logger.warning(f"⚠️ Could not load workflow state for session {query} to set approval.")
    except Exception as e:
        logger.error(f"Workflow State Update Failed: {e}", exc_info=True)
        # We don't fail the request because Global Memory is already updated, which is the key action.
        # But user might be stuck.
        
    return {"status": "approved", "message": "Graph approved. Workflow advancing."}
