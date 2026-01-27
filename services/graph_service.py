# services/graph_service.py
import logging
from typing import Dict, List, Any, Optional

import networkx as nx
from networkx.readwrite import json_graph
import re

from services.graph_persistence_service import load_graphs, save_graphs
from services.graph_analytics_service import GraphAnalyticsService

logger = logging.getLogger(__name__)


from services.schema.relation_ontology import get_relation_props, CausalStrength
from enum import Enum

class EvaluationMode(Enum):
    STRICT = "strict"
    SCARCITY = "scarcity"


def calculate_confidence(
    base_confidence: float,
    evidence_count: int,
    agreement_bonus: float = 0.0,
    conflict_penalty: float = 0.0,
    citation_bonus: float = 0.0
) -> float:
    """
    Research-Grade Confidence Scoring Algorithm.
    Formula: (Base + Source_Boost + Agreement + Citation_Boost) * Consistency
    """
    # 1. Source Boost: Diminishing returns for more sources
    # 1 source -> +0.0, 2 -> +0.1, 3 -> +0.15, 5+ -> +0.2
    source_boost = 0.0
    if evidence_count >= 5: source_boost = 0.2
    elif evidence_count >= 3: source_boost = 0.15
    elif evidence_count >= 2: source_boost = 0.1
    
    final_score = base_confidence + source_boost + agreement_bonus + citation_bonus - conflict_penalty
    return max(0.1, min(1.0, final_score)) # Cap between 0.1 and 1.0


