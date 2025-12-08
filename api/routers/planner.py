# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from workflow import run_step
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class InputValidationError(ValueError):
    """Raised when user input is invalid."""
    pass


@router.post("/plan")
async def plan_task(payload: ResearchRequest) -> dict:
    """
    Planner entrypoint.

    Behavior:
      - Load previous state for this query from DB (if exists)
      - Otherwise, start a new state with this query
      - Run a single workflow step
      - Persist updated state back to DB
    """

    # 1️⃣ Validate input
    try:
        if not payload.query or not payload.query.strip():
            raise InputValidationError("Query cannot be empty")

        query = payload.query.strip()

    except InputValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # 2️⃣ Load saved workflow state for this query (if any)
    try:
        existing_state = load_state_for_query(query)
    except Exception as e:
        logger.error(f"Failed to load workflow state for query='{query}': {e}", exc_info=True)
        existing_state = None

    if existing_state:
        state: VRAState = existing_state
        logger.info(f"Resuming workflow for query='{query}' at step={state.get('current_step')}")
    else:
        state = VRAState(query=query)
        logger.info(f"Starting new workflow for query='{query}'")

    # 3️⃣ Inject collected papers into state if research step already performed
    # Research response structure: {"status": "...", "data": {"papers": [...]}}
    data_block = existing_state.get("data") if existing_state else None
    if data_block and isinstance(data_block, dict):
        papers_list = data_block.get("papers")
        if isinstance(papers_list, list) and papers_list:
            state["collected_papers"] = papers_list

    # 4️⃣ Execute one workflow step
    try:
        updated_state = await run_step(state)
    except Exception as e:
        logger.error(f"Error during workflow step: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during planning",
        )

    # 5️⃣ Persist updated state
    try:
        save_state_for_query(query=query, state=updated_state)
    except Exception as e:
        logger.error(f"Failed to save workflow state for query='{query}': {e}", exc_info=True)
        updated_state["error"] = "⚠ State was not persisted — workflow may not resume correctly."

    # Final response
    return updated_state
