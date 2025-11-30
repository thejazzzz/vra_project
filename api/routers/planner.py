# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from workflow import run_step
from state.state_schema import VRAState
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/plan")
async def plan_task(payload: ResearchRequest) -> dict:
    try:
        state: VRAState = {"query": payload.query}

        # Offload sync blocking function to thread-pool
        updated_state = await asyncio.to_thread(run_step, state)

        return updated_state

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")

    except Exception as e:
        logger.error(f"Error in plan_task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred")
