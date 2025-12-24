# services/graph_service.py
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
    Phase 3.1 Enhanced: Normalization and Frequency Calculation.
    
    # Convention: Concept -> Paper via 'appears_in'
    # Downstream analytics must treat edges as direction-agnostic
    """
    G = nx.DiGraph()

    # -----------------------------
    # Global-level concepts & relations
    # -----------------------------
    if global_analysis:
        for node in global_analysis.get("nodes", []):
            if isinstance(node, dict):
                node_id = node.get("id")
                if node_id:
                    norm_id = node_id.strip() # Case sensitivity: Keep original for display but maybe inconsistent?
                    # Plan says: concept_id = concept.strip().lower()
                    # Let's use lower for ID to prevent dupes, but store label
                    norm_id = node_id.strip().lower()
                    G.add_node(
                        norm_id,
                        label=node_id, # Display name
                        type=node.get("type", "concept")
                    )
            else:
                s_node = str(node).strip()
                G.add_node(s_node.lower(), label=s_node, type="concept")

        # Relations
        for rel in global_analysis.get("relations", []):
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                G.add_edge(
                    src.strip().lower(),
                    tgt.strip().lower(),
                    relation=rel.get("relation", "related_to"),
                    evidence=rel.get("evidence"),
                )

    # -----------------------------
    # Paper-level relations (Explicit Concept Links)
    # -----------------------------
    if paper_concepts:
        for paper_id, concepts in paper_concepts.items():
            if not concepts:
                continue
            
            # Ensure paper node exists
            # IDs for papers are usually Canonical IDs, so we keep them as is
            G.add_node(paper_id, type="paper", label=paper_id)
            
            for concept in concepts:
                norm_concept = concept.strip().lower()
                # Ensure concept node exists
                if norm_concept not in G:
                    G.add_node(norm_concept, type="concept", label=concept.strip())
                
                # Explicit edge
                G.add_edge(
                    norm_concept,
                    paper_id,
                    relation="appears_in"
                )

    # -----------------------------
    # Paper-level LLM relations
    # -----------------------------
    if paper_relations:
        for relations in paper_relations.values():
            for rel in relations:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt:
                    G.add_edge(
                        src.strip().lower(),
                        tgt.strip().lower(),
                        relation=rel.get("relation", "related_to"),
                    )

    # -----------------------------
    # Enhanced Annotation: Paper Frequency
    # -----------------------------
    # Calculate paper frequency for all concepts
    max_freq = 0
    concept_frequencies = {}

    for node in G.nodes():
        if G.nodes[node].get("type") == "concept":
            # Count papers connected (successors/predecessors agnostic approach)
            # Since we just added edges Concept->Paper as 'appears_in', check successors
            try:
                successors = list(G.successors(node))
            except:
                successors = []
            
            paper_nodes = [n for n in successors if G.nodes[n].get("type") == "paper"]
            paper_count = len(paper_nodes)
            
            G.nodes[node]["paper_frequency"] = paper_count
            G.nodes[node]["paper_ids"] = paper_nodes
            concept_frequencies[node] = paper_count
            if paper_count > max_freq:
                max_freq = paper_count
    
    # Store normalized frequency
    if max_freq > 0:
        for node, freq in concept_frequencies.items():
             G.nodes[node]["paper_frequency_norm"] = round(freq / max_freq, 2)

    logger.info(
        "🧠 Knowledge Graph: %d nodes, %d edges (Annotated)",
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

    # Create paper nodes
    for paper in selected_papers:
        canonical_id = paper.get("canonical_id")
        if not canonical_id:
            logger.warning("Skipping paper missing canonical_id")
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

    # Add citation edges
    edge_count = 0
    for paper in selected_papers:
        src_cid = paper.get("canonical_id")
        if not src_cid: continue

        metadata = paper.get("metadata", {}) or {}
        references = metadata.get("references", [])
        if not isinstance(references, list): continue

        for ref in references:
            ref_s2_id = ref.get("paperId")
            if not ref_s2_id: continue

            tgt_cid = s2_to_canonical.get(str(ref_s2_id))
            if tgt_cid and tgt_cid != src_cid:
                G.add_edge(src_cid, tgt_cid, type="citation")
                edge_count += 1

    logger.info("📎 Citation Graph: %d nodes, %d edges", G.number_of_nodes(), edge_count)
    return json_graph.node_link_data(G)


def enrich_knowledge_graph(kg_data: Dict, cg_data: Dict) -> Dict:
    """
    Level 3: Cross-Graph Reasoning
    Enrich Knowledge Graph nodes with citation-based metrics.
    """
    if not cg_data or "nodes" not in cg_data: return kg_data

    try:
        G_kg = nx.node_link_graph(kg_data)
        G_cg = nx.node_link_graph(cg_data)
    except Exception as exc:
        logger.error("Failed to reconstruct graphs for enrichment: %s", exc)
        return kg_data

    if G_cg.number_of_nodes() == 0: return kg_data

    citation_counts = dict(G_cg.in_degree())
    try:
        pagerank_scores = nx.pagerank(G_cg, alpha=0.85)
    except:
        pagerank_scores = {}

    enriched = 0
    for node_id in G_kg.nodes:
        if node_id in G_cg.nodes:
            G_kg.nodes[node_id]["citation_count"] = citation_counts.get(node_id, 0)
            G_kg.nodes[node_id]["pagerank"] = pagerank_scores.get(node_id, 0.0)
            enriched += 1

    logger.info("🔗 Cross-Graph: Enriched %d KG nodes", enriched)
    return json_graph.node_link_data(G_kg)
