# api/routers/graph_approval.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from services.memory_service import MemoryService
from services.graph_persistence_service import load_graphs
from database.db import SessionLocal
from api.dependencies.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ApprovalRequest(BaseModel):
    user_id: str
    run_id: str # To verify we are approving the correct version? 
    # For now, just query/user_id is unique enough if we approve LATEST.

@router.post("/graphs/{query}/approve")
async def approve_graph(
    query: str, 
    request: ApprovalRequest,
    current_user = Depends(get_current_user)
):
    """
    Research-Grade Approval Gate.
    Triggers:
    1. Global Memory Update (Longitudinal Tracking).
    2. Locking of the run (optional).
    """
    # 1. Load the Graph
    # We load the stored graph.
    # Use authenticated user ID, verify permission (Ownership check could go here)
    data = load_graphs(query, current_user.id)
    if not data or not data.get("knowledge_graph"):
        raise HTTPException(status_code=404, detail="Graph not found for approval.")
    
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
        
    return {"status": "approved", "message": "Graph approved. Insights integrated into Global Memory."}
