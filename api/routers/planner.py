# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.research_service import process_research_task
from agents.planner_agent import planner_agent
from copy import deepcopy

from workflow import run_step
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
USER_ID = "demo-user"


def _load_or_create_state(query: str):
    state = load_state_for_query(query, USER_ID)
    if state:
        return state
    
    # Initialize minimal valid state
    return VRAState(
        query=query,
        collected_papers=[],
        selected_papers=[],
        added_papers=[],
        paper_summaries={},
        paper_concepts={},
        paper_relations={},
        global_analysis={},
        knowledge_graph={},
        citation_graph={},
        current_step=None,
        user_feedback=None,
        audience="general",
    )


@router.post("/plan")
async def plan_task(payload: ResearchRequest):
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    state = _load_or_create_state(query)

    # If papers were already collected previously, return the state
    if state.get("collected_papers"):
        return {"state": state}

    try:
        result = await process_research_task(query)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Paper search failed")

        papers = result["papers"]

        # Ensure canonical_id exists
        for p in papers:
            if "canonical_id" not in p:
                logger.error(f"Paper missing canonical_id: {p}")
                raise HTTPException(status_code=500, detail="Paper missing canonical_id")

        state["collected_papers"] = papers
        state["selected_papers"] = deepcopy(papers)
        state["current_step"] = "awaiting_research_review"
        state["audience"] = payload.audience or "general"
        save_state_for_query(query, state, USER_ID)
        return {"state": state}

    except HTTPException:
        raise
    except Exception:
        logger.error("Research task failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Paper search failed")


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
