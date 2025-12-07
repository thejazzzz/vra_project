# File: agents/graph_builder_agent.py
import logging
from state.state_schema import VRAState
from services.graph_service import build_knowledge_graph, build_citation_graph

logger = logging.getLogger(__name__)

class GraphBuilderAgent:
    def run(self, state: VRAState) -> VRAState:
        logger.info("📊 Running Graph Builder Agent")

        # Build Knowledge Graph
        state["knowledge_graph"] = build_knowledge_graph(
            paper_relations=state.get("paper_relations", {}),
            paper_concepts=state.get("paper_concepts", {}),
            global_analysis=state.get("global_analysis", {})
        )

        # Build Citation Graph (if user picked papers)
        selected = state.get("selected_papers") or state.get("collected_papers") or []
        state["citation_graph"] = build_citation_graph(selected)

        # Move workflow to next HITL stage
        state["current_step"] = "awaiting_graph_review"

        logger.info("📊 Graphs created and awaiting human review")
        return state


graph_builder_agent = GraphBuilderAgent()
