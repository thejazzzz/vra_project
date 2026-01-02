# agents/gap_analysis_agent.py
import logging
import networkx as nx
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class GapAnalysisAgent:
    """
    Analyzes Knowledge, Citation, and Author graphs to identify research gaps
    with supporting evidence, confidence scores, and detailed taxonomy.
    """
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🔍 Gap Analysis: Scanning for evidence-backed research opportunities...")
        
        kg_data = state.get("knowledge_graph")
        
        if not kg_data:
            logger.warning("No knowledge graph found. Skipping gap analysis.")
            return state

        try:
            KG = nx.node_link_graph(kg_data)
        except Exception as e:
            logger.error(f"Failed to parse graphs for gap analysis: {e}")
            state["research_gaps"] = []
            return state
        
        gaps = []

        # --------------------------------------------------------
        # Metrics Calculation Helpers (Phase 3.1 Enhanced)
        # --------------------------------------------------------
        
        # Calculate max papers for ANY concept for normalization
        max_papers = 0
        concept_nodes = [n for n in KG.nodes if KG.nodes[n].get("type") == "concept"]
        
        # Helper for robust paper neighbor finding (Direction Agnostic)
        def get_paper_neighbors(concept_node):
            out_neighbors = []
            in_neighbors = []
            try:
                out_neighbors = list(KG.successors(concept_node)) if KG.is_directed() else list(KG.neighbors(concept_node))
            except: pass
            
            try:
                in_neighbors = list(KG.predecessors(concept_node)) if KG.is_directed() else []
            except: pass
            
            all_neighbors = set(out_neighbors + in_neighbors)
            return [n for n in all_neighbors if KG.nodes[n].get("type") == "paper"]

        if concept_nodes:
            counts = []
            for c in concept_nodes:
                p_neighbors = get_paper_neighbors(c)
                counts.append(len(p_neighbors))
            if counts:
                max_papers = max(counts)

        def compute_confidence_and_nature(concept, G_undirected):
            # 1. Normalized Coverage (Optimized)
            # Use precomputed frequency if available
            paper_count = 0
            if "paper_frequency" in KG.nodes[concept]:
                paper_count = KG.nodes[concept]["paper_frequency"]
            else:
                # Fallback to manual calc
                paper_neighbors = get_paper_neighbors(concept)
                paper_count = len(paper_neighbors)
            
            norm_coverage = paper_count / max_papers if max_papers > 0 else 0

            # 2. Clustering Coefficient (Novelty proxy)
            try:
                clustering = nx.clustering(G_undirected, concept)
            except:
                clustering = 0

            # 3. Confidence Formula
            confidence = (
                0.5 * (1.0 - norm_coverage) +
                0.3 * (1.0 - clustering) +
                0.2 * 1.0 
            )
            
            # 4. Nature Classification
            nature = "nascent" if paper_count <= 1 else "under_explored"
            
            return round(min(confidence, 0.95), 2), paper_count, nature, clustering

        # Create undirected view for structural metrics
        KG_undirected = KG.to_undirected()

        # --------------------------------------------------------
        # Strategy 1: Conceptual Gaps (Under-explored Concepts)
        # --------------------------------------------------------
        for n in concept_nodes:
            confidence, paper_count, nature, clustering = compute_confidence_and_nature(n, KG_undirected)
            
            # Thresholds: Low coverage but existed in graph
            if paper_count <= 2 and confidence > 0.6:
                 rationale = f"Concept '{n}' has low coverage ({paper_count} papers) and low clustering ({clustering:.2f}), indicating a {nature} topic."
                 
                 gaps.append({
                        "gap_id": f"GAP_CONCEPT_{n.upper()}",
                        "gap_class": "conceptual",
                        "type": "under_explored_concept",
                        "subtype": nature,
                        "concept": n,
                        "description": f"The concept '{n}' is {nature} and lacks deep exploration.",
                        "rationale": rationale,
                        "evidence": {
                            "paper_count": paper_count,
                            "max_benchmark": max_papers,
                            "confidence_score": confidence
                        },
                        "confidence": confidence
                    })

        # --------------------------------------------------------
        # Strategy 2: Structural Gaps (Bridging Candidates)
        # --------------------------------------------------------
        is_connected_check = False
        if KG.is_directed():
            is_connected_check = nx.is_weakly_connected(KG)
            get_components = nx.weakly_connected_components
        else:
            is_connected_check = nx.is_connected(KG)
            get_components = nx.connected_components

        if not is_connected_check:
            components = list(get_components(KG))
            # Filter non-trivial
            significant_components = [c for c in components if len(c) >= 3]
            
            if len(significant_components) > 1:
                # Find bridging candidates in each component
                bridging_info = []
                
                for comp in significant_components:
                    # Concepts in this component
                    comp_concepts = [n for n in comp if KG.nodes[n].get("type") == "concept"]
                    # Sort by degree (hubs in their own cluster)
                    ranked = sorted(comp_concepts, key=lambda x: KG.degree(x), reverse=True)
                    
                    # Enrich candidates
                    for node in ranked[:2]:
                        bridging_info.append({
                            "concept": node,
                            "local_degree": KG.degree(node),
                            "cluster_size": len(comp)
                        })
                
                gaps.append({
                    "gap_id": "GAP_STRUCTURAL_BRIDGE",
                    "gap_class": "structural",
                    "type": "structural_hole",
                    "description": "Fragmented research clusters detected. Bridging these unrelated sub-fields is a high-impact opportunity.",
                    "rationale": f"Graph has {len(significant_components)} disconnected clusters. Connecting hubs from these clusters can yield novel combinations.",
                    "evidence": {
                        "cluster_count": len(significant_components),
                        "bridging_candidates": bridging_info
                    },
                    "confidence": 0.85
                })

        # Sort gaps by confidence
        gaps.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        top_gaps = gaps[:5]

        state["research_gaps"] = top_gaps
        
        if top_gaps:
            logger.info(f"✅ Gap Analysis: Identified {len(top_gaps)} high-confidence gaps.")
        else:
            logger.info("Gap Analysis: No significant gaps found.")

        return state

gap_analysis_agent = GapAnalysisAgent()
