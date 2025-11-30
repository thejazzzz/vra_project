# File: workflow.py
"""
LangGraph-style state workflow (placeholder for Step A)
In Step B: this will be upgraded into a real LangGraph.
"""
from agents.planner_agent import planner_agent
from state.state_schema import VRAState


def run_step(state: VRAState) -> VRAState:
    step = planner_agent.decide_next_step(state)
    state["current_step"] = step
    return state

__all__ = ["run_step"]
