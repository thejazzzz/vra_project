# services/author_graph_service.py
import networkx as nx
from networkx.readwrite import json_graph
from typing import List, Dict, Any
from collections import defaultdict
from itertools import combinations
import logging

logger = logging.getLogger(__name__)

def build_author_graph(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a co-authorship graph from a list of papers.
    Includes Phase 3.1 Enhanced Metrics: Dominance, Diversity, and proper edge construction.
    Results include a 'meta' field for data integrity signals.
    """
    G = nx.Graph()
    
    # 1. Build Index: Author -> Set of Paper IDs
    author_to_papers = defaultdict(set)
    # Track paper details for edge attributes (id -> title/source) - optional but useful for edge expansion
    # For now, just storing IDs is sufficient for the requirement.
    
    # Safe extraction of author lists
    valid_papers_count = 0
    
    for paper in papers:
        raw_authors = paper.get("authors", [])
        # Require canonical_id or id to prevent title collisions
        p_id = paper.get("canonical_id") or paper.get("id")

        if not p_id or not raw_authors:
            # Skip papers without valid robust IDs
            continue
            
        valid_papers_count += 1
        
        # Normalize authors
        normalized_authors = set()
        for a in raw_authors:
            name = None
            if isinstance(a, str):
                name = a.strip().title()
            elif isinstance(a, dict) and "name" in a:
                name = a["name"].strip().title()
            
            if name:
                normalized_authors.add(name)
        
        # Add to index and graph nodes
        for author in normalized_authors:
            author_to_papers[author].add(p_id)
            if not G.has_node(author):
                G.add_node(author, type="author", paper_count=0)
            
    # 2. Populate Nodes with basic counts
    # We do this from the index to ensure consistency
    for author, p_ids in author_to_papers.items():
        if G.has_node(author):
            G.nodes[author]["paper_count"] = len(p_ids)

    # 3. Build Edges from Index
    # Iterate over all pairs of authors
    # If using combinations on all authors, it's O(N^2). 
    # Better: iterate papers? No, standard co-authorship is clique expansion per paper.
    # But since we built the index, we can just iterate combinations of authors *who have shared papers*? 
    # Actually, iterating papers and adding cliques is faster for sparse graphs.
    # Let's stick to the robust plan: Iterate combinations of keys if N is small, 
    # OR iterate papers and form cliques.
    # Given typical research session size (20-50 papers), clique expansion is fine.
    
    # Let's use the Paper -> Authors mapping implicitly.
    # Re-iterate papers to form cliques (it's properly robust for multi-edge weighting).
    
    # reset mapping for clique iteration to ensure we use same normalization
    # Actually, let's use the sets from step 1 to verify.
    
    edge_weights = defaultdict(int)
    edge_shared_papers = defaultdict(set)
    
    for author_a, papers_a in author_to_papers.items():
        for author_b, papers_b in author_to_papers.items():
            if author_a >= author_b: continue # Avoid duplicates and self-loops
            
            shared = papers_a.intersection(papers_b)
            if shared:
                G.add_edge(
                    author_a, 
                    author_b, 
                    weight=len(shared),
                    shared_papers=list(shared)
                )

    # 4. Calculate Metrics & Influence
    # Default values
    diversity_index = 0.0
    
    if len(G) > 0:
        # Degree Centrality (based on connection structure)
        # Verify we have edges before trusting centrality fully? 
        # nx.degree_centrality works on disconnected graphs too (it's local).
        degree_centrality = nx.degree_centrality(G)
        
        # Weighted Degree (strength)
        weighted_degree = dict(G.degree(weight="weight"))
        
        total_input_papers = valid_papers_count
        dominance_values = []
        
        for node in G.nodes():
            dc = degree_centrality.get(node, 0.0)
            pc = G.nodes[node]["paper_count"]
            wd = weighted_degree.get(node, 0.0)
            
            G.nodes[node]["degree_centrality"] = dc
            
            # Influence Score: Composite of volume (paper_count) and centrality
            # Previous: pc * dc. 
            # Improvement: if edges exist, use weighted degree + pc? 
            # Let's keep it simple and comparable to before, but actual numbers now.
            # If graph is disconnected (no edges), dc is 0. 
            # So influence becomes 0 which is what user observed.
            # Fallback: if no edges, influence = paper_count (normalized)?
            
            if G.number_of_edges() > 0:
                # Influence Score: Volume (paper_count) boosted by Centrality (degree_centrality)
                # Formula: score = pc * (1 + dc)
                score = pc * (1.0 + dc)
            else:
                score = pc * 0.1 # Just volume based, heavily discounted if isolated
            
            G.nodes[node]["influence_score"] = round(score, 3)
            
            # Dominance
            dom = 0.0
            if total_input_papers > 0:
                dom = pc / total_input_papers
            G.nodes[node]["dominance"] = round(dom, 2)
            dominance_values.append(dom)

        # Graph-Level Diversity Index
        max_dom = max(dominance_values) if dominance_values else 0
        diversity_index = round(1.0 - max_dom, 2)
    
    # Attach Graph Attributes
    G.graph["diversity_index"] = diversity_index
    G.graph["total_authors"] = len(G.nodes)
    
    # 5. Construct Final Response with Metadata (Phase 0 Requirement)
    data = json_graph.node_link_data(G)
    
    # Ensure backward compatibility structure
    if "links" not in data:
        data["links"] = []
    
    num_edges = G.number_of_edges()
    
    data["meta"] = {
        "edges_present": num_edges > 0,
        "collaboration_mode": "basic",
        # Metrics are only scientifically valid if we have >1 paper (edges possible) and actual edges exist
        "metrics_valid": num_edges > 0 and valid_papers_count >= 2,
        "influence_model": "pc*(1.0+dc)",
        "warning": None if num_edges > 0 else "Insufficient collaboration data for centrality metrics",
        "total_papers_analyzed": valid_papers_count
    }
    
    # Explicitly attach graph-level attributes to the root or inside 'graph' key 
    # depending on what frontend expects. nx usually puts them in data['graph'].
    # We also put them in meta for easier access if needed.
    data["meta"]["diversity_index"] = diversity_index

    return data
