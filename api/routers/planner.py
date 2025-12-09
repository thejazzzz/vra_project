# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from workflow import run_step
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.research_service import process_research_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/plan")
async def plan_task(payload: ResearchRequest) -> dict:
    user_id = "demo-user"  # TODO: integrate real auth later
    query = payload.query.strip() if payload.query else None

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1️⃣ Load state if it exists
    try:
        state = load_state_for_query(query, user_id) or VRAState(query=query)
    except Exception:
        logger.exception("Failed to load workflow state")
        state = VRAState(query=query)

    # 2️⃣ Auto-run research step if papers missing
    if not state.get("collected_papers"):
        logger.info("🔍 No papers found — running research collection...")
        research_result = await process_research_task(query)

        if not research_result.get("success", False):
            logger.error("Research failed")
            raise HTTPException(status_code=500, detail="Research step failed")

        papers = research_result.get("papers", [])
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found for query")

        state["collected_papers"] = papers
        state["selected_papers"] = papers  # default behavior initially
        state["current_step"] = "awaiting_analysis"  # ensure workflow continues

        # Save state after research
        try:
            save_state_for_query(query, state, user_id)
        except Exception:
            logger.exception("Failed to persist state after research")

    # 3️⃣ Execute workflow
    try:
        updated_state = await run_step(state)
    except Exception:
        logger.exception("Workflow step failed")
        raise HTTPException(status_code=500, detail="Workflow execution error")

    # 4️⃣ Persist workflow after step
    try:
        save_state_for_query(query, updated_state, user_id)
    except Exception:
        logger.exception("Failed to save updated workflow state")
        updated_state = {
            "state": updated_state,
            "warning": "⚠ State not persisted — workflow may not resume correctly."
        }

    return updated_state
