# File: agents/planner_agent.py
"""
Rule-based Master Planner Agent (Phase 1)
This version controls the flow without an LLM.
Later we will replace logic with OpenAI decision-making.
"""
from state.state_schema import VRAState


class PlannerAgent:
    def decide_next_step(self, state: VRAState) -> str:
        if "query" not in state or not state["query"]:
            return "awaiting_query"  # No task yet

        # Step 1: If no papers collected
        if not state.get("collected_papers"):
            return "acquisition_agent"

        # Step 2: If no analysis results yet
        if not state.get("analysis_results"):
            return "analysis_agent"

        # Step 3: If report not yet generated
        if not state.get("draft_report"):
            return "report_agent"

        return "completed"

planner_agent = PlannerAgent()

