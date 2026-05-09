import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from agents.data_acquisition_agent import data_acquisition_agent
from services.graph_service import build_citation_graph

async def main():
    query = "attention is all you need"
    print(f"Running acquisition for: {query}")
    
    papers = await data_acquisition_agent.run(query, limit=2, expand_citations=True)
    
    print("\n--- RESULTS ---")
    print(f"Total merged papers: {len(papers)}")
    
    # Let's test the graph builder
    graph_data = build_citation_graph(papers)
    
    print("\n--- GRAPH DATA ---")
    print(f"Nodes: {len(graph_data.get('nodes', []))}")
    print(f"Edges: {len(graph_data.get('links', []))}")
    
    for n in graph_data.get('nodes', [])[:3]:
        print(f"Node: {n.get('id')} - Citations: {n.get('citation_count')} - Concepts: {n.get('concepts')}")
        
    for e in graph_data.get('links', [])[:3]:
        print(f"Edge: {e.get('source')} -> {e.get('target')} (Type: {e.get('type')})")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
