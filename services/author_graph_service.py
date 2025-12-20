# services/author_graph_service.py
import networkx as nx
from networkx.readwrite import json_graph
from typing import List, Dict, Any

def build_author_graph(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a co-authorship graph from a list of papers.
    Phase 3.1 Enhanced: Dominance & Diversity.
    """
    G = nx.Graph()

    for paper in papers:
        raw_authors = paper.get("authors", [])
        
        # Normalize authors: Strip whitespace, maybe lowercase for ID but keep label
        # Simple normalization: Title Case
        authors = []
        for a in raw_authors:
            if isinstance(a, str):
                name = a.strip().title()
                if name:  # Skip empty names
                    authors.append(name)
            elif isinstance(a, dict) and "name" in a:
                name = a["name"].strip().title()
                if name:
                    authors.append(name)
        
        # Add nodes
        for author in authors:
            if not G.has_node(author):
                G.add_node(author, type="author", paper_count=0)
            
            G.nodes[author]["paper_count"] += 1

        # Add edges
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                u, v = authors[i], authors[j]
    # Calculate Metrics & Influence
    if len(G) > 0:
        degree_centrality = nx.degree_centrality(G)
        
        # Dominance: paper_count / total_input_papers
        total_input_papers = len(papers)        # Actually, let's normalize by finding the max paper count in graph as a proxy for "most prolific = dominant".
        
        # Refined Dominance: paper_count / number_of_input_papers
        # We passed 'papers' list. so we know len(papers).
        total_input_papers = len(papers)
        
        dominance_values = []
        
        for node in G.nodes():
            dc = degree_centrality[node]
            pc = G.nodes[node]["paper_count"]
            
            G.nodes[node]["degree_centrality"] = dc
            G.nodes[node]["influence_score"] = pc * dc
            
            # Dominance
            dom = 0.0
            if total_input_papers > 0:
                dom = pc / total_input_papers
            G.nodes[node]["dominance"] = round(dom, 2)
            dominance_values.append(dom)

        # Graph-Level Diversity Index
        # 1 - max(dominance)
        # If someone authored 100% of papers, diversity = 0.
        max_dom = max(dominance_values) if dominance_values else 0
        diversity_index = round(1.0 - max_dom, 2)
        
        # Attach to Graph attributes (networkx graph attr)
        G.graph["diversity_index"] = diversity_index
        G.graph["total_authors"] = len(G.nodes)

    data = json_graph.node_link_data(G)
    data["graph"] = G.graph # Explicitly attach graph-level attributes
    return data
