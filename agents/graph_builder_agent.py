# agents/graph_builder_agent.py
import logging
from typing import Dict
from services.graph_service import build_knowledge_graph, build_citation_graph
from services.graph_persistence_service import save_graphs

logger = logging.getLogger(__name__)


class GraphBuilderAgent:
    """
    Converts analysis output + metadata into Knowledge + Citation graphs.
    """

    def run(self, state: Dict) -> Dict:
        query = state.get("query")
        if not query:
            logger.error("Missing required 'query' in state for graph building")
            state["error"] = "Missing query for graph building"
            return state

        user_id = state.get("user_id", "demo-user")

        selected_papers = state.get("selected_papers", [])
        global_analysis = state.get("global_analysis", {})

        paper_relations = state.get("paper_relations") or {}
        paper_concepts = state.get("paper_concepts") or {}

        # ----------------------------
        # Build Knowledge Graph
        # ----------------------------
        kg = build_knowledge_graph(
            paper_relations=paper_relations,
            paper_concepts=paper_concepts,
            global_analysis=global_analysis
        )

        # ----------------------------
        # Build Citation Graph (canonical IDs only)
        # ----------------------------
        citation_graph = build_citation_graph([
            {"id": p.get("canonical_id")}
            for p in selected_papers
            if p.get("canonical_id")
        ])

        try:
            save_graphs(query, user_id, kg, citation_graph)
        except Exception as e:
            logger.error(f"Failed to persist graphs for query={query}: {e}")

        state["knowledge_graph"] = kg
        state["citation_graph"] = citation_graph
        state["current_step"] = "awaiting_graph_review"

        return state


graph_builder_agent = GraphBuilderAgent()
