# agents/graph_builder_agent.py
import logging
from typing import Dict
from services.graph_service import build_knowledge_graph, build_citation_graph, enrich_knowledge_graph
from services.graph_persistence_service import save_graphs
from services.author_graph_service import build_author_graph

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

        user_id = state.get("user_id")
        if not user_id:
             logger.warning("Missing user_id in state for graph building")
             # Should we fail? For now, let's allow it but log heavily or maybe raise?
             # Given strict auth plan, we should probably fail or assume it was set by planner.
             state["error"] = "Missing user_id for graph building"
             return state

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
        # Build Citation Graph
        # ----------------------------
        citation_graph = build_citation_graph(selected_papers)

        # ----------------------------
        # Level 3: Cross-Graph Enrichment
        # ----------------------------
        try:
            logger.info(f"Enriching knowledge graph for query={query}")
            kg = enrich_knowledge_graph(kg, citation_graph)
        except Exception as e:
            logger.error(f"Failed to enrich knowledge graph for query={query}: {e}")
            #Continue with the original graph rather than failing completely


        try:
            save_graphs(query, user_id, kg, citation_graph)
        except Exception as e:
            logger.error(f"Failed to persist graphs for query={query}: {e}")

        # ----------------------------
        # Build Author Graph (Phase 3)
        # ----------------------------
        try:
            author_graph = build_author_graph(selected_papers)
            state["author_graph"] = author_graph
        except Exception as e:
            logger.error(f"Failed to build author graph for query={query}: {e}")
            state["author_graph"] = None

        state["knowledge_graph"] = kg
        state["citation_graph"] = citation_graph
        state["current_step"] = "awaiting_graph_review"

        return state


graph_builder_agent = GraphBuilderAgent()
