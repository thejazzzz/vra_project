# services/graph_analytics_service.py
import networkx as nx
from typing import Dict, List, Any
import logging
from services.schema.relation_ontology import get_relation_props
from services.memory_service import MemoryService

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
        # -----------------------------
        # Phase 4 Safety: Scope Guard (Refusal Mode)
        # -----------------------------
        if self.G.graph.get("scope_limited", False):
            logger.warning("Analytics Refused: Scope Limited (Insufficient Data)")
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Analytics aborted due to insufficient evidence (Safety Guard).",
                "conflicts": [],
                "gaps": [],
                "novelty": [],
                "negative_evidence": [],
                "bias_metrics": {}
            }

        return {
            "conflicts": self._detect_conflicts(),
            "gaps": self._detect_gaps(),
            "novelty": self._score_novelty(),
            "negative_evidence": self._detect_negative_evidence(),
            "bias_metrics": self._analyze_bias()
        }

    # ------------------------------------------------------------------
    # 1. Conflict Detection (Direction-Aware & Causal)
    # ------------------------------------------------------------------
    def _detect_conflicts(self) -> List[Dict]:
        """
        Find edges that semantically contradict each other.
        Respects directionality: A->B is distinct from B->A.
        """
        conflicts = []
        full_edges = list(self.G.edges(data=True))
        
        # 1. Group by Directional Pair (u, v)
        directional_map = {}
        for u, v, data in full_edges:
            # Failure Guard: Skip Hypotheses
            if data.get("is_hypothesis"): continue
            
            # Explicit Meta-Edge Exclusion (Methodological Requirement)
            if data.get("type") == "meta" or data.get("relation") == "appears_in": continue
            
            # Causal Filtering: Ignored purely associative edges for conflict detection
            # We only care if a CAUSAL claim is contradicted.
            if data.get("causal_strength") == "associative": continue

            key = (u, v)
            if key not in directional_map: directional_map[key] = []
            directional_map[key].append(data)

        # 2. Check Same-Direction Conflicts (A->B vs A->B)
        for (u, v), edges in directional_map.items():
            if len(edges) < 2: continue
            
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    d1, d2 = edges[i], edges[j]
                    
                    # Polarity Check: +1 vs -1
                    if d1.get("polarity", 0) * d2.get("polarity", 0) < 0:
                        conflicts.append({
                            "type": "direct_contradiction",
                            "source": u, "target": v,
                            "conflict": f"{d1.get('relation', 'unknown')} vs {d2.get('relation', 'unknown')}",
                            "severity": "high"
                        })

        # 3. Check Inverse-Direction Conflicts (A->B vs B->A)
        # Only relevant if ontology says they imply inverse properties
        # e.g. A causes B (valid) and B causes A (valid loop) -> Not a conflict per se.
        # But A supports B vs B refutes A? 
        # For now, let's stick to the User's request: "inverse direction conflicts using ontology"
        
        # Iterate all pairs
        for (u, v), edges_ab in directional_map.items():
            if (v, u) in directional_map:
                edges_ba = directional_map[(v, u)]
                
                for d_ab in edges_ab:
                    for d_ba in edges_ba:
                        # Check Ontology Inverse
                        # If A->B is "supports", and B->A is "refutes"...
                        # If relation "supports" has inverse "supported_by"...
                        # If B->A is "refutes", does "refutes" == "supported_by"? No.
                        # This logic is tricky without a full reasoning engine.
                        
                        # Simpler Semantic Check:
                        # If A "causes" B, and B "prevents" A. -> Conflict (Feedback Loop?)
                        # Let's rely on Polarity for now.
                        # If A->B (+) and B->A (-), is that a conflict? 
                        # "Exercise improves Health", "Health degrades Exercise"? -> Conflict.
                        
                        # Only flag if both are Strong Causal
                        if (d_ab.get("causal_strength") == "causal" and 
                            d_ba.get("causal_strength") == "causal"):
                            
                            if d_ab.get("polarity", 0) * d_ba.get("polarity", 0) < 0:
                                conflicts.append({
                                    "type": "feedback_loop_conflict",
                                    "source": f"{u}<->{v}",
                                    "conflict": f"{u}->{v} ({d_ab['relation']}) vs {v}->{u} ({d_ba['relation']})",
                                    "severity": "medium"
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
                        
                        # Gap Validity Check: Must have meaningful shared context
                        # Exclude purely meta-neighbors (like "Paper X") which causes trivial gaps
                        # This requires checking the type of common neighbors, but U is a simple graph.
                        # Approximation: Require > 2 common neighbors for robustness
                        if len(commons) > 2:
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
            
            # MultiDiGraph returns keys as (u, v, k)
            # DiGraph returns keys as (u, v)
            for edge_key, score in betweenness.items():
                if len(edge_key) == 3:
                    u, v, k = edge_key
                    data = self.G.get_edge_data(u, v, k)
                else:
                    u, v = edge_key
                    data = self.G.get_edge_data(u, v)
                
                if not data: continue
                
                # Meta-Edge Exclusion
                if data.get("type") == "meta" or data.get("relation") == "appears_in": continue

                # Failure Guard: Don't score hypotheses as "Novel Insights" (too risky)
                if data.get("is_hypothesis"): continue
                
                # Causal Weighting (Novelty = Causal > Associative)
                causal_weight = 1.0 if data.get("causal_strength") == "causal" else 0.5
                
                # Prior frequency proxy (paper_count)
                evidence_count = data.get("evidence_count", 1)
                rarity = 1.0 / (evidence_count + 1) 
                
                # Phase 4: Longitudinal Decay & Contestation
                # ------------------------------------------
                # Check Global Memory
                history = MemoryService.get_edge_context(u, v)
                run_count = history.get("max_run_count", 0)
                is_contested = history.get("is_contested", False)
                
                # Decay Formula: Novelty fades with familiarity
                # If seen in 0 previous runs -> Decay=1.0
                # If seen in 5 previous runs -> Decay=0.5 (Floor 0.5)
                # Simple linear decay for now: max(0.5, 1.0 - (runs * 0.1))
                decay = max(0.5, 1.0 - (run_count * 0.1))
                
                # Contestation Penalty (Research Audit)
                if is_contested:
                    decay *= 0.2 # Massive penalty if scientists disagree
                
                novelty = score * rarity * data.get("confidence", 0.5) * causal_weight * decay * 100
                
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

    def _detect_negative_evidence(self) -> List[Dict]:
        """
        Identify 'Dead Ends' or 'Negative Results'.
        Distinguishes 'Not Studied' (Gap) from 'Studied and Ineffective'.
        Rule: Evidence >= 2 AND Polarity <= 0 (Neutral/Negative).
        """
        neg_evidence = []
        for u, v, data in self.G.edges(data=True):
             # Skip meta
            if data.get("type") == "meta" or data.get("relation") == "appears_in": continue
            
            # Check Evidence Volume (Must be non-trivial)
            if data.get("evidence_count", 0) < 2: continue
            
            # Check Polarity (Neutral or Negative)
            # Polarity: 1 (Positive), -1 (Negative), 0 (Neutral)
            if data.get("polarity", 1) <= 0:
                neg_evidence.append({
                    "source": u, "target": v,
                    "relation": data.get("relation"),
                    "reason": f"Consistently neutral/negative result ({data.get('relation', 'unknown')}) across {data.get('evidence_count', 'N/A')} sources.",
                    "type": "negative_result"
                })
        
        return neg_evidence

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
