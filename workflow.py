# File: workflow.py
import logging
from state.state_schema import VRAState

from agents.planner_agent import planner_agent  # currently unused but kept
from agents.graph_builder_agent import graph_builder_agent
from services.analysis_service import run_analysis_task

logger = logging.getLogger(__name__)


async def run_step(state: VRAState) -> VRAState:
    """
    Main asynchronous workflow execution entry point.
    Controls transitions between agents based on current state.
    """

    current = state.get("current_step")
    logger.info(f"🔄 Workflow run step: {current}")

    # =============================================================
    # STEP 1: Initial query complete → move to analysis
    # =============================================================
    if not current or current == "awaiting_query":
        state["selected_papers"] = state.get("collected_papers", [])
        state["current_step"] = "awaiting_analysis"
        return state

    # =============================================================
    # STEP 2: Global Analysis
    # =============================================================
    if current == "awaiting_analysis":
        query = state.get("query", "")
        papers = state.get("selected_papers", [])

        if not query or not papers:
            logger.error("❌ Missing query or selected papers for analysis.")
            state["error"] = "Missing input for analysis step"
            state["current_step"] = "completed"
            return state

        logger.info("🧠 Running global analysis...")
        try:
            result = await run_analysis_task(query, papers)
            state["global_analysis"] = result
            state["current_step"] = "awaiting_graphs"
        except Exception as e:
            logger.error(f"❌ Global analysis failed: {e}", exc_info=True)
            state["error"] = f"Analysis failed: {str(e)}"
            state["current_step"] = "completed"
        return state

    # =============================================================
    # STEP 3: Graph Builder Agent
    # =============================================================
    if current == "awaiting_graphs":
        logger.info("🧩 Building graphs...")
        try:
            state = graph_builder_agent.run(state)
            # graph_builder_agent sets current_step to "awaiting_graph_review"
        except Exception as e:
            logger.error(f"❌ Graph builder failed: {e}", exc_info=True)
            state["error"] = f"Graph build failed: {str(e)}"
            state["current_step"] = "completed"
        return state

    # =============================================================
    # STEP 4: Human Review
    # =============================================================
    if current == "awaiting_graph_review":
        logger.info("⏸ Awaiting graph & analysis review...")
        return state

    # =============================================================
    # STEP 5: Placeholder Report Generation
    # =============================================================
    if current == "awaiting_report":
        state["draft_report"] = "Report generation coming soon..."
        state["current_step"] = "awaiting_report_review"
        return state

    if current == "awaiting_report_review":
        logger.info("⏸ Awaiting report review...")
        return state

    # FINAL STATE
    state["current_step"] = "completed"
    return state
