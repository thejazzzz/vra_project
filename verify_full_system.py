
import sys
import os
import json
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("SystemTest")

print("🚀 Starting VRA System-Wide Verification...")

# ----------------------------------------------------
# 0. Mock Persistence Service (Prevent Import Error)
# ----------------------------------------------------
# The persistence service fails on import if env vars are missing.
# We block it from importing real logic.
sys.modules["services.graph_persistence_service"] = MagicMock()

print("✅ Persistence Layer Mocked (Database credentials check bypassed).")

# ----------------------------------------------------
# 1. Setup Mock Data (Simulating Research Phase)
# ----------------------------------------------------
print("\n[1/5] Setting up State (Simulating Research Complete)...")

mock_papers = [
    {
        "canonical_id": "PAPER_1",
        "title": "Deep Learning for Graphs",
        "paper_id": "S2_1",
        "summary": "A survey on GNNs.",
        "metadata": {
            "paperId": "S2_1",
            "references": [{"paperId": "S2_2"}] # Paper 1 cites Paper 2
        }
    },
    {
        "canonical_id": "PAPER_2",
        "title": "Graph Convolutional Networks",
        "paper_id": "S2_2",
        "summary": "Introduction of GCN.",
        "metadata": {
            "paperId": "S2_2",
            "references": []
        }
    },
     {
        "canonical_id": "PAPER_3",
        "title": "Isolated Research Topic",
        "paper_id": "S2_3",
        "summary": "Something completely different.",
        "metadata": {
            "paperId": "S2_3",
            "references": []
        }
    }
]

state = {
    "query": "Explain Graph Neural Networks",
    "user_id": "test_user",
    "selected_papers": mock_papers,
    "current_step": "awaiting_analysis"
}
print("✅ State initialized with 3 papers.")


# ----------------------------------------------------
# 2. Simulate Analysis Phase (Mocking OpenAI)
# ----------------------------------------------------
print("\n[2/5] Running Analysis (Mocking LLM)...")

# Mock the structure returned by _call_openai_for_analysis
mock_analysis_result = {
    "summary": "GNNs are powerful.",
    "nodes": [
        {"id": "GNN", "type": "concept"},
        {"id": "GCN", "type": "method"},
        {"id": "Accuracy", "type": "metric"}
    ],
    "relations": [
        {
            "source": "GCN", 
            "target": "GNN", 
            "relation": "extends",
            "evidence": {"paper_id": "S2_2", "excerpt": "GCN extends GNNs."}
        },
        {
            "source": "GCN",
            "target": "Accuracy",
            "relation": "improves"
        }
    ],
    "key_concepts": ["GNN", "GCN"] # Backwards compat
}

# Apply mock to the state directly to simulate the Analysis Service success
state["global_analysis"] = mock_analysis_result
state["current_step"] = "awaiting_graphs"
print("✅ Analysis Data Injected (Level 1: Typed Nodes, Level 2: Evidence included).")


# ----------------------------------------------------
# 3. Run Graph Builder (Real Logic)
# ----------------------------------------------------
print("\n[3/5] Running Graph Builder Agent...")

from agents.graph_builder_agent import graph_builder_agent
from services.graph_service import enrich_knowledge_graph

# Execute Agent (Persistence is already mocked via sys.modules above)
state = graph_builder_agent.run(state)

# Verify KG
kg = state["knowledge_graph"]
print(f"   -> KG Nodes: {len(kg['nodes'])}")
print(f"   -> KG Links: {len(kg['links'])}")

# Check Level 1 (Types)
gcn_node = next(n for n in kg['nodes'] if n['id'] == "GCN")
assert gcn_node.get("type") == "method", "Level 1 Fail: Node type missing"

# Check Level 2 (Evidence)
gcn_gnn_link = next(l for l in kg['links'] if l['source'] == "GCN" and l['target'] == "GNN")
assert gcn_gnn_link.get("evidence"), "Level 2 Fail: Evidence missing on edge"
assert gcn_gnn_link["evidence"]["paper_id"] == "S2_2", "Level 2 Fail: Evidence mismatch"

# Check Level 3 (Cross-Graph Enrichment / Citiation Graph)
cg = state["citation_graph"]
print(f"   -> CG Nodes: {len(cg['nodes'])}")

p2_node = next(n for n in cg['nodes'] if n['id'] == "PAPER_2")
c_link = next((l for l in cg['links'] if l['source'] == "PAPER_1" and l['target'] == "PAPER_2"), None)
assert c_link, "Citation Graph Fail: Missing citation edge"

print("✅ Graph Builder Verified (Levels 1, 2, 3).")


# ----------------------------------------------------
# 4. Run Gap Analysis (Real Logic)
# ----------------------------------------------------
print("\n[4/5] Running Gap Analysis Agent (Level 4)...")
from agents.gap_analysis_agent import gap_analysis_agent

state = gap_analysis_agent.run(state)
gaps = state.get("research_gaps", [])

print(f"   -> Found {len(gaps)} Gap Categories.")
gap_types = [g["type"] for g in gaps]
print(f"   -> Types: {gap_types}")

# Should find 'under_explored_concepts' 
assert "under_explored_concepts" in gap_types, "Level 4 Fail: Missed under-explored concepts"

print("✅ Gap Analysis Verified.")


# ----------------------------------------------------
# 5. Run Reporting Agent (Real Logic, Mock LLM)
# ----------------------------------------------------
print("\n[5/5] Running Reporting Agent...")
from agents.reporting_agent import reporting_agent

# Mock the generate_report_content function to avoid OpenAI
with patch("agents.reporting_agent.generate_report_content") as mock_gen:
    mock_gen.return_value = "# Final Report\n\nExisting Gaps: ...\n\nReference: Paper 1"
    
    state = reporting_agent.run(state)
    
    report = state.get("draft_report")
    assert report, "Reporting Fail: No report generated"
    assert "Final Report" in report
    
    # Verify call args contained paper info
    call_args = mock_gen.call_args[0][0]
    assert "Deep Learning for Graphs" in call_args, "Reporting Fail: Prompt missing paper titles"
    assert "S2_1" in call_args, "Reporting Fail: Prompt missing paper IDs"

print("✅ Reporting Agent Verified.")

print("\n🎉 ALL SYSTEMS FUNCTIONAL! Phase 1 & 2 Integration Test Passed.")
