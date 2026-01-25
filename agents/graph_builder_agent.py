# agents/graph_builder_agent.py
import logging
from typing import Dict
from services.graph_service import build_knowledge_graph, build_citation_graph, enrich_knowledge_graph, EvaluationMode
from services.graph_persistence_service import save_graphs
from services.author_graph_service import build_author_graph
from services.graph_analytics_service import GraphAnalyticsService

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
        # Phase 3: Run-Level Provenance
        # ----------------------------
        from uuid import uuid4
        from datetime import datetime
        
        run_meta = {
            "run_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "model_version": state.get("workflow_version", "v1.0"),
            "prompt_hash": state.get("prompt_hash", "unknown"),
        }

        # ----------------------------
        # Build Knowledge Graph
        # ----------------------------
        # Auto-Detect Scarcity
        # Trigger if paper count matches OR PDF coverage is low
        paper_count = len(selected_papers)
         
        # Calculate PDF coverage (Rely ONLY on status for robust check)
        # If 'pdf_status' is missing, do not count as success.
        successful_pdfs = sum(1 for p in selected_papers if p.get("pdf_status") == "success")
        
        pdf_success_rate = successful_pdfs / max(1, paper_count)
        eval_mode = EvaluationMode.STRICT
        
        if paper_count < 3 or pdf_success_rate < 0.4:
            logger.info(f"📉 Scarcity Detected (Papers: {paper_count}, PDF Rate: {pdf_success_rate:.0%}). Switching to SCARCITY mode.")
            eval_mode = EvaluationMode.SCARCITY
            
        kg = build_knowledge_graph(
            paper_relations=paper_relations,
            paper_concepts=paper_concepts,
            global_analysis=global_analysis,
            run_meta=run_meta,
            evaluation_mode=eval_mode,
            papers=selected_papers
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

        # ----------------------------
        # Phase 2: Research Analytics
        # ----------------------------
        try:
            logger.info("Running Research Analytics (Conflicts, Gaps, Novelty)...")
            analytics_service = GraphAnalyticsService(kg)
            analytics_results = analytics_service.analyze()
            state["research_analytics"] = analytics_results
        except Exception as e:
            logger.error(f"Research Analytics failed: {e}")
            state["research_analytics"] = {"error": str(e)}


        try:
            save_graphs(
                query, 
                user_id, 
                kg, 
                citation_graph, 
                state.get("research_analytics")
            )
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
