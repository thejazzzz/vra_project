# File: workflow.py
import logging
import asyncio
from state.state_schema import VRAState
from agents.graph_builder_agent import graph_builder_agent
from agents.gap_analysis_agent import gap_analysis_agent
from agents.reporting_agent import reporting_agent
from services.analysis_service import run_analysis_task

logger = logging.getLogger(__name__)


async def run_step(state: VRAState) -> VRAState:
    try:
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
            return await _handle_analysis_step(state)

        # ---------------------------------------------------------
        # STEP 3 — BUILD GRAPHS
        # ---------------------------------------------------------
        if current == "awaiting_graphs":
            return await _handle_graph_build_step(state)

        # ---------------------------------------------------------
        # STEP 4 — WAIT FOR GRAPH REVIEW
        # ---------------------------------------------------------
        if current == "awaiting_graph_review":
            # This state waits for user signal.
            # If user approves, they might set state to 'awaiting_gap_analysis' or 'awaiting_report'
            return state

        # ---------------------------------------------------------
        # STEP 5 — REPORT GENERATION (placeholder)
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # STEP 4.5 — GAP ANALYSIS (New Level 4)
        # ---------------------------------------------------------
        # We run this automatically after graph review, or as part of reporting
        if current == "awaiting_gap_analysis":
             # Run gap analysis
            state = await asyncio.to_thread(gap_analysis_agent.run, state)
            state["current_step"] = "awaiting_report"
            return state

        # ---------------------------------------------------------
        # STEP 5 — REPORT GENERATION
        # ---------------------------------------------------------
        if current == "awaiting_report":
            # Real reporting agent
            state = await asyncio.to_thread(reporting_agent.run, state)
            return state

        # ---------------------------------------------------------
        # STEP 6 — WAIT FOR FINAL REVIEW
        # ---------------------------------------------------------
        if current == "awaiting_final_review":
            return state

        # ---------------------------------------------------------
        # DEFAULT → STOP
        # ---------------------------------------------------------
        if current not in ["completed", "failed", "error"]:
            logger.warning(f"Unknown workflow step encountered: {current}") 
            state["error"] = f"Unknown workflow step: {current}"
            state["current_step"] = "failed"
        return state

    except Exception as e:
        logger.error(f"Critical workflow error: {e}", exc_info=True)
        state["error"] = f"Workflow crashed: {str(e)}"
        state["current_step"] = "failed"
        return state


async def run_until_interaction(state: VRAState) -> VRAState:
    """
    Executes workflow steps continuously until it reaches a state requiring user interaction
    (e.g., 'awaiting_graph_review') or a terminal state.
    """
    max_steps = 10
    steps_run = 0

    while steps_run < max_steps:
        step = state.get("current_step")
        logger.info(f"🔄 Workflow Loop Step {steps_run+1}: {step}")

        # STOP: User Interaction Required
        if step in [
            "awaiting_research_review",
            "awaiting_graph_review",
            "awaiting_final_review",
        ]:
            break

        # STOP: Terminal States
        if step in ["completed", "failed", "error"]:
            break

        # Execute Next Step
        new_state = await run_step(state)
        steps_run += 1

        # Check for deadlock (no state change)
        if new_state.get("current_step") == step:
            logger.warning(f"Deadlock detected: State {step} did not transition. Stopping.")
            state = new_state
            break

        state = new_state

    if steps_run >= max_steps:
        logger.warning(f"Max steps ({max_steps}) reached. Stopping loop safely.")

    return state


async def _handle_analysis_step(state: VRAState) -> VRAState:
    query = state.get("query", "")
    papers = state.get("selected_papers") or []

    if not query or not papers:
        state["error"] = "Missing query or selected papers"
        state["current_step"] = "failed"
        return state

    logger.info("🧠 Performing global analysis...")
    audience = state.get("audience", "general")
    try:
        analysis = await run_analysis_task(query, papers, audience=audience)
        state["global_analysis"] = analysis
        state["current_step"] = "awaiting_graphs"
    except Exception as e:
        logger.error(f"Analysis step failed: {e}", exc_info=True)
        state["error"] = f"Analysis step failed: {str(e)}"
        state["current_step"] = "failed"
    
    return state


async def _handle_graph_build_step(state: VRAState) -> VRAState:
    logger.info("🔗 Building Knowledge + Citation Graphs")
    try:
        # Run graph builder
        # Note: graph_builder_agent.run returns a modified state
        state = await asyncio.to_thread(graph_builder_agent.run, state)
        
        # Check if the agent actually advanced the step
        if state.get("current_step") == "awaiting_graphs":
            # If it didn't move forward, assumption is it crashed or failed silently
            state["current_step"] = "failed"
            state["error"] = "Graph builder failed to advance state"
            
    except Exception as e:
        logger.error(f"Graph build error: {e}", exc_info=True)
        state["current_step"] = "failed"
        state["error"] = f"Graph build mechanism failed: {str(e)}"

    return state
