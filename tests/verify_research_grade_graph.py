# tests/verify_research_grade_graph.py
import sys
import os
from dotenv import load_dotenv
load_dotenv(".env.local")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.graph_service import build_knowledge_graph
from services.graph_analytics_service import GraphAnalyticsService
import json

def test_pipeline():
    print("Starting Research-Grade Pipeline Verification...\n")

    # 1. Mock Data with Intentional Issues
    # -----------------------------------
    paper_relations = {
        "P1": [
            {"source": "Exercise", "target": "Health", "relation": "improves", "evidence": {"excerpt": "Exercise significantly improves CV health."}},
        ],
        "P2": [
            {"source": "exercise", "target": "Health", "relation": "improves", "evidence": {"excerpt": "Daily exercise improves health."}},
            # Contradiction to P1/P2 in P3
        ],
        "P3": [
            {"source": "Excessive Exercise", "target": "Health", "relation": "degrades", "evidence": {"excerpt": "Too much exercise degrades joints."}},
            # This is not a direct contradiction to "Exercise", but let's force one for testing
            {"source": "Exercise", "target": "Health", "relation": "degrades", "evidence": {"excerpt": "Exercise can degrade health if improper."}}, 
        ],
        "P4": [
            # Gap Candidate Data Construction
            # We need Diet and Exercise to share > 2 neighbors to be a "Structural Gap"
            # Exercise is linked to Health (P1)
            
            # 1. Link Diet to Health (Shared Neighbor 1)
            {"source": "Diet", "target": "Health", "relation": "improves"}, 
            
            # 2. Key: Add common neighbors for both
            {"source": "Diet", "target": "Longevity", "relation": "improves"}, 
            {"source": "Exercise", "target": "Longevity", "relation": "increases"}, # Shared 2
            
            {"source": "Diet", "target": "Mental Clarity", "relation": "boosts"},
            {"source": "Exercise", "target": "Mental Clarity", "relation": "boosts"}, # Shared 3
            
            # Now (Diet, Exercise) share Health, Longevity, Mental Clarity.
            # But no direct link between Diet and Exercise.
        ],
        "P5": [
            # Novelty Candidate: "Meditation" -> "Gene Expression" (Rare bridge)
            # Removed Health link to force Meditation -> Gene ... flows to be critical
            # {"source": "Meditation", "target": "Health", "relation": "improves"},
            {"source": "Meditation", "target": "Gene Expression", "relation": "modulates"}, # Rare
            
            # Make Gene Expression a Bridge to Metabolism to boost Betweenness
            {"source": "Gene Expression", "target": "Metabolism", "relation": "regulates"},
        ]
    }

    # 2. Build Graph (Verification Layer)
    # -----------------------------------
    print("--- Phase 1: Verification & Construction ---")
    
    # Mock Run Meta
    run_meta = {"run_id": "test-123", "model_version": "vTest"}
    
    # Mock Overrides (Priority 4)
    overrides = [
        {"source": "Human", "target": "Machine", "relation": "collaborates_with", "action": "add_edge"}
    ]
    
    kg = build_knowledge_graph(paper_relations=paper_relations, run_meta=run_meta, overrides=overrides)
    
    # Check Override (Add Edge)
    links = kg["links"]
    human_machine = [l for l in links if l["source"] == "human" and l["target"] == "machine"]
    print(f"Manual Edges (Human->Machine): {len(human_machine)}")
    assert len(human_machine) > 0, "Manual Override 'add_edge' failed"
    assert human_machine[0]["confidence"] == 1.0, "Manual Confidence not 1.0"
    print("Manual Override verified")

    # Check Provenance
    print(f"Graph Meta: {kg.get('graph', {}).get('meta')}")
    assert kg.get("graph", {}).get("meta", {}).get("run_id") == "test-123", "Run Provenance Missing"
    print("Provenance verified")
    
    # Check Canonicalization
    nodes = {n["id"] for n in kg["nodes"]}
    print(f"Nodes found: {sorted(list(nodes))}")
    assert "exercise" in nodes and "Exercise" not in nodes, "Canonicalization Failed"
    print("Canonicalization verified")

    # Check Confidence
    links = kg["links"]
    exercise_health = [l for l in links if l["source"] == "exercise" and l["target"] == "health"]
    print(f"Edges (Exercise->Health): {len(exercise_health)}")
    for l in exercise_health:
        print(f"  - Relation: {l.get('relation')} | Confidence: {l.get('confidence')}")

    # We should have aggregated the "improves" relation
    # Note: 'improves' might be normalized or the test data might have it differently?
    # In the mock data P1 and P2 use "improves".
    try:
        improves = [l for l in exercise_health if l["relation"] == "improves"][0]
        print(f"Confidence (Improves): {improves.get('confidence')} (Evidence: {improves.get('evidence_count')})")
    except IndexError:
        raise AssertionError("Could not find 'improves' edge. Check normalization or aggregation.")    
    # 3. Analyze Graph (Analytics Layer)
    # ----------------------------------
    print("\n--- Phase 2: Research Analytics ---")
    analytics = GraphAnalyticsService(kg).analyze()
    
    # Check Conflicts
    conflicts = analytics["conflicts"]
    print(f"Conflicts Found: {len(conflicts)}")
    for c in conflicts:
        print(f"  Warning {c['type']}: {c['source']}->{c['target']} [{c['severity']}]")
    # Verify the expected Exercise->Health contradiction is detected
    exercise_conflicts = [c for c in conflicts if c["source"] == "exercise" and c["target"] == "health"]
    assert len(exercise_conflicts) > 0, "Expected Exercise->Health conflict not detected"
    
    # Check Gaps
    gaps = analytics["gaps"]
    print(f"\nGaps Found: {len(gaps)}")
    for g in gaps:
        print(f"  Gap: {g['source']} <-> {g['target']} ({g['reason']})")
    assert len(gaps) > 0, "Expected gaps not detected"
        
    # Check Novelty
    novelty = analytics["novelty"]
    print(f"\nNovelty Insights: {len(novelty)}")
    for n in novelty:
        print(f"  Insight {n['source']}->{n['target']} ({n['relation']}) Score: {n['score']}")
    # Verify the Meditation->Gene Expression novelty is detected
    meditation_novelty = [n for n in novelty if n["source"] == "meditation" and n["target"] == "gene expression"]
    if len(meditation_novelty) == 0:
        print(f"Novelty Check Failed. Found items: {json.dumps(novelty, indent=2)}")
    assert len(meditation_novelty) > 0, "Expected Meditation->Gene Expression novelty not detected"

    print("\nVerification Complete.")

if __name__ == "__main__":
    test_pipeline()
