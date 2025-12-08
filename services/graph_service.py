# File: services/graph_service.py
import logging
from typing import Dict, List, Any

import networkx as nx
from networkx.readwrite import json_graph  # <– use this version

logger = logging.getLogger(__name__)


def build_knowledge_graph(
    paper_relations: Dict[str, List[Dict]] = None,
    paper_concepts: Dict[str, List[str]] = None,
    global_analysis: Dict[str, Any] = None,
) -> Dict:
    """Build knowledge graph as JSON using NetworkX node-link format."""
    G = nx.DiGraph()

    # Global analysis concepts + relations
    if global_analysis:
        for c in global_analysis.get("key_concepts", []):
            G.add_node(c)

        for rel in global_analysis.get("relations", []):
            src = rel.get("source")
            tgt = rel.get("target")
            label = rel.get("relation", "related_to")
            if src and tgt:
                G.add_edge(src, tgt, relation=label)

    # Paper-level relations (future expansion)
    if paper_relations:
        for pid, relations in paper_relations.items():
            for rel in relations:
                src = rel.get("source")
                tgt = rel.get("target")
                label = rel.get("relation", "related_to")
                if src and tgt:
                    G.add_edge(src, tgt, relation=label)

    logger.info(
        f"🧠 Knowledge Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
    )

    # Use json_graph instead of nx.node_link_data to satisfy Pylance
    return json_graph.node_link_data(G, edges="edges")


def build_citation_graph(selected_papers: List[Dict]) -> Dict:
    """Minimal citation graph (nodes only for now)."""
    G = nx.DiGraph()
    for paper in selected_papers:
        pid = paper.get("id")
        if pid:
            G.add_node(pid)

    logger.info(f"📎 Citation Graph: {G.number_of_nodes()} paper nodes")

    return json_graph.node_link_data(G, edges="edges")
