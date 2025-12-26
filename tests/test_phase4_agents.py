
# tests/test_phase4_agents.py
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.hypothesis_generation_agent import hypothesis_generation_agent
from agents.reviewer_agent import reviewer_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_phase4():
    print("🧪 Testing Phase 4 Agents...")
    
    # Mock State with Gaps
    state = {
        "query": "Quantum Machine Learning",
        "research_gaps": [
            {
                "gap_id": "GAP_01",
                "concept": "Error Correction",
                "description": "Lack of robust error correction in NISQ devices for ML tasks.",
                "confidence": 0.85
            }
        ],
        "concept_trends": {
            "Variational Circuits": {"status": "growth", "growth_rate": 0.2}
        },
        "hypotheses": [],
        "reviews": []
    }

    # 1. Run Hypothesis Generation
    print("\n--- Running Hypothesis Generation ---")
    state = hypothesis_generation_agent.run(state)
    
    if state["hypotheses"]:
        print(f"✅ Generated {len(state['hypotheses'])} hypotheses.")
        print(state["hypotheses"][0])
    else:
        print("❌ No hypotheses generated.")
        return

    # 2. Run Reviewer
    print("\n--- Running Reviewer ---")
    state = reviewer_agent.run(state)
    
    if state["reviews"]:
        print(f"✅ Generated {len(state['reviews'])} reviews.")
        print(state["reviews"][0])
    else:
        print("❌ No reviews generated.")
        return

    print("\n✅ Phase 4 Test Complete!")

if __name__ == "__main__":
    test_phase4()
