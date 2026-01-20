import os
import sys

from dotenv import load_dotenv
load_dotenv(".env.local")

# 1. MOCK ENVIRONMENT (Override .env.local)
os.environ["DATABASE_URL"] = "postgresql://mock:mock@localhost:5432/mock_db"
os.environ["OPENAI_API_KEY"] = "mock-key"

from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.graph_service import build_knowledge_graph
from services.graph_analytics_service import GraphAnalyticsService
from services.memory_service import MemoryService
from services.trend_service import TrendService
from database.models.memory_model import GlobalConceptStats, GlobalEdgeStats, TrendState

# Mock Data
MOCK_SMALL_PAPER_SET = {
    "p1": {"concepts": ["A", "B"], "relations": [{"source": "A", "target": "B", "relation": "causes"}]}
}

MOCK_LARGE_PAPER_SET = {
    f"p{i}": {
        "concepts": [f"N{i}A", f"N{i}B", "C", "D"], 
        "relations": [{"source": f"N{i}A", "target": f"N{i}B", "relation": "causes"}]
    } for i in range(1, 4)
}
MOCK_LARGE_PAPER_SET["p0"] = {
    "concepts": ["A", "B", "C", "D"], 
    "relations": [{"source": "A", "target": "B", "relation": "causes"}]
}

@patch("services.memory_service.SessionLocal")
def test_scope_guard_refusal(mock_session):
    """
    TestCase 1: System determines 'INSUFFICIENT_DATA' when sources < 3.
    Frontend Contract: Verify 'scope_limited' flag is set.
    """
    print("\n🧪 Test 1: Scope Guard Refusal...")
    # Prepare Data Correctly
    p_relations = {pid: data["relations"] for pid, data in MOCK_SMALL_PAPER_SET.items()}
    p_concepts = {pid: data["concepts"] for pid, data in MOCK_SMALL_PAPER_SET.items()}

    # 1. Build Graph with small data
    kg = build_knowledge_graph(
        paper_relations=p_relations, 
        paper_concepts=p_concepts,
        run_meta={"query": "test_q"}
    )
    print(f"DEBUG: Type of KG: {type(kg)}")
    print(f"DEBUG: KG Keys: {kg.keys() if isinstance(kg, dict) else 'Not a dict'}")
    
    # 2. Verify Scope Flag
    # Check if 'graph' key exists using assertion
    assert "graph" in kg, "❌ 'graph' key missing in KG response."

    print(f"DEBUG: KG['graph'] type: {type(kg['graph'])}")
    print(f"DEBUG: KG['graph'] content: {kg['graph']}")

    assert kg["graph"].get("scope_limited") == True, "❌ Failed: scope_limited should be True for small dataset"
    print("   ✅ Graph marked as scope_limited.")
    
    # 3. Verify Analytics Refusal
    analytics_service = GraphAnalyticsService(kg)
    results = analytics_service.analyze()
    
    assert results["status"] == "INSUFFICIENT_DATA", "❌ Failed: Analytics status should be INSUFFICIENT_DATA"
    print("   ✅ Analytics refused successfully.")


