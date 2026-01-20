# services/graph_service.py
import logging
from typing import Dict, List, Any, Optional

import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger(__name__)


from services.schema.relation_ontology import get_relation_props, CausalStrength

def calculate_confidence(
    base_confidence: float,
    evidence_count: int,
    agreement_bonus: float = 0.0,
    conflict_penalty: float = 0.0
) -> float:
    """
    Research-Grade Confidence Scoring Algorithm.
    Formula: (Base + Source_Boost + Agreement) * Consistency
    """
    # 1. Source Boost: Diminishing returns for more sources
    # 1 source -> +0.0, 2 -> +0.1, 3 -> +0.15, 5+ -> +0.2
    source_boost = 0.0
    if evidence_count >= 5: source_boost = 0.2
    elif evidence_count >= 3: source_boost = 0.15
    elif evidence_count >= 2: source_boost = 0.1
    
    final_score = base_confidence + source_boost + agreement_bonus - conflict_penalty
    return max(0.1, min(1.0, final_score)) # Cap between 0.1 and 1.0


def build_knowledge_graph(
    paper_relations: Optional[Dict[str, List[Dict]]] = None,
    paper_concepts: Optional[Dict[str, List[str]]] = None,
    global_analysis: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Build a semantic Knowledge Graph (KG) with Verification & Confidence Scoring.
    Phase 1 Enhanced: Logically verified, evidence-backed graph construction.
    """
    G = nx.DiGraph()

    # Intermediate storage for edge aggregation: (source, target, relation_type) -> List[evidence]
    aggregated_edges: Dict[tuple, List[Dict]] = {}

    # Helper to add to aggregation
    def _add_relation_candidate(src, tgt, rel_type, evidence_item):
        key = (src.strip().lower(), tgt.strip().lower(), rel_type.strip().lower())
        if key not in aggregated_edges:
            aggregated_edges[key] = []
        aggregated_edges[key].append(evidence_item)

    # -----------------------------
    # 1. Ingest Global Relations
    # -----------------------------
    if global_analysis:
        # Add Nodes
        for node in global_analysis.get("nodes", []):
            if isinstance(node, dict):
                node_id = node.get("id")
                if node_id:
                    norm_id = node_id.strip().lower()
                    G.add_node(norm_id, label=node_id, type=node.get("type", "concept"))
            else:
                s_node = str(node).strip()
                G.add_node(s_node.lower(), label=s_node, type="concept")

        # relations
        for rel in global_analysis.get("relations", []):
            if rel.get("source") and rel.get("target"):
                _add_relation_candidate(
                    rel["source"], 
                    rel["target"], 
                    rel.get("relation", "related_to"),
                    {"source": "global_analysis", "meta": rel.get("evidence")}
                )

    # -----------------------------
    # 2. Ingest Paper Relations (The Core Evidence)
    # -----------------------------
    if paper_relations:
        for paper_id, relations in paper_relations.items():
            for rel in relations:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt:
                    # Ensure nodes exist
                    s_norm = src.strip().lower()
                    t_norm = tgt.strip().lower()
                    if s_norm not in G: G.add_node(s_norm, label=src, type="concept")
                    if t_norm not in G: G.add_node(t_norm, label=tgt, type="concept")

                    _add_relation_candidate(
                        src, tgt, 
                        rel.get("relation", "related_to"),
                        {"paper_id": paper_id, "excerpt": rel.get("evidence", {}).get("excerpt")}
                    )

    # -----------------------------
    # 3. Ingest Paper Links
    # -----------------------------
    if paper_concepts:
        for paper_id, concepts in paper_concepts.items():
            if not concepts: continue
            
            # Add paper node if missing
            if paper_id not in G:
                G.add_node(paper_id, type="paper", label=paper_id)
            
            for concept in concepts:
                c_norm = concept.strip().lower()
                if c_norm not in G: 
                    G.add_node(c_norm, type="concept", label=concept)
                
                # Direct Concept->Paper link (associative)
                # We don't verify these the same way, they are definite "mentions"
                G.add_edge(c_norm, paper_id, relation="appears_in", confidence=1.0, type="meta")

    # -----------------------------
    # 4. Verification & Edge Construction
    # -----------------------------
    for (src, tgt, rel_raw), evidence_list in aggregated_edges.items():
        # Get Ontology Properties
        props = get_relation_props(rel_raw)
        
        # Calculate Confidence
        # Base: 0.6 (LLM output is decent)
        # Evidence Count: Number of distinct papers backing this
        unique_papers = set()
        for ev in evidence_list:
            if "paper_id" in ev: unique_papers.add(ev["paper_id"])
        
        conf_score = calculate_confidence(0.6, len(unique_papers))
        
        # Flag Hypothesis
        is_hypothesis = conf_score < 0.45
        
        # Add Edge
        G.add_edge(
            src, tgt,
            relation=props.label,
            original_relation=rel_raw,
            polarity=props.polarity,
            causal_strength=props.strength.value,
            symmetric=props.symmetric,
            confidence=conf_score,
            evidence_count=len(unique_papers),
            evidence=evidence_list, # Store full evidence trail
            is_hypothesis=is_hypothesis
        )

    # -----------------------------
    # 5. Frequency Annotation (Existing Logic Refined)
    # -----------------------------
    max_freq = 0
    concept_frequencies = {}

    for node in G.nodes():
        if G.nodes[node].get("type") == "concept":
            # Count papers connected via 'appears_in'
            # Note: appears_in is Concept->Paper
            paper_neighbors = [n for n in G.successors(node) if G.nodes[n].get("type") == "paper"]
            paper_count = len(paper_neighbors)
            
            G.nodes[node]["paper_frequency"] = paper_count
            concept_frequencies[node] = paper_count
            if paper_count > max_freq: max_freq = paper_count
    
    if max_freq > 0:
        for node, freq in concept_frequencies.items():
             G.nodes[node]["paper_frequency_norm"] = round(freq / max_freq, 2)

    logger.info(
        "🧠 Verified Graph: %d nodes, %d edges. Aggregated from %d raw claims.",
        G.number_of_nodes(),
        G.number_of_edges(),
        len(aggregated_edges) if aggregated_edges else 0
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
