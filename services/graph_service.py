# services/graph_service.py
import logging
from typing import Dict, List, Any

import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger(__name__)


def build_knowledge_graph(
    paper_relations: Dict[str, List[Dict]] = None,
    paper_concepts: Dict[str, List[str]] = None,
    global_analysis: Dict[str, Any] = None,
) -> Dict:
    G = nx.DiGraph()

    # Global concepts
    if global_analysis:
        for c in global_analysis.get("key_concepts", []):
            G.add_node(c, type="concept")

        for rel in global_analysis.get("relations", []):
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                G.add_edge(src, tgt, relation=rel.get("relation", "related_to"))

    # Paper-level relations
    if paper_relations:
        for _, relations in paper_relations.items():
            for rel in relations:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt:
                    G.add_edge(src, tgt, relation=rel.get("relation", "related_to"))

    logger.info(f"🧠 Knowledge Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return json_graph.node_link_data(G)


def build_citation_graph(selected_papers: List[Dict]) -> Dict:
    G = nx.DiGraph()

    for p in selected_papers:
        cid = p.get("canonical_id")
        if not cid:
            logger.warning("Skipping paper missing canonical_id in citation graph")
            continue

        G.add_node(cid, type="paper")

    logger.info(f"📎 Citation Graph nodes = {G.number_of_nodes()}")
    return json_graph.node_link_data(G)