@patch("services.memory_service.SessionLocal")
def test_approval_gate_and_memory(mock_session_cls):
    """
    TestCase 2: 'Approve' action triggers Memory Service.
    TestCase 3: Subsequent runs show Novelty Decay.
    """
    print("\n🧪 Test 2 & 3: Approval Gate & Novelty Decay...")
    
    # Mock DB Session
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_db.__enter__.return_value = mock_db # Critical for 'with SessionLocal() as db:'
    
    from datetime import datetime, timezone, timedelta
    now_aware = datetime.now(timezone.utc)

    # Mock Data Objects
    mock_edge_stats = MagicMock(spec=GlobalEdgeStats)
    mock_edge_stats.run_count = 5
    mock_edge_stats.weighted_frequency = 5.0
    mock_edge_stats.last_seen = now_aware
    mock_edge_stats.first_seen = now_aware - timedelta(days=100)

    mock_concept_stats = MagicMock(spec=GlobalConceptStats)
    mock_concept_stats.first_seen = now_aware - timedelta(days=100)
    mock_concept_stats.last_seen = now_aware
    mock_concept_stats.run_count = 5
    mock_concept_stats.weighted_frequency = 5.0

    # Mock db.scalar(select(...))
    def side_effect_scalar(stmt):
        # We can try to guess the model from the statement string representation or just return generic mocks
        s = str(stmt)
        if "global_edge_stats" in s.lower():
            return mock_edge_stats
        if "global_concept_stats" in s.lower():
            return mock_concept_stats
        return None

    mock_db.scalar.side_effect = side_effect_scalar

    
    # 1. Build Graph (Large enough to pass scope)
    p_relations_lg = {pid: data["relations"] for pid, data in MOCK_LARGE_PAPER_SET.items()}
    p_concepts_lg = {pid: data["concepts"] for pid, data in MOCK_LARGE_PAPER_SET.items()}
    
    kg = build_knowledge_graph(
        paper_relations=p_relations_lg,
        paper_concepts=p_concepts_lg, 
        run_meta={"query": "test_q_large"}
    )
    assert kg["graph"].get("scope_limited") == False
    
    # 2. Run Analytics (Should simulate fetching history)
    # We need to mock MemoryService.get_edge_context to return our mock stats
    # 3. Simulate Approval (The Gate)
    # We need to mock MemoryService.get_edge_context to return our mock stats (Use 'max_run_count')
    with patch.object(MemoryService, 'get_edge_context', return_value={"max_run_count": 5, "is_contested": False}):
        analytics_service = GraphAnalyticsService(kg)
        results = analytics_service.analyze()
        
        # Verify Novelty Decay
        # Base decay for 5 runs should be significant
        # Note: Concepts are likely normalized to lowercase in KnowledgeGraphBuilder
        scored_edge = next((e for e in results["novelty"] if e["source"].lower() == "a" and e["target"].lower() == "b"), None)
        available_edges = [f"{n['source']}->{n['target']}" for n in results['novelty']]
        assert scored_edge is not None, f"❌ Failed: Expected edge A->B not found. Available: {available_edges}"
        print(f"   ℹ️  Edge Novelty Score: {scored_edge['score']}")
        # Score scale is 0-100. Base ~25-50. Decayed ~12-25. 
        # Just ensure it's not maxed out (100) and exists.
        assert scored_edge["score"] < 90, "❌ Failed: Novelty should be decayed for known edge."
        print("   ✅ Novelty Decay verified.")

    # 3. Simulate Approval (The Gate)
    print("\n🧪 Test: Approving Graph...")
    MemoryService.update_global_stats(kg, approved=True)
    
    # Verify DB Upsert called
    # We expect 'A', 'B' concepts and 'A->B' edge to be added/updated
    # The implementation uses db.add() and db.commit()
    assert mock_db.commit.called, "❌ Failed: DB Commit not called on approval."
    print("   ✅ Global Memory update triggered.")

@patch("services.memory_service.SessionLocal")
def test_trend_calculation(mock_session):
    """
    TestCase 4: Trend classification logic (Emerging vs Stable).
    """
    print("\n🧪 Test 4: Trend Intelligence...")
    try:
        from datetime import datetime, timezone, timedelta
        
        # Legacy Concept: Seen 3 years ago, created 3 years ago (Aware)
        old_date = datetime.now(timezone.utc) - timedelta(days=365*3)
        print(f"DEBUG: old_date type: {type(old_date)}")
        print(f"DEBUG: now type: {type(datetime.now(timezone.utc))}")
        
        # Case A: Stable (High freq, consistent)
        state_stable = TrendService.calculate_trend(
            first_seen=old_date,
            last_seen=datetime.now(timezone.utc),
            _run_count=20,
            weighted_freq=15.0
        )
        assert state_stable.value == "stable", f"❌ Expected stable, got {state_stable}"
        print(f"   ✅ 'Stable' logic verified.")
        
        # Case B: Re-emerging (Old start, gap, recent activity)
        state_reemerge = TrendService.calculate_trend(
            first_seen=old_date,
            last_seen=datetime.now(timezone.utc),
            _run_count=5, 
            weighted_freq=5.0
        )
        assert state_reemerge.value == "reemerging", f"❌ Expected reemerging, got {state_reemerge}"
        print(f"   ✅ 'Re-emerging' logic verified.")
    except Exception as e:
        print(f"💥 ERROR in Test 4: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("🚀 Starting Research-Grade System Verification...")
    try:
        test_scope_guard_refusal()
        test_approval_gate_and_memory()
        test_trend_calculation()
        print("\n🏆 ALL SYSTEMS GO. Backend Logic is 100% compliant.")
    except AssertionError as e:
        print(f"\n💥 VERIFICATION FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 RUNTIME ERROR: {str(e)}")
        sys.exit(1)
