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
