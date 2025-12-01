# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from workflow import run_step
from state.state_schema import VRAState
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

class InputValidationError(ValueError):
    """Raised when user input is invalid."""
    pass

@router.post("/plan")
async def plan_task(payload: ResearchRequest) -> dict:
    # First: validate input only
    try:
        if not payload.query or not payload.query.strip():
            raise InputValidationError("Query cannot be empty")

        state: VRAState = {"query": payload.query}

    except InputValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Second: run sync logic in thread (could raise system errors)
    try:
        updated_state = await asyncio.to_thread(run_step, state)
        return updated_state

    except Exception as e:
        logger.error(f"Error in plan_task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred"
        )
