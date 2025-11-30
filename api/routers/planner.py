# File: api/routers/planner.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/plan")
async def plan_task():
    # Placeholder - planner logic will be implemented later
    return {"task": "planner received"}


