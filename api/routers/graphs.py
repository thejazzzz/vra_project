# File: api/routers/graphs.py
import asyncio
from fastapi import APIRouter, HTTPException
from services.graph_persistence_service import load_graphs
import logging

logger = logging.getLogger(__name__)


router = APIRouter()

@router.get("/graphs/{query}")
async def get_graphs(query: str):
    user_id = "demo-user"  # Replace with real auth later
    try:
        graphs = await asyncio.to_thread(load_graphs, query, user_id)
    except Exception as e:
        # Log the full error for debugging
        # Avoid logging PII (user_id, query)
        logger.error("Error loading graphs", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading graphs")    

    # Distinguish "not found" (None) from "empty result"
    if graphs is None:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs  # Could be empty, which is valid
