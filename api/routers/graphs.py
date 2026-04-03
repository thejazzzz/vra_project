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
from services.graph_service import recompute_analytics_for_saved_graph, find_citation_path
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
    logger.info(f"🔍 Approval Request for ID: {query} (user: {current_user.id})")
    
    # ⚠️ Use session_id (the UUID in the path) directly for loading
    data = load_graphs(query, current_user.id)
    
    if not data or not data.get("knowledge_graph"):
        # Fallback to translation only if direct UUID lookup fails (legacy or edge case)
        session_record = db.query(ResearchSession).filter(ResearchSession.session_id == query).first()
        if session_record:
            actual_query = session_record.query.strip().lower()
            logger.info(f"♻️ Direct UUID lookup failed. Falling back to translated query: '{actual_query}'")
            data = load_graphs(actual_query, current_user.id)

    if not data or not data.get("knowledge_graph"):
        logger.error(f"❌ Graph data not found in DB for session/query: '{query}' (user: {current_user.id})")
        raise HTTPException(status_code=404, detail=f"Graph not found for approval (ID: {query}).")
    
    kg = data["knowledge_graph"]
    actual_query = data.get("query", query) # Use query from DB if found
    logger.info(f"📊 Graph data retrieved for '{actual_query}'. Nodes: {len(kg.get('nodes', []))}, Edges: {len(kg.get('links', []))}")
    
    run_meta = kg.get("graph", {}).get("meta", {})
    
    if request.run_id:
        stored_run = run_meta.get("run_id")
        if stored_run and stored_run != request.run_id:
            logger.warning(f"Approval Rejected: Run ID Mismatch. Request={request.run_id}, Stored={stored_run}")
            raise HTTPException(status_code=409, detail="Run ID mismatch. Please refresh.")
    
    try:
        MemoryService.update_global_stats(kg, approved=True)
        logger.info(f"🧠 Memory Stats updated for graph approval.")
    except Exception as e:
        logger.error(f"Memory Update Critical Failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Memory update failed.")
        
    from services.state_service import load_state_for_query, save_state_for_query
    try:
        # NOTE: load_state_for_query uses session_id (the UUID) as the key in the workflow_states table
        current_state = load_state_for_query(query, current_user.id)
        if current_state:
            current_state["graph_approved"] = True
            if current_state.get("current_step") == "awaiting_graph_review":
                current_step = "awaiting_gap_analysis"
                current_state["current_step"] = current_step
                
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
    user_id = current_user.id
    try:
        graphs = load_graphs(query, user_id)
        if not graphs or not graphs.get("knowledge_graph"):
            raise HTTPException(status_code=404, detail="Graph not found")
        
        kg = graphs["knowledge_graph"]
        actual_query = graphs.get("query", query)
        
        updated_kg = apply_graph_edit(kg, request.action, request.model_dump())
        
        save_graphs(
            query=actual_query, 
            user_id=user_id, 
            knowledge=updated_kg, 
            citation=graphs.get("citation_graph", {}), 
            analytics=graphs.get("research_analytics", {}),
            session_id=query if query != actual_query else graphs.get("session_id")
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


@router.get("/{query}/citation-path")
def get_citation_path(
    query: str,
    source: str,
    target: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find the shortest path between two paper IDs in the citation graph."""
    user_id = current_user.id
    try:
        graphs = load_graphs(query, user_id)
        if not graphs or not graphs.get("citation_graph"):
            raise HTTPException(status_code=404, detail="Citation graph not found")
        
        path = find_citation_path(graphs["citation_graph"], source, target)
        return {"status": "success", "path": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find citation path for session {query}: {e}")
        raise HTTPException(status_code=500, detail="Error computing citation path")


@router.get("/{query}")
def get_graphs(
    query: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handles UUID (session_id) or Query string for loading."""
    user_id = current_user.id
    try:
        graphs = load_graphs(query, user_id)
    except Exception as e:
        logger.error(f"Graph load error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load graphs")

    if graphs is None:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs
