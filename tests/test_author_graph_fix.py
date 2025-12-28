
import logging
import json
from services.author_graph_service import build_author_graph

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_author_graph():
    print("--- Testing Build Author Graph ---")
    
    # INPUT DATA
    papers = [
        {
            "canonical_id": "p1",
            "title": "Paper One",
            "authors": ["Alice", "Bob"]
        },
        {
            "canonical_id": "p2",
            "title": "Paper Two",
            "authors": ["Bob", "Charlie"]
        },
        {
            "canonical_id": "p3",
            "title": "Paper Three",
            "authors": ["Alice", "David", "Bob"]
        },
        {
            "canonical_id": "p4",
            "title": "Paper Four - Isolated",
            "authors": ["Eve"]
        }
    ]

    # EXECUTE
    result = build_author_graph(papers)
    
    # VERIFY
    nodes = result.get("nodes", [])
    links = result.get("links", [])
    meta = result.get("meta", {})
    
    print(f"\nNodes count: {len(nodes)}")
    print(f"Links count: {len(links)}")
    print("Meta:", json.dumps(meta, indent=2))
    
    # Check Specifics
    # Alice and Bob co-authored p1 and p3. Weight should be 2.
    ab_link = next((l for l in links if (l['source'] == 'Alice' and l['target'] == 'Bob') or (l['source'] == 'Bob' and l['target'] == 'Alice')), None)
    
    if ab_link:
        print(f"\nSUCCESS: Link found between Alice and Bob. Weight: {ab_link.get('weight')}")
        print(f"Shared Papers: {ab_link.get('shared_papers')}")
        assert ab_link.get('weight') == 2
        assert set(ab_link.get('shared_papers')) == {'p1', 'p3'}
    else:
        print("\nFAILURE: No link between Alice and Bob!")

    # Check Influence
    print("\nInfluence Scores:")
    for n in nodes:
        print(f"{n['id']}: {n.get('influence_score')} (Papers: {n.get('paper_count')})")
        
    print("\nTest completed.")

if __name__ == "__main__":
    test_author_graph()
