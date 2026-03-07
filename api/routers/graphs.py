# File: api/routers/graphs.py
from fastapi import APIRouter, HTTPException, Depends, Header
from services.graph_persistence_service import load_graphs
from typing import Optional
from api.dependencies.auth import get_current_user
from database.models.auth_models import User


import logging

router = APIRouter()
logger = logging.getLogger(__name__)





@router.get("/graphs/{query}")
def get_graphs(query: str, current_user: User = Depends(get_current_user)):

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query")
    
    user_id = current_user.id

    try:
        graphs = load_graphs(query, user_id)
    except Exception as e:
        logger.error(f"Graph load error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load graphs")

    if graphs is None:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs

from api.models.analysis_models import GraphEditRequest
from services.graph_editing_service import apply_graph_edit
from services.graph_persistence_service import save_graphs

@router.post("/graphs/{query}/edit")
def edit_graph(query: str, request: GraphEditRequest, current_user: User = Depends(get_current_user)):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query")
    
    user_id = current_user.id
    
    try:
        graphs = load_graphs(query, user_id)
        if not graphs or not graphs.get("knowledge_graph"):
            raise HTTPException(status_code=404, detail="Graph not found")
        
        kg = graphs["knowledge_graph"]
        updated_kg = apply_graph_edit(kg, request.action, request.model_dump())
        
        # Save the updated graph
        save_graphs(
            query=query, 
            user_id=user_id, 
            knowledge=updated_kg, 
            citation=graphs.get("citation_graph", {}), 
            analytics=graphs.get("research_analytics", {})
        )
        
        return {"status": "success", "message": "Graph updated", "data": updated_kg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph edit error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to edit graph")
