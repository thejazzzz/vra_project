# File: agents/planner_agent.py

from state.state_schema import VRAState
import logging


logger = logging.getLogger(__name__)


class PlannerAgent:
    def decide_next_step(self, state: VRAState) -> str:
        """
        For now, the workflow engine (run_step) owns the state machine.
        The planner just returns the current step or initializes it.

        This avoids accidentally skipping required steps like analysis.
        """
        current = state.get("current_step")

        # First time: move into the HITL review after research collection
        if not current:
            logger.info("Planner initializing state → awaiting_research_review")
            return "awaiting_research_review"

        # Do NOT auto-advance; let run_step interpret the current_step.
        # This prevents skipping 'awaiting_analysis' and other internal steps.
        logger.info(f"Planner keeping current_step as {current}")
        return current


planner_agent = PlannerAgent()