def build_knowledge_graph(
    paper_relations: Optional[Dict[str, List[Dict]]] = None,
    paper_concepts: Optional[Dict[str, List[str]]] = None,
    global_analysis: Optional[Dict[str, Any]] = None,
    run_meta: Optional[Dict[str, Any]] = None,
    overrides: Optional[List[Dict]] = None, # Phase 3: User Feedback
    evaluation_mode: EvaluationMode = EvaluationMode.STRICT,
    papers: Optional[List[Dict]] = None # Phase 4: Citation Metadata
) -> Dict:
    """
    Build a semantic Knowledge Graph (KG) with Verification & Confidence Scoring.
    Phase 1 Enhanced: Logically verified, evidence-backed graph construction.
    Phase 3: Added Run-Level Provenance & User Overrides.
    Phase 4: Added Scarcity Mode and Citation-Based Confidence.
    """
    # -----------------------------
    # Scarcity Settings
    # -----------------------------
    is_scarcity = (evaluation_mode == EvaluationMode.SCARCITY)
    MIN_PAPERS = 2 if is_scarcity else 3
    MIN_EDGES = 3 if is_scarcity else 5
    CONFIDENCE_FLOOR = 0.35 if is_scarcity else 0.45 
    ALLOW_ASSOCIATIVE = is_scarcity  # Allow weaker edges in scarcity mode
    
    logger.info(f"🏗️ Building Graph in {evaluation_mode.value.upper()} mode (Min Papers: {MIN_PAPERS})")

    G = nx.MultiDiGraph() # Changed to MultiDiGraph to support conflicting edges (research-grade)
    if run_meta:
        G.graph["meta"] = run_meta

    # Index Papers for Citation Lookup
    paper_map = {}
    if papers:
        for p in papers:
            # We match by ID used in relations key
            pid = p.get("id") or p.get("paper_id") # normalized paper_id
            if pid: paper_map[str(pid)] = p
            # Also map canonical if different
            cid = p.get("canonical_id")
            if cid: paper_map[str(cid)] = p

    # -----------------------------
    # Helper: Canonicalization (Methodological Requirement)
    # -----------------------------
    def canonical_concept_id(text: str) -> str:
        """
        Research-Grade Canonicalization.
        Prevents 'Self Attention' vs 'self-attention' fragmentation.
        """
        if not text: return ""
        # Improved Normalization: strip, lower, hyphen/underscore replacement, and regex whitespace collapse
        text = text.strip().lower().replace("-", " ").replace("_", " ")
        return re.sub(r'\s+', ' ', text)

    # Helpers for Overrides
    reject_set = set()
    confirm_set = set()
    
    if overrides:
        for o in overrides:
            # Defensively check inputs
            src_raw = o.get("source")
            tgt_raw = o.get("target")
            
            if not src_raw or not tgt_raw:
                logger.warning(f"Skipping malformed override entry: {o}")
                continue
                
            s, t = canonical_concept_id(src_raw), canonical_concept_id(tgt_raw)
            act = o.get("action")
            
            if act == "reject_edge":
                reject_set.add((s, t))
            elif act == "confirm_edge":
                confirm_set.add((s, t))
            elif act == "add_edge":
                # Priority 4: Manual Additions
                # We add them logic-free here (they skip aggregation verification)
                # But we must ensure nodes exist
                rel = o.get("relation", "related_to")
                
                if s not in G: G.add_node(s, label=src_raw, type="concept", manual=True)
                if t not in G: G.add_node(t, label=tgt_raw, type="concept", manual=True)
                
                # Get props
                props = get_relation_props(rel)
                
                # Add confident edge
                G.add_edge(
                    s, t,
                    relation=props.label,
                    original_relation=rel,
                    polarity=props.polarity,
                    causal_strength=props.strength.value,
                    confidence=1.0, # Human = Truth
                    evidence_count=1,
                    evidence=[{"source": "user_override", "user_id": run_meta.get("user_id", "unknown") if run_meta else "user"}],
                    is_hypothesis=False,
                    is_manual=True
                )

    # Intermediate storage for edge aggregation: (source, target, relation_type) -> List[evidence]
    aggregated_edges: Dict[tuple, List[Dict]] = {}
    
    # Helper to add to aggregation
    def _add_relation_candidate(src, tgt, rel_type, evidence_item):
        s_canon = canonical_concept_id(src)
        t_canon = canonical_concept_id(tgt)
        if not s_canon or not t_canon: return
        
        # User Feedback Check: Global REJECT (Optimization)
        if (s_canon, t_canon) in reject_set:
            return 

        # Key is STRICTLY directional now, but relies on canonical IDs
        key = (s_canon, t_canon, rel_type.strip().lower())
        
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
                    canon_id = canonical_concept_id(node_id)
                    G.add_node(canon_id, label=node_id, type=node.get("type", "concept"))
            else:
                s_node = str(node).strip()
                G.add_node(canonical_concept_id(s_node), label=s_node, type="concept")

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
                    s_canon = canonical_concept_id(src)
                    t_canon = canonical_concept_id(tgt)
                    
                    if s_canon not in G: G.add_node(s_canon, label=src, type="concept")
                    if t_canon not in G: G.add_node(t_canon, label=tgt, type="concept")

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
            
            for concept in set(concepts):  # Deduplicate
                c_canon = canonical_concept_id(concept)
                if c_canon not in G: 
                    G.add_node(c_canon, type="concept", label=concept)
                
                # Direct Concept->Paper link (associative)
                G.add_edge(c_canon, paper_id, relation="appears_in", confidence=1.0, type="meta")

    # -----------------------------
    # 4. Verification & Edge Construction
    # -----------------------------
    # -----------------------------
    # 4. Verification & Edge Construction
    # -----------------------------

    # Phase 2: Graph Construction & Enrichment
    # -----------------------------
    
    # 2a. Add Edges with Initial Confidence (Pass 1)
    temp_edges = []
    
    for relation_key, evidence_list in aggregated_edges.items():
        src, tgt, rel_raw = relation_key
        props = get_relation_props(rel_raw)
        
        # Calculate Base Confidence from Evidence
        unique_papers = set()
        max_citations = 0

        for ev in evidence_list:
             pid = ev.get("paper_id")
             if pid: 
                 unique_papers.add(pid)
                 # Check Citations
                 if paper_map and pid in paper_map:
                     p_meta = paper_map[pid].get("metadata", {})
                     # Try multiple keys because structure varies
                     cc = p_meta.get("citationCount") or p_meta.get("citation_count") or 0
                     if isinstance(cc, int) and cc > max_citations:
                         max_citations = cc
        
        evidence_count = len(unique_papers)
        
        # Citation Bonus
        # Logarithmic-ish steps
        citation_bonus = 0.0
        if max_citations > 1000: citation_bonus = 0.15
        elif max_citations > 100: citation_bonus = 0.10
        elif max_citations > 20: citation_bonus = 0.05
        
        # User Feedback Check
        agreement_bonus = 0.3 if (src, tgt) in confirm_set else 0.0
        
        # Store for Pass 2
        temp_edges.append({
            "u": src, "v": tgt, "key": relation_key, 
            "evidence_count": evidence_count,
            "agreement_bonus": agreement_bonus,
            "citation_bonus": citation_bonus,
            "evidence_list": evidence_list,
            "props": props
        })
        
        # Add basic edge for PageRank
        G.add_edge(src, tgt)

    # 2b. Compute PageRank (on preliminary graph)
    pagerank = {}
    if G.number_of_edges() > 0:
        try:
            pagerank = nx.pagerank(G, alpha=0.85)
        except Exception as e:
            logger.debug(f"PageRank computation failed: {e}")

    # 2c. Finalize Edges with Boosted Confidence (Pass 2)
    # Preserve Manual Edges before clearing
    manual_edges_backup = []
    for u, v, data in G.edges(data=True):
        if data.get("is_manual"):
            manual_edges_backup.append((u, v, data))

    G.remove_edges_from(list(G.edges))
    
    confidence_calibration = {"0.0-0.3": 0, "0.3-0.6": 0, "0.6-1.0": 0}

    for edge_data in temp_edges:
        src = edge_data["u"]
        tgt = edge_data["v"]
        
        # Citation Bonus (PageRank)
        src_rank = pagerank.get(src, 0)
        tgt_rank = pagerank.get(tgt, 0)
        
        rank_bonus = 0.0
        if src_rank > 0.05 and tgt_rank > 0.05:
            rank_bonus = 0.05
            
        conf_score = calculate_confidence(
            0.6, 
            edge_data["evidence_count"], 
            agreement_bonus=edge_data["agreement_bonus"] + rank_bonus,
            citation_bonus=edge_data["citation_bonus"]
        )
        
        # Calibration Tracking
        if conf_score < 0.3: confidence_calibration["0.0-0.3"] += 1
        elif conf_score < 0.6: confidence_calibration["0.3-0.6"] += 1
        else: confidence_calibration["0.6-1.0"] += 1

        # Research Flags
        is_hypothesis = conf_score < CONFIDENCE_FLOOR
        insufficient_evidence = edge_data["evidence_count"] == 1 and conf_score < 0.5

        # Add Final Edge
        G.add_edge(
            src, tgt, 
            relation=edge_data["props"].label, # Use .label from props
            original_relation=edge_data["key"][2], # rel_raw
            polarity=edge_data["props"].polarity,
            causal_strength=edge_data["props"].strength.value,
            symmetric=edge_data["props"].symmetric,
            confidence=conf_score,
            evidence_count=edge_data["evidence_count"],
            evidence=edge_data["evidence_list"],
            is_hypothesis=is_hypothesis,
            insufficient_evidence=insufficient_evidence
        )
        
    # Re-add Manual Edges
    for u, v, data in manual_edges_backup:
        G.add_edge(u, v, **data)
    
    # Store calibration metadata in graph attributes for later analysis
    G.graph["confidence_calibration"] = confidence_calibration

    # -----------------------------
    # Phase 4 Safety: Scope Verification
    # -----------------------------
    total_papers = len(paper_relations) if paper_relations else 0
    
    # Meaningful Edge Count (Exclude 'appears_in', low confidence)
    # Refined logic using ALLOW_ASSOCIATIVE flag
    # Meaningful Edge Count (Exclude 'appears_in', low confidence)
    raw_edge_count = G.number_of_edges()
    is_sparse = raw_edge_count < 20 # Dynamic Scarcity Mode

    meaningful_edges = []
    for _, _, e in G.edges(data=True):
        # 1. Check Confidence
        # If sparse, lower the floor to show *something* (Exploratory)
        effective_floor = CONFIDENCE_FLOOR * 0.5 if is_sparse else CONFIDENCE_FLOOR
        
        if e.get("confidence", 0) < effective_floor: 
            continue
            
        # 2. Check Relation Type compatibility
        rel = e.get("relation")
        
        # Always exclude meta-relation "appears_in" from Counting Scope
        if rel == "appears_in": 
            continue
            
        # If NOT in Scarcity Mode (ALLOW_ASSOCIATIVE=False), exclude weak associations
        # BUT if graph is sparse, allow them to spur curiosity
        if not ALLOW_ASSOCIATIVE and not is_sparse and rel == "associated_with":
            continue
            
        meaningful_edges.append(e)
    
    total_edges = len(meaningful_edges)
    
    # Rule: < MIN_PAPERS OR < MIN_EDGES -> Insufficient
    if total_papers < MIN_PAPERS or total_edges < MIN_EDGES:
        G.graph["scope_limited"] = True
        logger.warning(f"⚠️ Graph Scope Limited: {total_papers} papers, {total_edges} edges. Analytics will be refused.")
    else:
        G.graph["scope_limited"] = False
        
    G.graph["evaluation_mode"] = evaluation_mode.value
    G.graph["maturity"] = "exploratory" if is_scarcity else "verified"

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


def recompute_analytics_for_saved_graph(query: str, user_id: str):
    """
    Phase 2 Maintenance: Re-run analytics after a Manual Graph Edit.
    Ensures 'conflicts', 'gaps', and 'novelty' reflect user changes.
    """
    data = load_graphs(query, user_id)
    if not data or not data.get("knowledge_graph"):
        logger.warning(f"No graph found for {query} to recompute analytics.")
        return

    logger.info(f"Recomputing analytics for {query}...")
    kg_data = data["knowledge_graph"]
    
    # 1. Run Analytics
    analytics_service = GraphAnalyticsService(kg_data)
    new_analytics = analytics_service.analyze()
    
    # 2. Save Back
    save_graphs(
        query, user_id, 
        kg_data, 
        data.get("citation_graph", {}),
        new_analytics
    )
    logger.info("✅ Analytics updated.")
