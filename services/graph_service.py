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

    # 1. Map S2 IDs to Canonical IDs for internal linking
    s2_to_canonical = {}

    for p in selected_papers:
        cid = p.get("canonical_id")
        if not cid:
            logger.warning("Skipping paper missing canonical_id in citation graph")
            continue

        G.add_node(cid, type="paper", title=p.get("title", ""))
        
        # Check metadata for Semantic Scholar ID
        meta = p.get("metadata", {})
        
        # If the metadata itself IS the S2 payload (which it is for S2 agent)
        # normalize to always look for 'paperId'
        s2_id = meta.get("paperId") or p.get("paper_id")
        
        if s2_id:
            s2_to_canonical[str(s2_id)] = cid

    # 2. Add edges
    edge_count = 0
    for p in selected_papers:
        src_cid = p.get("canonical_id")
        if not src_cid: 
            continue

        # Extract references from metadata
        meta = p.get("metadata", {})
        references = meta.get("references", [])
        
        # If references is None (not a list), skip
        if not references:
            continue

        for ref in references:
            ref_s2_id = ref.get("paperId")
            if ref_s2_id:
                tgt_cid = s2_to_canonical.get(str(ref_s2_id))
                if tgt_cid and tgt_cid != src_cid:
                    G.add_edge(src_cid, tgt_cid, type="citation")
                    edge_count += 1

    logger.info(f"📎 Citation Graph: {G.number_of_nodes()} nodes, {edge_count} edges")
    return json_graph.node_link_data(G)
