# verify_phase3.py
import sys
import os
import json
import logging
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())
sys.modules["services.graph_persistence_service"] = MagicMock()
sys.modules["openai"] = MagicMock()

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("🚀 Starting Phase 3.1 ENHANCED Verification...")

# ------------------------------------------------------------------
# Setup Mock State
# ------------------------------------------------------------------
mock_papers = [
    {"canonical_id": "P1", "title": "A", "year": "2021", "authors": ["Alice"]},
    {"canonical_id": "P2", "title": "B", "year": "2022", "authors": ["Alice", "Bob"]},
]
mock_concepts = {
    "P1": ["gnn"],          # pre-normalized
    "P2": ["gnn", "transformer"]
}
mock_kg = {
    "nodes": [{"id":"gnn", "type":"concept"}, {"id":"P1", "type":"paper"}],
    "links": [{"source":"gnn", "target":"P1"}],
    "directed": True,
    "graph": {}
}

state = {
    "query": "Test",
    "selected_papers": mock_papers,
    "paper_concepts": mock_concepts,
    "knowledge_graph": mock_kg,
    "citation_graph": {"nodes":[], "links":[]}
}

# ------------------------------------------------------------------
# Test 1: Knowledge Graph (Normalized Freq)
# ------------------------------------------------------------------
print("\n[1/6] Testing KG Normalization & Frequency...")
from services.graph_service import build_knowledge_graph
kg_data = build_knowledge_graph(paper_concepts=mock_concepts, global_analysis={"nodes":[]})

# Check if 'gnn' node has paper_frequency
gnn_node = next(n for n in kg_data["nodes"] if n["id"] == "gnn")
assert "paper_frequency" in gnn_node, "KG Fail: Missing paper_frequency"
# GNN is in P1 and P2 -> freq 2. Max is 2. Norm = 1.0.
assert gnn_node["paper_frequency"] == 2, f"Expected freq 2, got {gnn_node['paper_frequency']}"
assert gnn_node["paper_frequency_norm"] == 1.0
print("✅ KG Frequency Verified.")

# ------------------------------------------------------------------
# Test 2: Gap Analysis (Taxonomy & Rationale)
# ------------------------------------------------------------------
print("\n[2/6] Testing Gap Taxonomy...")
from agents.gap_analysis_agent import gap_analysis_agent
# Inject graph
state["knowledge_graph"] = kg_data
state = gap_analysis_agent.run(state)
gaps = state.get("research_gaps", [])

if gaps:
    first_gap = gaps[0]
    assert "gap_class" in first_gap, "Gap Fail: Missing gap_class"
    assert "rationale" in first_gap, "Gap Fail: Missing rationale"
    print(f"   -> Rationale: {first_gap['rationale']}")
    
    # High-Value Assertion: Explainability
    assert all("gap_id" in g and "rationale" in g for g in gaps), "Gap Fail: Not all gaps explainable"

print("✅ Gap Taxonomy Verified.")

# ------------------------------------------------------------------
# Test 3: Summarization (Retry/Reliability)
# ------------------------------------------------------------------
print("\n[3/6] Testing Summary Reliability & Retry...")
from agents.paper_summarization_agent import paper_summarization_agent
with patch("agents.paper_summarization_agent.generate_structured_json") as mock_json:
    # First call returns partial (simulate failure)
    # Second call returns success (retry works)
    # Actually, let's simulate total failure to check _status="error" logic?
    # Or simulate partial fallback.
    
    # Side effect: First call partial, Second call partial -> fallback status
    mock_json.side_effect = [
        {"problem": "Partial"}, # Missing keys
        {"problem": "Partial"}  # Retry fails too
    ]
    
    # Run heavily limited to avoid complex patching of multiple calls
    state["selected_papers"] = [mock_papers[0]] # Just P1
    state = paper_summarization_agent.run(state)
    
    summ = state["paper_structured_summaries"]["P1"]
    assert summ["_status"] == "partial_fallback", f"Status Fail: {summ.get('_status')}"
    assert "method" in summ, "Fallback Fail: Missing keys not filled"

print("✅ Summary Reliability Verified.")

# ------------------------------------------------------------------
# Test 4: Trend Analysis (Saturation)
# ------------------------------------------------------------------
print("\n[4/6] Testing Trend Saturation...")
# Reset concepts explicitly (fresh dict) to avoid pollution
state["paper_concepts"] = {
    "P1": ["gnn"],
    "P2": ["gnn", "transformer"]
}
# Restore papers (modified in Test 3)
state["selected_papers"] = mock_papers
from services.trend_analysis_service import detect_concept_trends

trends_result = detect_concept_trends(state["selected_papers"], state["paper_concepts"])
trends = trends_result["trends"]
gnn_trend = trends["gnn"]
print(f"DEBUG GNN TREND: {gnn_trend}")
# Robust float check
assert abs(gnn_trend["trend_confidence"] - 0.22) < 0.01, f"Trend Fail: Expected ~0.22, got {gnn_trend['trend_confidence']}"
print("✅ Trend Metrics Verified.")

# ------------------------------------------------------------------
# Test 5: Author Graph (Diversity)
# ------------------------------------------------------------------
print("\n[5/6] Testing Author Diversity...")
from services.author_graph_service import build_author_graph
# Alice (2 papers), Bob (1 paper). Total inputs = 2.
# Alice Dom = 2/2 = 1.0. 
# Diversity = 1 - 1.0 = 0.0. (Monopoly)
ag = build_author_graph(state["selected_papers"])
div_idx = ag["graph"].get("diversity_index")
print(f"DEBUG Diversity: {div_idx}")
assert abs(div_idx - 0.0) < 1e-6, f"Div Fail: {div_idx}"
print("✅ Author Diversity Verified.")

# ------------------------------------------------------------------
# Test 6: Reporting (Anchoring)
# ------------------------------------------------------------------
print("\n[6/6] Testing Report Anchoring...")
from agents.reporting_agent import reporting_agent
with patch("agents.reporting_agent.generate_report_content") as mock_rep:
    mock_rep.return_value = "Body"
    state = reporting_agent.run(state)
    
    # Check if GAP ID is in context
    call_args = mock_rep.call_args[0][0]
    # We generated gaps in Step 2. e.g. GAP_CONCEPT_GNN
    assert "GAP_" in call_args, "Reporting Fail: Gap IDs not in prompt"
    
    # Check manual append
    final_report = state["draft_report"]
    assert "Evidence Summary" in final_report
    assert "<!-- Generated by VRA Reporting Agent -->" in final_report

print("✅ Reporting Anchoring Verified.")

print("\n🎉 Phase 3.1 ENHANCED Verification Complete in All Aspects!")
