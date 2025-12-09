# api/routers/graphs.py
from fastapi import APIRouter, HTTPException
from services.graph_persistence_service import load_graphs

router = APIRouter()

@router.get("/graphs/{query}")
async def get_graphs(query: str):
    user_id = "demo-user"  # later replaced with auth

    graphs = load_graphs(query, user_id)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return graphs
