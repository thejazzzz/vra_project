#agents/gap_analysis_agent.py
import logging
import networkx as nx
from typing import Dict, List, Any
from services.graph_service import enrich_knowledge_graph

logger = logging.getLogger(__name__)

class GapAnalysisAgent:
    """
    Analyzes the Knowledge Graph to identify research gaps (structural holes, 
    isolated subgraphs, or missing links between major concepts).
    """
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🔍 Gap Analysis: Scanning for research opportunities...")
        
        kg_data = state.get("knowledge_graph")
        if not kg_data:
            logger.warning("No knowledge graph found. Skipping gap analysis.")
            return state

        try:
            # Convert to NetworkX for analysis
            G = nx.node_link_graph(kg_data)
        except Exception as e:
            logger.error(f"Failed to parse KG for gap analysis: {e}")
            return state
        
        gaps = []
        
        # --------------------------------------------------------
        # Heuristic 1: Under-explored Concepts (Low Degree)
        # --------------------------------------------------------
        # Nodes with low degree (few connections) might be under-researched
        # or just peripheral. We filter for 'concept' type to be more specific.
        low_degree_nodes = []
        for n, d in G.degree():
            node_data = G.nodes[n]
            if node_data.get("type") == "concept" and d <= 1:
                low_degree_nodes.append(n)
        
        if low_degree_nodes:
            # Sort by name for consistency
            low_degree_nodes.sort()
            gaps.append({
                "type": "under_explored_concepts",
                "description": "These concepts have few connections in the current graph, suggesting they might be under-utilized or niche.",
                "items": low_degree_nodes[:10] 
            })
            
        # --------------------------------------------------------
        # Heuristic 2: Disconnected Domains (Components)
        # --------------------------------------------------------
        # If the graph is fragmented, we have isolated fields of study.
        if not nx.is_weakly_connected(G):
            components = list(nx.weakly_connected_components(G))
            # Filter for non-trivial components (size >= 2) to avoid noise
            significant_components = [c for c in components if len(c) >= 2]
            
            if len(significant_components) > 1:
                gaps.append({
                    "type": "disconnected_domains",
                    "description": "The research landscape is fragmented into disjoint clusters. Connecting these distinct areas could yield novel insights.",
                    "count": len(significant_components)
                })

        # --------------------------------------------------------
        # Heuristic 3: High Centrality but No Direct Link
        # --------------------------------------------------------
        # (Optional for later: Find top 2 metrics leaders that are NOT connected)

        # Save gaps to state
        state["research_gaps"] = gaps
        
        if gaps:
            logger.info(f"✅ Gap Analysis: Found {len(gaps)} categories of potential gaps.")
            for gap in gaps:
                logger.info(f"   - {gap['type']}: {gap.get('count') or len(gap.get('items', []))} items")
        else:
            logger.info("Gap Analysis: No obvious structural gaps found.")

        return state

gap_analysis_agent = GapAnalysisAgent()
