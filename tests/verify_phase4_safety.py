# tests/verify_phase4_safety.py
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv(".env.local")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.graph_service import build_knowledge_graph
from services.graph_analytics_service import GraphAnalyticsService
from services.memory_service import MemoryService

class TestPhase4Safety(unittest.TestCase):
    
    def test_scope_guard_refusal(self):
        print("\n🧪 Testing Scope Guard Refusal...")
        # 1. Create Sparse Data (< 3 papers)
        raw_data = {
            "P1": [{"source": "A", "target": "B", "relation": "associated_with"}]
        }
        
        # 2. Build Graph
        kg = build_knowledge_graph(paper_relations=raw_data)
        
        # 3. Check Flag
        is_limited = kg.get("graph", {}).get("scope_limited")
        print(f"Scope Limited Flag: {is_limited}")
        self.assertTrue(is_limited, "❌ Graph should be marked scope_limited")
        
        # 4. Check Analytics Refusal
        analytics = GraphAnalyticsService(kg).analyze()
        print(f"Analytics Status: {analytics.get('status')}")
        self.assertEqual(analytics.get("status"), "INSUFFICIENT_DATA", "❌ Analytics should refuse to run")
        print("✅ Scope Guard Verified.")

    @patch('services.graph_analytics_service.MemoryService')
    def test_novelty_decay(self, mock_memory):
        print("\n🧪 Testing Novelty Decay (Longitudinal Memory)...")
        
        # Setup: Graph with valid scope
        raw_data = {f"P{i}": [{"source": "A", "target": "B", "relation": "improves", "evidence": {"excerpt": "text"}}] for i in range(5)}
        # Add a "Idea" bridge
        raw_data["P1"].append({"source": "A", "target": "C", "relation": "causes"})
        raw_data["P2"].append({"source": "C", "target": "B", "relation": "causes"})
        
        # Case A: First Run (0 history)
        mock_memory.get_edge_context.return_value = {"max_run_count": 0, "is_contested": False}
        
        kg = build_knowledge_graph(paper_relations=raw_data)
        service = GraphAnalyticsService(kg)
        
        # Force graph to NOT be scope limited (we have 5 papers, should be fine)
        # But let's debug actual flag
        # print(kg["graph"]) 
        
        novelty_a = service._score_novelty()
        score_a = novelty_a[0]["score"] if novelty_a else 0
        print(f"Score (Run 0): {score_a}")
        
        # Case B: 10th Run (High history)
        mock_memory.get_edge_context.return_value = {"max_run_count": 10, "is_contested": False}
        novelty_b = service._score_novelty()
        score_b = novelty_b[0]["score"] if novelty_b else 0
        print(f"Score (Run 10): {score_b}")
        
        self.assertLess(score_b, score_a, "❌ Novelty should decay with history")
        print("✅ Novelty Decay Verified.")

if __name__ == "__main__":
    unittest.main()
