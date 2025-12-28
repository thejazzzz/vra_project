# File: workflow.py
import logging
import asyncio
from state.state_schema import VRAState
from agents.graph_builder_agent import graph_builder_agent
from agents.paper_summarization_agent import paper_summarization_agent
# from services.data_normalization_service import normalize_paper_metadata (Will implement next)
from agents.gap_analysis_agent import gap_analysis_agent
from agents.reporting_agent import reporting_agent
from agents.hypothesis_generation_agent import hypothesis_generation_agent
from agents.reviewer_agent import reviewer_agent
from services.analysis_service import run_analysis_task
from services.trend_analysis_service import detect_concept_trends
from database.models.workflow_state_model import WorkflowState
from database.db import SessionLocal

logger = logging.getLogger(__name__)


async def run_step(state: VRAState) -> VRAState:
    try:
        current = state.get("current_step")
        logger.info(f"🔄 Workflow step: {current}")

        # ----------------------------------------------------
        # Phase 3.1 Safety: Transition Validation
        # ----------------------------------------------------
        ALLOWED_STEPS = {
            "awaiting_research_review", "awaiting_analysis",
            "awaiting_paper_summaries", "awaiting_graphs", "awaiting_graph_review",
            "awaiting_gap_analysis", "awaiting_hypothesis", "reviewing_hypotheses",
            "awaiting_report", "awaiting_final_review",
            "completed", "failed", "error"
        }
        if current not in ALLOWED_STEPS:
             logger.error(f"Illegal workflow state: {current}")
             state["error"] = f"Illegal workflow state: {current}"
             state["current_step"] = "failed"
             return state

        # ---------------------------------------------------------
        # STEP 1 — Human selects papers → move to analysis
        # ---------------------------------------------------------
        if current == "awaiting_research_review":
            state["current_step"] = "awaiting_analysis"
            return state

        # ---------------------------------------------------------
        # STEP 2 — GLOBAL ANALYSIS
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # STEP 2 — GLOBAL ANALYSIS
        # ---------------------------------------------------------
        if current == "awaiting_analysis":
            return await _handle_analysis_step(state)

        # ---------------------------------------------------------
        # STEP 2.5 — PAPER SUMMARIZATION (Phase 3)
        # ---------------------------------------------------------
        if current == "awaiting_paper_summaries":
            logger.info("📄 Generating structured paper summaries...")
            state = await asyncio.to_thread(paper_summarization_agent.run, state)
            
            # Run Trend Analysis (Phase 3) - Depends on summaries/concepts
            logger.info("📈 Detecting temporal trends...")
            try:
                trend_result = detect_concept_trends(
                    state.get("selected_papers", []),
                    state.get("paper_concepts", {}),
                    paper_relations=state.get("paper_relations", {})
                )
                state["concept_trends"] = trend_result.get("trends", {})
                logger.info(f"Trend Analysis Metadata: {trend_result.get('metadata')}")
            except Exception as e:
                logger.warning(f"Trend analysis failed: {e}")
                state["concept_trends"] = {}


            state["current_step"] = "awaiting_graphs"
            return state

        # ---------------------------------------------------------
        # STEP 3 — BUILD GRAPHS
        # ---------------------------------------------------------
        if current == "awaiting_graphs":
            return await _handle_graph_build_step(state)

        # ---------------------------------------------------------
        # STEP 4 — WAIT FOR GRAPH REVIEW
        # ---------------------------------------------------------
        if current == "awaiting_graph_review":
            if state.get("graph_approved", False):
                 state["current_step"] = "awaiting_gap_analysis"
            return state

        # ---------------------------------------------------------
        # STEP 5 — REPORT GENERATION (placeholder)
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # STEP 4.5 — GAP ANALYSIS (New Level 4)
        # ---------------------------------------------------------
        if current == "awaiting_gap_analysis":
             # Run gap analysis
            state = await asyncio.to_thread(gap_analysis_agent.run, state)
            state["current_step"] = "awaiting_hypothesis"
            return state

        # ---------------------------------------------------------
        # STEP 4.6 — HYPOTHESIS GENERATION (Phase 4)
        # ---------------------------------------------------------
        if current == "awaiting_hypothesis":
            state = await asyncio.to_thread(hypothesis_generation_agent.run, state)
            state["current_step"] = "reviewing_hypotheses"
            return state

        # ---------------------------------------------------------
        # STEP 4.7 — REVIEWER (Phase 4.1)
        # ---------------------------------------------------------
        if current == "reviewing_hypotheses":
            state = await asyncio.to_thread(reviewer_agent.run, state)
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
        
        # FIX 2: KG Consistency
        # Update selected_papers to the RE-RANKED subset used for analysis
        if "used_papers" in analysis:
            used = analysis["used_papers"]
            if used and isinstance(used, list):
                logger.info(f"KG Consistency: Updating selected_papers with {len(used)} re-ranked items.")
                state["selected_papers"] = used
            else:
                logger.debug("KG Consistency: used_papers empty or invalid. Keeping original selection.")
             
        state["current_step"] = "awaiting_paper_summaries"
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
