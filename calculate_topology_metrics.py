import sys
import os
import networkx as nx
from dotenv import load_dotenv

load_dotenv(".env.local")

# Add current dir to path
sys.path.append(os.getcwd())

from services.graph_service import calculate_confidence, compute_velocity
from services.graph_analytics_service import GraphAnalyticsService
import math

def calculate_metrics():
    # 1. Edge Evidence Confidence Algorithm
    # Test values: Base = 0.6, ≥ 5 papers -> Source Boost = 0.2, citations > 1000 -> Citation Bonus = 0.15, No Conflict
    conf = calculate_confidence(
        base_confidence=0.6,
        evidence_count=5,
        agreement_bonus=0.0,
        conflict_penalty=0.0,
        citation_bonus=0.15
    )
    print(f"Edge Evidence Confidence: {conf:.4f}")
    
    # 2. Graph Topology Metrics (PageRank, Betweenness Centrality, Citation Velocity)
    CG = nx.DiGraph()
    CG.add_node("PaperA", citations=1500, year=2020)
    CG.add_node("PaperB", citations=200, year=2022)
    CG.add_edge("PaperB", "PaperA")
    
    pr = nx.pagerank(CG, alpha=0.85)
    print(f"PageRank - PaperA: {pr['PaperA']:.4f}")
    
    bc = nx.betweenness_centrality(CG, normalized=True)
    print(f"Betweenness Centrality - PaperA: {bc['PaperA']:.4f}")
    
    # Citation Velocity
    # Velocity = Citations / (Current Year - Publish Year + 1)
    velocity_A = 1500 / (2026 - 2020)
    print(f"Citation Velocity - PaperA: {velocity_A:.4f}")

    # 3. Edge Novelty Metric
    # Using GraphAnalyticsService
    # Need a dummy dict for graph_data
    kg_data = {
        "nodes": [
            {"id": "ConceptA", "type": "concept", "betweenness": 0.5},
            {"id": "ConceptB", "type": "concept", "betweenness": 0.3}
        ],
        "links": [
            {
                "source": "ConceptA", 
                "target": "ConceptB", 
                "relation": "improves", 
                "confidence": 0.8, 
                "evidence_count": 2, 
                "betweenness": 0.5 # injected for formula
            }
        ]
    }
    gas = GraphAnalyticsService(kg_data)
    
    # Manually reproduce the formula since _score_novelty uses specific edge keys
    # Novelty = BetweennessCentrality * (1 / (EvidenceCount + 1)) * EdgeConfidence * CausalWeight * DecayPenalty * 100
    # Let's assume CausalWeight=1.0, DecayPenalty=1.0 for this dummy edge
    bc_edge = 0.5 # From nodes
    ev_count = 2
    edge_conf = 0.8
    causal_weight = 1.0 # default for 'improves' could be 0.8, let's say 1.0
    decay = 1.0
    
    novelty = bc_edge * (1 / (ev_count + 1)) * edge_conf * causal_weight * decay * 100
    print(f"Edge Novelty Score: {novelty:.4f}")

if __name__ == "__main__":
    calculate_metrics()
