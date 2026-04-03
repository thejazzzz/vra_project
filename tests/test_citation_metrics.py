import pytest
import networkx as nx
import math
import sys
import os

from services.graph_service import (
    compute_betweenness,
    compute_communities,
    compute_age_normalized,
    compute_entropy,
    compute_velocity,
    compute_citation_metrics,
    compute_co_citation_and_coupling
)

def test_betweenness_nonzero():
    # Create a star graph which has high betweenness for the center
    G = nx.DiGraph()
    G.add_edges_from([("A", "B"), ("C", "B"), ("D", "B"), ("B", "E")])
    
    betweenness = compute_betweenness(G)
    
    assert "B" in betweenness
    assert betweenness["B"] > 0
    # Center node B should have higher betweenness than others
    assert betweenness["B"] > betweenness["A"]

def test_community_partitioning():
    # Create two disjoint clusters joined by one edge
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "B"), ("B", "C"), ("C", "A"), # Cluster 1
        ("D", "E"), ("E", "F"), ("F", "D"), # Cluster 2
        ("C", "D") # Bridge
    ])
    
    communities = compute_communities(G)
    
    # A, B, C should likely be in one community
    assert communities["A"] == communities["B"]
    assert communities["B"] == communities["C"]
    
    # D, E, F should likely be in another
    assert communities["D"] == communities["E"]
    assert communities["E"] == communities["F"]
    
    # The two clusters should be different
    assert communities["C"] != communities["D"]

def test_age_normalization_decreases_old_bias():
    G = nx.DiGraph()
    G.add_node("Old_Paper", year=2000, citation_count=100)
    G.add_node("New_Paper", year=2024, citation_count=100)
    
    pagerank = {"Old_Paper": 0.5, "New_Paper": 0.5}
    current_year = 2025
    
    compute_age_normalized(G, pagerank, current_year)
    
    old_score = G.nodes["Old_Paper"].get("age_normalized_influence", 0)
    new_score = G.nodes["New_Paper"].get("age_normalized_influence", 0)
    
    # Old paper's score should be significantly reduced compared to new paper
    assert new_score > old_score
    
    # Specifically, old age = 2025-2000=25. ln(26) = 3.25
    # New age = 2025-2024=1. ln(2) = 0.69
    assert math.isclose(old_score, 0.5 / math.log(26), rel_tol=1e-3)
    assert math.isclose(new_score, 0.5 / math.log(2), rel_tol=1e-3)

def test_entropy_range():
    G = nx.DiGraph()
    # Paper A cites papers from 1 community (Low entropy)
    G.add_edges_from([("A", "B"), ("A", "C")])
    G.nodes["B"]["community"] = 1
    G.nodes["C"]["community"] = 1
    
    # Paper X cites papers from 2 different communities (Higher entropy)
    G.add_edges_from([("X", "Y"), ("X", "Z")])
    G.nodes["Y"]["community"] = 1
    G.nodes["Z"]["community"] = 2
    
    compute_entropy(G)
    
    entropy_a = G.nodes["A"].get("citation_entropy", -1)
    entropy_x = G.nodes["X"].get("citation_entropy", -1)
    
    assert math.isclose(entropy_a, 0.0, abs_tol=1e-9)  # Only 1 community, entropy is zero    assert entropy_x > 0.0  # Distributed across communities
    
    # Max entropy for 2 classes is - (0.5*ln(0.5) + 0.5*ln(0.5)) = ln(2) ~ 0.693
    assert math.isclose(entropy_x, math.log(2), rel_tol=1e-3)
    
    # Check bounds 0 <= entropy <= log(k)
    assert 0 <= entropy_x <= math.log(2)

def test_velocity():
    G = nx.DiGraph()
    G.add_node("P1", year=2020, citation_count=100)
    G.add_node("P2", year=2024, citation_count=20)
    
    current_year = 2025
    compute_velocity(G, current_year)
    
    v1 = G.nodes["P1"].get("citation_velocity", 0)
    v2 = G.nodes["P2"].get("citation_velocity", 0)
    
    # P1 age = 5, v = 100/5 = 20
    # P2 age = 1, v = 20/1 = 20
    assert v1 == 20.0
    assert v2 == 20.0

def test_velocity_missing_year():
    G = nx.DiGraph()
    G.add_node("P1", citation_count=100) # missing year
    current_year = 2025
    compute_velocity(G, current_year)
    v1 = G.nodes["P1"].get("citation_velocity", -1)
    assert v1 == 0.0 # should set to 0.0 rather than inflate
    
def test_betweenness_deterministic():
    # Betweenness is evaluated via a sample of k=100;
    # on larger graphs, seed=42 forces this down a reproducible path.
    G = nx.erdos_renyi_graph(200, 0.05, directed=True, seed=42)
    b1 = compute_betweenness(G)
    b2 = compute_betweenness(G)
    
    # Must perfectly match run-to-run with a fixed seed inside the target
    assert b1 == b2


def test_hits_computation():
    G = nx.DiGraph()
    # Hub points to many authorities
    G.add_edges_from([("Hub1", "Auth1"), ("Hub1", "Auth2"), ("Hub2", "Auth1")])
    # Give all nodes required attributes so compute_citation_metrics won't fail
    for n in G.nodes:
        G.nodes[n]["year"] = 2024
        G.nodes[n]["citation_count"] = 10
        
    compute_citation_metrics(G, 2025)
    
    # Hub1 should have a higher hub score than Hub2
    assert G.nodes["Hub1"].get("hub_score", 0) > G.nodes["Hub2"].get("hub_score", 0)
    # Auth1 should have a higher authority score than Auth2
    assert G.nodes["Auth1"].get("authority_score", 0) > G.nodes["Auth2"].get("authority_score", 0)


def test_co_citation_and_coupling():
    G = nx.DiGraph()
    # A and B co-cited by C1
    G.add_edges_from([("C1", "A"), ("C1", "B")])
    # X and Y bib-coupled by citing Z
    G.add_edges_from([("X", "Z"), ("Y", "Z")])
    
    compute_co_citation_and_coupling(G)
    
    assert G.has_edge("A", "B")
    assert G.get_edge_data("A", "B").get("type") == "co_citation"
    assert G.get_edge_data("A", "B").get("weight") == 1
    
    assert G.has_edge("X", "Y")
    assert G.get_edge_data("X", "Y").get("type") == "bibliographic_coupling"
    assert G.get_edge_data("X", "Y").get("weight") == 1
