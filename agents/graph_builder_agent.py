# File: agents/graph_builder_agent.py
import logging
from typing import Dict, List, Any

from state.state_schema import VRAState
from services.graph_service import build_knowledge_graph, build_citation_graph
from utils.sanitization import clean_text, is_nonempty_text
from services.graph_persistence_service import save_graphs

logger = logging.getLogger(__name__)


class GraphBuilderAgent:
    def _bootstrap_from_global_analysis(self, state: VRAState) -> None:
        global_analysis = state.get("global_analysis", {}) or {}

        concepts = []
        for c in global_analysis.get("key_concepts", []) or []:
            cleaned = clean_text(c)
            if is_nonempty_text(cleaned):
                concepts.append(cleaned)
        relations_raw = global_analysis.get("relations", []) or []

        relations: List[Dict[str, Any]] = []
        for r in relations_raw:
            if not isinstance(r, dict):
                continue
            src = clean_text(r.get("source"))
            tgt = clean_text(r.get("target"))
            rel = clean_text(r.get("relation") or "related_to")
            if is_nonempty_text(src) and is_nonempty_text(tgt):
                relations.append({"source": src, "target": tgt, "relation": rel})

        if concepts and "paper_concepts" not in state:
            state["paper_concepts"] = {"GLOBAL": concepts}

        if relations and "paper_relations" not in state:
            state["paper_relations"] = {"GLOBAL": relations}

    def run(self, state: VRAState) -> VRAState:
        logger.info("📊 Running Graph Builder Agent")

        # Bootstrap if needed
        self._bootstrap_from_global_analysis(state)

        paper_concepts = state.get("paper_concepts", {})
        paper_relations = state.get("paper_relations", {})

        # Build knowledge graph
        state["knowledge_graph"] = build_knowledge_graph(
            paper_relations=paper_relations,
            paper_concepts=paper_concepts,
            global_analysis=state.get("global_analysis", {}),
        )

        # Build citation graph
        selected = state.get("selected_papers") or state.get("collected_papers") or []
        state["citation_graph"] = build_citation_graph(selected)

        # Persist if possible
        query = state.get("query")
        if not query:
            logger.warning("Query missing in state — graph persistence skipped")
            state["error"] = "Graph persistence skipped — no query found"
        else:
            try:
                save_graphs(
                    query=query,
                    user_id=state.get("user_id", "demo-user"),
                    knowledge=state["knowledge_graph"],
                    citation=state["citation_graph"]
                )
            except Exception as e:
                logger.error(f"Failed to persist graphs: {e}", exc_info=True)
                state["error"] = "Graph persistence failed — graphs available in-memory only"

        # Continue workflow (HITL)
        state["current_step"] = "awaiting_graph_review"
        logger.info("📊 Graphs available & awaiting review (persistence may have failed)")
        return state


graph_builder_agent = GraphBuilderAgent()
