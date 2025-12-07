# File: services/graph_service.py
import logging
from typing import Dict, List
import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger(__name__)


# ===============================
#  Knowledge Graph Builder
# ===============================
def build_knowledge_graph(
    paper_relations: Dict[str, List[Dict]],
    paper_concepts: Dict[str, List[str]],
    global_analysis: Dict
) -> Dict:
    """
    Build a concept-level graph from extracted relations + concepts.
    Output format: node-link JSON for visualization.
    """

    logger.info("Building Knowledge Graph...")

    G = nx.Graph()  # undirected for conceptual relationships

    # Collect all concepts and relations
    all_concepts = set()
    all_relations = []

    # Per-paper relations
    for pid, rels in paper_relations.items():
        all_relations.extend(rels)

    # Per-paper concepts
    for pid, concepts in paper_concepts.items():
        all_concepts.update(concepts)

    # Global analysis (optional)
    if global_analysis:
        global_rels = global_analysis.get("relations", [])
        global_concepts = global_analysis.get("key_concepts", [])
        all_relations.extend(global_rels)
        all_concepts.update(global_concepts)

    # Add nodes
    for concept in all_concepts:
        G.add_node(concept)

    # Add edges
    for rel in all_relations:
        src = rel.get("source")
        tgt = rel.get("target")
        if not src or not tgt:
            continue
        G.add_edge(src, tgt, relation=rel.get("relation", "related_to"))

    logger.info(f"KG: {len(G.nodes())} nodes, {len(G.edges())} edges")

    return json_graph.node_link_data(G)


# ===============================
#  Citation Graph Builder
# ===============================
def build_citation_graph(papers: List[Dict]) -> Dict:
    """
    Build a directed citation graph between papers.
    Requires `references` list in metadata if available.
    """

    logger.info("Building Citation Graph...")

    G = nx.DiGraph()

    # Add nodes
    for p in papers:
        pid = p.get("id")
        if pid:
            G.add_node(pid, title=p.get("title", "Unknown Title"))

    # Add citation edges
    for p in papers:
        src = p.get("id")
        refs = p.get("references", [])
        for ref in refs:
            if ref and ref in G.nodes():  # Only connect known papers
                G.add_edge(src, ref)

    logger.info(f"Citation Graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    return json_graph.node_link_data(G)
