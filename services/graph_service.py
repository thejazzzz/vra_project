#services/graph_service.py
import logging
from typing import Dict, List, Any, Optional

import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger(__name__)


def build_knowledge_graph(
    paper_relations: Optional[Dict[str, List[Dict]]] = None,
    paper_concepts: Optional[Dict[str, List[str]]] = None,
    global_analysis: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Build a semantic Knowledge Graph (KG) from LLM-extracted concepts and relations.
    """
    G = nx.DiGraph()

    # -----------------------------
    # Global-level concepts & relations
    # -----------------------------
    if global_analysis:
        # Typed nodes (preferred format)
        for node in global_analysis.get("nodes", []):
            if isinstance(node, dict):
                node_id = node.get("id")
                if node_id:
                    G.add_node(
                        node_id,
                        type=node.get("type", "concept")
                    )
            else:
                # Fallback if LLM returns plain strings
                G.add_node(str(node), type="concept")

        # Backward compatibility: key_concepts
        for concept in global_analysis.get("key_concepts", []):
            if concept not in G:
                G.add_node(concept, type="concept")

        # Semantic relations
        for rel in global_analysis.get("relations", []):
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                G.add_edge(
                    src,
                    tgt,
                    relation=rel.get("relation", "related_to"),
                    evidence=rel.get("evidence"),
                )

    # -----------------------------
    # Paper-level relations
    # -----------------------------
    if paper_relations:
        for relations in paper_relations.values():
            for rel in relations:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt:
                    G.add_edge(
                        src,
                        tgt,
                        relation=rel.get("relation", "related_to"),
                    )

    logger.info(
        "🧠 Knowledge Graph: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )

    return json_graph.node_link_data(G)


def build_citation_graph(selected_papers: List[Dict]) -> Dict:
    """
    Build a paper-to-paper citation graph using canonical paper IDs.
    """
    G = nx.DiGraph()
    s2_to_canonical: Dict[str, str] = {}

    # -----------------------------
    # Create paper nodes
    # -----------------------------
    for paper in selected_papers:
        canonical_id = paper.get("canonical_id")
        if not canonical_id:
            logger.warning(
                "Skipping paper missing canonical_id in citation graph"
            )
            continue

        G.add_node(
            canonical_id,
            type="paper",
            title=paper.get("title", ""),
        )

        metadata = paper.get("metadata", {}) or {}
        s2_id = metadata.get("paperId") or paper.get("paper_id")

        if s2_id:
            s2_to_canonical[str(s2_id)] = canonical_id

    # -----------------------------
    # Add citation edges
    # -----------------------------
    edge_count = 0

    for paper in selected_papers:
        src_cid = paper.get("canonical_id")
        if not src_cid:
            continue

        metadata = paper.get("metadata", {}) or {}
        references = metadata.get("references", [])

        if not isinstance(references, list):
            continue

        for ref in references:
            ref_s2_id = ref.get("paperId")
            if not ref_s2_id:
                continue

            tgt_cid = s2_to_canonical.get(str(ref_s2_id))
            if tgt_cid and tgt_cid != src_cid:
                G.add_edge(src_cid, tgt_cid, type="citation")
                edge_count += 1

    logger.info(
        "📎 Citation Graph: %d nodes, %d edges",
        G.number_of_nodes(),
        edge_count,
    )

    return json_graph.node_link_data(G)


def enrich_knowledge_graph(kg_data: Dict, cg_data: Dict) -> Dict:
    """
    Level 3: Cross-Graph Reasoning
    Enrich Knowledge Graph nodes with citation-based metrics.
    """
    if not cg_data or "nodes" not in cg_data:
        return kg_data

    try:
        G_kg = nx.node_link_graph(kg_data)
        G_cg = nx.node_link_graph(cg_data)
    except Exception as exc:
        logger.error(
            "Failed to reconstruct graphs for enrichment: %s",
            exc,
        )
        return kg_data

    if G_cg.number_of_nodes() == 0:
        return kg_data

    # -----------------------------
    # Citation metrics
    # -----------------------------
    citation_counts = dict(G_cg.in_degree())

    try:
        pagerank_scores = nx.pagerank(G_cg, alpha=0.85)
    except Exception as exc:
        logger.warning("PageRank computation failed: %s", exc)
        pagerank_scores = {}

    enriched = 0

    for node_id in G_kg.nodes:
        if node_id in G_cg.nodes:
            G_kg.nodes[node_id]["citation_count"] = citation_counts.get(
                node_id, 0
            )
            G_kg.nodes[node_id]["pagerank"] = pagerank_scores.get(
                node_id, 0.0
            )
            enriched += 1

    logger.info(
        "🔗 Cross-Graph: Enriched %d KG nodes with citation metrics",
        enriched,
    )

    return json_graph.node_link_data(G_kg)
