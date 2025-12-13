# File: workflow.py
import logging
import asyncio
from state.state_schema import VRAState
from agents.graph_builder_agent import graph_builder_agent
from services.analysis_service import run_analysis_task

logger = logging.getLogger(__name__)


async def run_step(state: VRAState) -> VRAState:
    current = state.get("current_step")
    logger.info(f"🔄 Workflow step: {current}")

    # ---------------------------------------------------------
    # STEP 1 — Human selects papers → move to analysis
    # ---------------------------------------------------------
    if current == "awaiting_research_review":
        state["current_step"] = "awaiting_analysis"
        return state

    # ---------------------------------------------------------
    # STEP 2 — GLOBAL ANALYSIS
    # ---------------------------------------------------------
    if current == "awaiting_analysis":
        query = state.get("query", "")
        papers = state.get("selected_papers") or []

        if not query or not papers:
            state["error"] = "Missing query or selected papers"
            state["current_step"] = "completed"
            return state

        logger.info("🧠 Performing global analysis...")
        try:
            analysis = await run_analysis_task(query, papers)
            state["global_analysis"] = analysis
            state["current_step"] = "awaiting_graphs"
        except Exception as e:
            logger.error(f"Analysis step failed: {e}")
            state["error"] = "Analysis step failed"
            state["current_step"] = "completed"

        return state

    # ---------------------------------------------------------
    # STEP 3 — BUILD GRAPHS
    # ---------------------------------------------------------
    if current == "awaiting_graphs":
        logger.info("🔗 Building Knowledge + Citation Graphs")
        try:
            state = await asyncio.to_thread(graph_builder_agent.run, state)
            if state.get("current_step") == "awaiting_graphs":
                state["current_step"] = "completed"
                state["error"] = "Graph builder failed to update state"
        except Exception as e:
            logger.error(f"Graph build error: {e}")
            state["current_step"] = "completed"
            state["error"] = "Graph build error"
        return state

    # ---------------------------------------------------------
    # STEP 4 — WAIT FOR GRAPH REVIEW
    # ---------------------------------------------------------
    if current == "awaiting_graph_review":
        return state

    # ---------------------------------------------------------
    # STEP 5 — REPORT GENERATION (placeholder)
    # ---------------------------------------------------------
    if current == "awaiting_report":
        state["draft_report"] = "Report generation coming soon..."
        state["current_step"] = "awaiting_final_review"
        return state

    # ---------------------------------------------------------
    # STEP 6 — WAIT FOR FINAL REVIEW
    # ---------------------------------------------------------
    if current == "awaiting_final_review":
        return state

    # ---------------------------------------------------------
    # DEFAULT → STOP
    # ---------------------------------------------------------
    state["current_step"] = "completed"
    return state
