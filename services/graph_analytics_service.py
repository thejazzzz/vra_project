# services/graph_analytics_service.py
import networkx as nx
from typing import Dict, List, Any
import logging
from services.schema.relation_ontology import get_relation_props

logger = logging.getLogger(__name__)

class GraphAnalyticsService:
    """
    Phase 2: Advanced Research Analytics.
    Generates research-grade insights: Conflicts, Gaps, and Novelty.
    """
    
    def __init__(self, graph_data: Dict):
        # Reconstruct graph from JSON
        self.G = nx.node_link_graph(graph_data)
        
    def analyze(self) -> Dict[str, Any]:
        """Run full suite of research analytics."""
        return {
            "conflicts": self._detect_conflicts(),
            "gaps": self._detect_gaps(),
            "novelty": self._score_novelty(),
            "bias_metrics": self._analyze_bias()
        }

    # ------------------------------------------------------------------
    # 1. Conflict Detection (Using Ontology)
    # ------------------------------------------------------------------
    def _detect_conflicts(self) -> List[Dict]:
        """
        Find edges that semantically contradict each other.
        Relies on 'inverse' properties from Ontology.
        """
        conflicts = []
        full_edges = list(self.G.edges(data=True))
        
        # Naive O(E^2) Scan - acceptable for typical KG size (< 500 edges)
        # Optimized: group by (u, v)
        pair_map = {}
        for u, v, data in full_edges:
            # Skip Hypotheses (Failure Propagation Guard)
            if data.get("is_hypothesis"): continue
            
            key = tuple(sorted((u, v)))
            if key not in pair_map: pair_map[key] = []
            pair_map[key].append((u, v, data))
            
        for (u, v), edges in pair_map.items():
            if len(edges) < 2: continue
            
            # Check for direct contradictions
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    e1_u, e1_v, d1 = edges[i]
                    e2_u, e2_v, d2 = edges[j]
                    
                    # Get properties
                    p1 = get_relation_props(d1.get("original_relation", ""))
                    p2 = get_relation_props(d2.get("original_relation", ""))
                    
                    # Case 1: Direct Opposition (A->B improves vs A->B degrades)
                    # Polarity Conflict: +1 vs -1
                    if p1.polarity * p2.polarity < 0:
                         conflicts.append({
                             "type": "polarity_conflict",
                             "source": u, "target": v,
                             "relations": [d1["original_relation"], d2["original_relation"]],
                             "severity": "high"
                         })
                         
                    # Case 2: Exact Inverse (A->B supports vs A->B refutes)
                    if p1.inverse == p2.label or p2.inverse == p1.label:
                        conflicts.append({
                            "type": "inverse_conflict",
                            "source": u, "target": v,
                             "relations": [d1["original_relation"], d2["original_relation"]],
                             "severity": "critical"
                        })

        return conflicts

    # ------------------------------------------------------------------
    # 2. Gap Analysis (Negative Evidence)
    # ------------------------------------------------------------------
    def _detect_gaps(self) -> List[Dict]:
        """
        Identify 'Missing Links' - concepts that SHOULD be connected but aren't.
        Heuristic: High centrality concepts in the same cluster with 0 direct edges.
        """
        gaps = []
        try:
            # Undirected view for clustering
            U = self.G.to_undirected()
            communities = list(nx.community.louvain_communities(U)) if len(self.G) > 5 else []
            
            # Identify high degree nodes (Hubs)
            degrees = dict(self.G.degree())
            top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:10]
            
            # Check disjoint hubs
            for i in range(len(top_nodes)):
                for j in range(i + 1, len(top_nodes)):
                    u, v = top_nodes[i], top_nodes[j]
                    
                    # If no edge exists
                    if not self.G.has_edge(u, v) and not self.G.has_edge(v, u):
                        # But they share neighbors? (Bibliographic Coupling)
                        commons = list(nx.common_neighbors(U, u, v))
                        if len(commons) > 1:
                            gaps.append({
                                "source": u,
                                "target": v,
                                "reason": f"Shared context ({len(commons)} common neighbors) but no direct link.",
                                "type": "structural_gap"
                            })
        except Exception as e:
            logger.warning(f"Gap analysis failed: {e}")
            
        return gaps

    # ------------------------------------------------------------------
    # 3. Novelty Scoring
    # ------------------------------------------------------------------
    def _score_novelty(self) -> List[Dict]:
        """
        Rank edges by 'Novelty'.
        Novelty ≈ (1 - retrieval_frequency) * betweenness_centrality * confidence
        """
        novelty_scores = []
        try:
            betweenness = nx.edge_betweenness_centrality(self.G)
            
            for (u, v), score in betweenness.items():
                data = self.G.get_edge_data(u, v)
                if not data: continue
                
                # Failure Guard: Don't score hypotheses as "Novel Insights" (too risky)
                if data.get("is_hypothesis"): continue
                
                # Prior frequency proxy (paper_count)
                # If an edge appears in MANY papers, it's NOT novel (it's established fact)
                # If it appears in FEW papers but bridges clusters, it's NOVEL.
                evidence_count = data.get("evidence_count", 1)
                rarity = 1.0 / (evidence_count + 1) # Simple inverse frequency
                
                novelty = score * rarity * data.get("confidence", 0.5) * 100
                
                if novelty > 0.01:
                    novelty_scores.append({
                        "source": u, "target": v,
                        "relation": data.get("relation"),
                        "score": round(novelty, 4),
                        "reason": "High bridging centrality with low literature volume"
                    })
            
            novelty_scores.sort(key=lambda x: x["score"], reverse=True)
            
        except Exception as e:
             logger.warning(f"Novelty scoring failed: {e}")
             
        return novelty_scores[:5] # Top 5 Insights

    # ------------------------------------------------------------------
    # 4. Bias Metrics
    # ------------------------------------------------------------------
    def _analyze_bias(self) -> Dict:
        """
        Analyze corpus coverage limitations.
        """
        # This requires access to paper metadata which might be sparse in graph
        # For now, return placeholders or rely on graph node 'type' distribution
        types = {}
        for n, d in self.G.nodes(data=True):
            t = d.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
            
        return {"node_type_distribution": types}
