# File: api/routers/graphs.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from api.dependencies.auth import get_current_user, get_db
from database.models.auth_models import User, ResearchSession
from database.db import SessionLocal
from sqlalchemy.orm import Session
import logging
import threading

from services.graph_persistence_service import load_graphs, save_graphs
from services.graph_editing_service import apply_graph_edit
from services.graph_service import recompute_analytics_for_saved_graph
from services.memory_service import MemoryService
from api.models.analysis_models import GraphEditRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/debug/router-check")
def router_check():
    return {"status": "ok", "router": "graphs"}


class ApprovalRequest(BaseModel):
    user_id: str
    run_id: Optional[str] = None


@router.post("/{query}/approve")
async def approve_graph(
    query: str, 
    request: ApprovalRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Research-Grade Approval Gate. Handles UUID (session_id) or Query string.
    """
    actual_query = query
    session_record = db.query(ResearchSession).filter(ResearchSession.session_id == query).first()
    if session_record:
        actual_query = session_record.query

    data = load_graphs(actual_query, current_user.id)
    if not data or not data.get("knowledge_graph"):
        raise HTTPException(status_code=404, detail=f"Graph not found for approval (ID: {query}).")
    
    kg = data["knowledge_graph"]
    run_meta = kg.get("graph", {}).get("meta", {})
    
    if request.run_id:
        stored_run = run_meta.get("run_id")
        if stored_run and stored_run != request.run_id:
            logger.warning(f"Approval Rejected: Run ID Mismatch. Request={request.run_id}, Stored={stored_run}")
            raise HTTPException(status_code=409, detail="Run ID mismatch. Please refresh.")
    
    try:
        MemoryService.update_global_stats(kg, approved=True)
    except Exception as e:
        logger.error(f"Memory Update Critical Failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Memory update failed.")
        
    from services.state_service import load_state_for_query, save_state_for_query
    try:
        current_state = load_state_for_query(query, current_user.id)
        if current_state:
            current_state["graph_approved"] = True
            if current_state.get("current_step") == "awaiting_graph_review":
                current_state["current_step"] = "awaiting_gap_analysis"
                
            save_state_for_query(query, current_state, current_user.id)
            logger.info(f"✅ Workflow State updated: graph_approved=True & advanced to Gap Analysis for session {query}")
        else:
            logger.warning(f"⚠️ Could not load workflow state for session {query} to set approval.")
    except Exception as e:
        logger.error(f"Workflow State Update Failed: {e}", exc_info=True)
        
    return {"status": "approved", "message": "Graph approved. Workflow advancing."}


@router.post("/{query}/edit")
def edit_graph(
    query: str, 
    request: GraphEditRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handles UUID (session_id) or Query string for editing."""
    actual_query = query
    session_record = db.query(ResearchSession).filter(ResearchSession.session_id == query).first()
    if session_record:
        actual_query = session_record.query
    
    user_id = current_user.id
    try:
        graphs = load_graphs(actual_query, user_id)
        if not graphs or not graphs.get("knowledge_graph"):
            raise HTTPException(status_code=404, detail="Graph not found")
        
        kg = graphs["knowledge_graph"]
        updated_kg = apply_graph_edit(kg, request.action, request.model_dump())
        
        save_graphs(
            query=actual_query, 
            user_id=user_id, 
            knowledge=updated_kg, 
            citation=graphs.get("citation_graph", {}), 
            analytics=graphs.get("research_analytics", {})
        )
        
        def _recompute():
            try:
                recompute_analytics_for_saved_graph(actual_query, user_id)
            except Exception as exc:
                logger.warning(f"Background analytics recompute failed: {exc}")
        
        threading.Thread(target=_recompute, daemon=True).start()
        
        return {"status": "success", "message": "Graph updated", "data": updated_kg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph edit error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to edit graph")


@router.get("/{query}")
def get_graphs(
    query: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handles UUID (session_id) or Query string for loading."""
    actual_query = query
    session_record = db.query(ResearchSession).filter(ResearchSession.session_id == query).first()
    if session_record:
        actual_query = session_record.query
    
    user_id = current_user.id
    try:
        graphs = load_graphs(actual_query, user_id)
    except Exception as e:
        logger.error(f"Graph load error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load graphs")

    if graphs is None:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs
