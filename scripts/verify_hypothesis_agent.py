import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock modules BEFORE importing agent if possible, or patch them
with patch.dict(sys.modules, {'services.research_service': MagicMock(), 'services.llm_service': MagicMock()}):
    from agents.hypothesis_generation_agent import hypothesis_generation_agent

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_agent():
    print("Testing HypothesisGenerationAgent with MOCKS...")
    
    # Mock State
    state = {
        "query": "Battery Optimization",
        "research_gaps": [
            {
                "confidence": 0.8,
                "concept": "Solid State Batteries",
                "description": "Lack of understanding in interface stability."
            }
        ],
        "concept_trends": {}
    }
    
    # Mock retrieval and LLM
    # We need to patch the functions imported inside the agent module
    with patch('agents.hypothesis_generation_agent.get_relevant_context', new_callable=MagicMock) as mock_retrieval, \
         patch('agents.hypothesis_generation_agent.generate_response', new_callable=MagicMock) as mock_llm:
        
        # Setup async mock for retrieval
        async def async_retrieval(*args, **kwargs):
            return "Mocked evidence from literature."
        mock_retrieval.side_effect = async_retrieval

        # Setup mock for LLM (it is called via asyncio.to_thread, so the mock itself can be sync)
        mock_llm.return_value = """
        {
            "hypotheses": [
                {
                    "id": "HYP_01",
                    "statement": "If we use solid electrolytes, stability improves.",
                    "novelty_score": 8,
                    "testability_score": 9,
                    "supporting_evidence": "Evidence A"
                }
            ]
        }
        """

        try:
            updated_state = await hypothesis_generation_agent.run(state)
            hypotheses = updated_state.get("hypotheses", [])
            print(f"Success! Generated {len(hypotheses)} hypotheses.")
            for h in hypotheses:
                print(f"- {h.get('id')}: {h.get('statement')}")
                
        except Exception as e:
            print(f"Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
