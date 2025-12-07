# File: workflow.py
import logging
from typing import Optional
from state.state_schema import VRAState

from agents.planner_agent import planner_agent
from agents.graph_builder_agent import graph_builder_agent
from services.analysis_service import run_analysis_task

logger = logging.getLogger(__name__)


def run_step(state: VRAState) -> VRAState:
    """
    Main synchronous workflow execution entry point.
    Controls transitions between agents based on current state.
    """

    current = state.get("current_step")
    logger.info(f"🔄 Workflow run step: {current}")

    # =============================================================
    # STEP 1: Initial Query -> Research step completed previously
    # =============================================================
    if not current or current == "awaiting_query":
        # After research endpoint finishes: move straight to selection
        state["selected_papers"] = state.get("collected_papers", [])
        state["current_step"] = "awaiting_analysis"
        return state

    # =============================================================
    # STEP 2: Global Analysis Agent
    # =============================================================
    if current == "awaiting_analysis":
        papers = state.get("selected_papers", [])
        query = state.get("query", "")

        if not query or not papers:
            logger.warning("❌ Missing query or selected papers for analysis step.")
            state["current_step"] = "completed"
            return state

        logger.info("🧠 Running global analysis...")
        result = run_global_analysis_sync(query, papers)
        state["global_analysis"] = result
        state["current_step"] = "awaiting_graphs"
        return state

    # =============================================================
    # STEP 3: Graph Builder Agent
    # =============================================================
    if current == "awaiting_graphs":
        state = graph_builder_agent.run(state)
        return state

    # =============================================================
    # STEP 4: Human Review of graphs and analysis
    # =============================================================
    if current == "awaiting_graph_review":
        logger.info("⏸ Awaiting human review before continuing...")
        # Workflow paused intentionally
        return state

    # =============================================================
    # STEP 5: Report Agent (later)
    # =============================================================
    if current == "awaiting_report":
        # TODO (future feature): call report synthesis
        state["draft_report"] = "Report generation coming soon..."
        state["current_step"] = "awaiting_report_review"
        return state

    if current == "awaiting_report_review":
        logger.info("⏸ Awaiting review of generated report...")
        return state

    state["current_step"] = "completed"
    return state


def run_global_analysis_sync(query: str, papers: list) -> dict:
    """Strict synchronous wrapper. Ensures a fresh event loop is used."""
    import asyncio
    return asyncio.run(run_analysis_task(query, papers))

