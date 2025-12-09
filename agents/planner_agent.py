# File: agents/planner_agent.py

from state.state_schema import VRAState

class PlannerAgent:
    def decide_next_step(self, state: VRAState) -> str:
        current = state.get("current_step")
        if not current:
            return "awaiting_research_review"

        # If HITL review required → STOP here
        if current.endswith("_review"):
            return current

        # Simplified sequential progression (skip analysis review for now)
        transition = {
            "awaiting_research_review": "awaiting_analysis",
            "awaiting_analysis": "awaiting_graphs",
            "awaiting_graphs": "awaiting_graph_review",
            "awaiting_graph_review": "awaiting_report",
            "awaiting_report": "awaiting_final_review",
            "awaiting_final_review": "completed",
        }

        return transition.get(current, "completed")


planner_agent = PlannerAgent()
