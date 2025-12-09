# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.research_service import process_research_task
from agents.planner_agent import planner_agent
from workflow import run_step
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
USER_ID = "demo-user"


def _load_or_create_state(query: str):
    state = load_state_for_query(query, USER_ID)
    return state or VRAState(query=query)


@router.post("/plan")
async def plan_task(payload: ResearchRequest):
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    state = _load_or_create_state(query)

    if not state.get("collected_papers"):
        try:
            result = await process_research_task(query)
            if not result.get("success"):
                raise HTTPException(status_code=500, detail="Paper search failed")

            state["collected_papers"] = result["papers"]
            state["selected_papers"] = result["papers"].copy()
            state["current_step"] = "awaiting_research_review"

            save_state_for_query(query, state, USER_ID)
        except HTTPException:
            raise
        except Exception:
            logger.error("Research task failed", exc_info=True)
            raise HTTPException(status_code=500, detail="Paper search failed")

    
    return {"state": state}


@router.post("/continue")
async def continue_workflow(payload: ResearchRequest):
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    state = _load_or_create_state(query)

    if not state.get("collected_papers"):
        raise HTTPException(
            status_code=400,
            detail="No state initialized. Call /plan first."
        )

    try:
        next_step = planner_agent.decide_next_step(state)
        state["current_step"] = next_step
        updated = await run_step(state)
        save_state_for_query(query, updated, USER_ID)
        return {"state": updated}

    except Exception as e:
        logger.error("Workflow continuation failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )
