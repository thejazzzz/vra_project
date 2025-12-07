# File: agents/graph_builder_agent.py
import logging
from typing import Dict, List, Any

from state.state_schema import VRAState
from services.graph_service import build_knowledge_graph, build_citation_graph
from utils.sanitization import clean_text, is_nonempty_text

logger = logging.getLogger(__name__)


class GraphBuilderAgent:
    def _bootstrap_from_global_analysis(self, state: VRAState) -> None:
        """
        If per-paper analysis is not yet implemented, we bootstrap
        paper_concepts and paper_relations from global_analysis under
        a synthetic 'GLOBAL' paper id.
        """
        global_analysis = state.get("global_analysis", {}) or {}

        concepts = [
            clean_text(c)
            for c in global_analysis.get("key_concepts", []) or []
            if is_nonempty_text(c)
        ]
        relations_raw = global_analysis.get("relations", []) or []

        relations: List[Dict[str, Any]] = []
        for r in relations_raw:
            if not isinstance(r, dict):
                continue
            src = clean_text(r.get("source"))
            tgt = clean_text(r.get("target"))
            rel = clean_text(r.get("relation") or "related_to")
            if not (is_nonempty_text(src) and is_nonempty_text(tgt)):
                continue
            relations.append({"source": src, "target": tgt, "relation": rel})

        # Initialize structures if missing
        if concepts and "paper_concepts" not in state:
            state["paper_concepts"] = {"GLOBAL": concepts}

        if relations and "paper_relations" not in state:
            state["paper_relations"] = {"GLOBAL": relations}

    def run(self, state: VRAState) -> VRAState:
        logger.info("📊 Running Graph Builder Agent")

        # Ensure we have something to build from
        self._bootstrap_from_global_analysis(state)

        paper_concepts = state.get("paper_concepts", {})
        paper_relations = state.get("paper_relations", {})

        # Build Knowledge Graph
        state["knowledge_graph"] = build_knowledge_graph(
            paper_relations=paper_relations,
            paper_concepts=paper_concepts,
            global_analysis=state.get("global_analysis", {}),
        )

        # Build Citation Graph (if user picked papers)
        selected = state.get("selected_papers") or state.get("collected_papers") or []
        state["citation_graph"] = build_citation_graph(selected)

        # Move workflow to next HITL stage
        state["current_step"] = "awaiting_graph_review"

        logger.info("📊 Graphs created and awaiting human review")
        return state


graph_builder_agent = GraphBuilderAgent()
