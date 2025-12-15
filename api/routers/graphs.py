# File: api/routers/graphs.py
from fastapi import APIRouter, HTTPException, Depends, Header
from services.graph_persistence_service import load_graphs
from typing import Optional


import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_user_id(x_user_id: Optional[str] = Header(None)):
    return x_user_id or "demo-user"


@router.get("/graphs/{query}")
def get_graphs(query: str, user_id: str = Depends(get_user_id)):

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query")

    try:
        graphs = load_graphs(query, user_id)
    except Exception as e:
        logger.error(f"Graph load error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load graphs")

    if graphs is None:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs
