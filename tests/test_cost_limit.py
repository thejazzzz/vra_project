import os
import pytest
from services.reporting.section_compiler import SectionCompiler, CostLimitExceededError
from services.llm_factory import LLMProvider

def test_cost_limit_guardrail():
    # Set MAX_CLOUD_CALLS via environment intentionally low for test
    os.environ["MAX_CLOUD_CALLS"] = "3"
    
    state = {
        "report_state": {
            "metrics": {
                "cloud_calls": 0
            }
        }
    }
    
    compiler = SectionCompiler(state)
    
    # 1. First call (0 -> 1)
    compiler._check_cost_guardrail(LLMProvider.OPENAI)
    assert state["report_state"]["metrics"]["cloud_calls"] == 1
    
    # 2. Second call (1 -> 2)
    compiler._check_cost_guardrail(LLMProvider.GOOGLE)
    assert state["report_state"]["metrics"]["cloud_calls"] == 2
    
    # 3. Third call (2 -> 3)
    compiler._check_cost_guardrail(LLMProvider.OPENROUTER)
    assert state["report_state"]["metrics"]["cloud_calls"] == 3
    
    # 4. Fourth call (3 >= limit, should raise)
    with pytest.raises(CostLimitExceededError) as exc_info:
        compiler._check_cost_guardrail(LLMProvider.OPENAI)
    
    assert "Max cloud calls reached" in str(exc_info.value)
    
    # Check that LOCAL provider does not increment limit
    compiler._check_cost_guardrail(LLMProvider.LOCAL)
    assert state["report_state"]["metrics"]["cloud_calls"] == 3

    # Clean up environment var
    os.environ.pop("MAX_CLOUD_CALLS", None)
