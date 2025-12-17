# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.models.research_models import ResearchRequest
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.research_service import process_research_task
from agents.planner_agent import planner_agent
from copy import deepcopy

from workflow import run_step, run_until_interaction
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
        updated = await run_until_interaction(state)
        save_state_for_query(query, updated, USER_ID)
        return {"state": updated}

    except Exception as e:
        logger.error("Workflow continuation failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )


class PaperReviewRequest(BaseModel):
    query: str
    selected_paper_ids: list[str]
    audience: str = "general"


@router.post("/review")
async def review_papers(payload: PaperReviewRequest):
    query = (payload.query or "").strip()
    state = _load_or_create_state(query)

    if not state.get("collected_papers"):
        raise HTTPException(400, "No collected papers to review")

    # Filter papers
    selected_ids = set(payload.selected_paper_ids)
    all_papers = state.get("collected_papers", [])

    # Keep only selected papers in the active set
    # We still keep 'collected_papers' as history if needed, but 'selected_papers' drives the next steps
    final_selection = [p for p in all_papers if p.get("canonical_id") in selected_ids]

    if not final_selection:
        raise HTTPException(400, "No papers selected. Cannot proceed.")

    state["selected_papers"] = final_selection
    state["audience"] = payload.audience

    # Trigger next step: Analysis
    # We manually set the transition here because this IS the user interaction
    state["current_step"] = "awaiting_analysis"

    # Save immediately
    save_state_for_query(query, state, USER_ID)

    # Run loop
    try:
        updated = await run_until_interaction(state)
        save_state_for_query(query, updated, USER_ID)
        return {"state": updated}
    except Exception as e:
        logger.error("Review processing failed", exc_info=True)
        raise HTTPException(500, f"Failed to process review: {e}")


class GraphReviewRequest(BaseModel):
    query: str
    feedback: str = None
    approved: bool = True


@router.post("/review-graph")
async def review_graph(payload: GraphReviewRequest):
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(400, "Query required")

    state = _load_or_create_state(query)
    
    # Validation: Ensure we are in the right state
    if state.get("current_step") != "awaiting_graph_review":
        # Strict check or lenient? Lenient allows recovery. 
        # But let's log warning.
        logger.warning(f"Graph review received but state is {state.get('current_step')}")

    # Set next step
    # We move to Gap Analysis (Level 4) or Reporting (Level 5)
    # Workflow.py says: awaiting_gap_analysis
    state["current_step"] = "awaiting_gap_analysis"
    if payload.feedback:
        state["user_feedback"] = payload.feedback

    save_state_for_query(query, state, USER_ID)

    try:
        updated = await run_until_interaction(state)
        save_state_for_query(query, updated, USER_ID)
        return {"state": updated}
    except Exception as e:
        logger.error("Graph review continuation failed", exc_info=True)
        raise HTTPException(500, f"Workflow failed: {e}")


@router.get("/status/{query}")
def get_status(query: str):
    """
    Get the current status of the research task for polling.
    """
    state_obj = _load_or_create_state(query) # Helper leverages load_state_for_query
    
    # Need to handle if state is empty/new
    current_step = state_obj.get("current_step")
    
    return {
        "current_step": current_step,
        "papers_count": len(state_obj.get("selected_papers", [])),
        "draft_report": state_obj.get("draft_report"),
        "error": state_obj.get("error")
    }
