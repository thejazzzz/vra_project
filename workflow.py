# File: workflow.py
import logging
from state.state_schema import VRAState
import asyncio

from agents.graph_builder_agent import graph_builder_agent
from services.analysis_service import run_analysis_task

logger = logging.getLogger(__name__)


async def run_step(state: VRAState) -> VRAState:
    """
    Main asynchronous workflow execution entry point.
    Controls transitions between agents based on current state.
    """

    current = state.get("current_step")
    logger.info(f"🔄 Workflow step: {current}")

    # =============================================================
    # STEP 1: Human reviewed research -> move to analysis
    # =============================================================
    if current == "awaiting_research_review":
        logger.info("📌 Research review complete → Next: Analysis")
        state["current_step"] = "awaiting_analysis"
        return state

    # =============================================================
    # STEP 2: Global Analysis
    # =============================================================
    if current == "awaiting_analysis":
        query = state.get("query", "")
        papers = state.get("selected_papers") or []

        if not query or not papers:
            state["error"] = "Missing query or papers for analysis"
            logger.error(state["error"])
            state["current_step"] = "completed"
            return state

        logger.info("🧠 Running analysis step...")
        try:
            result = await run_analysis_task(query, papers)
            state["global_analysis"] = result
            state["current_step"] = "awaiting_graphs"
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            state["error"] = "Analysis step failed"
            state["current_step"] = "completed"

        return state

    # =============================================================
    # STEP 3: Build Knowledge + Citation Graphs
    # =============================================================
    if current == "awaiting_graphs":
        logger.info("🔗 Building graphs...")
        try:
            state = await asyncio.to_thread(graph_builder_agent.run, state)
            # Agent sets: awaiting_graph_review
            if state.get("current_step") == "awaiting_graphs":
                logger.error("Agent failed to advance state from awaiting_graphs")
                state["error"] = "Graph builder agent did not advance workflow state"
                state["current_step"] = "completed"

        except Exception as e:
            logger.error(f"Graph build failed: {e}", exc_info=True)
            state["error"] = "Graph build failed"
            state["current_step"] = "completed"
        return state

    # =============================================================
    # STEP 4: Wait for user to review graphs
    # =============================================================
    if current == "awaiting_graph_review":
        logger.info("⏸ Awaiting graph review...")
        return state

    # =============================================================
    # STEP 5: Generate Report
    # =============================================================
    if current == "awaiting_report":
        logger.info("📝 Generating report (placeholder)")
        state["draft_report"] = "Report generation coming soon..."
        state["current_step"] = "awaiting_final_review"
        return state

    # =============================================================
    # STEP 6: Wait for final review
    # =============================================================
    if current == "awaiting_final_review":
        logger.info("⏸ Awaiting final review...")
        return state

    # FINAL FALLBACK
    state["current_step"] = "completed"
    return state
