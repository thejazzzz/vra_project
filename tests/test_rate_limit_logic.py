import asyncio
import time
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set min delay for testing to 2 seconds so test runs quickly
os.environ["LLM_MIN_DELAY"] = "2.0"

from services.llm.orchestrator import LLMOrchestrator
import services.llm.orchestrator as orchestrator_module

def mock_generate_response(*args, **kwargs):
    print(f"[{time.time():.2f}] Mock generate_response executed.")
    time.sleep(0.1)
    return "Mocked response"

# Monkeypatch the module-level function reference
orchestrator_module.generate_response = mock_generate_response

async def test_concurrent_calls():
    print("Testing 3 concurrent LLM calls...")
    start_time = time.time()
    
    tasks = [
        LLMOrchestrator.robust_generate_response(prompt=f"Test {i}")
        for i in range(3)
    ]
    
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    elapsed = end_time - start_time
    print(f"Total time for 3 calls with 2.0s min delay: {elapsed:.2f}s")
    
    # First call happens immediately
    # Second call waits 2s
    # Third call waits another 2s
    # Total time should be at least 4 seconds
    assert elapsed >= 4.0, f"Expected at least 4.0s elapsed time, got {elapsed:.2f}s"
    print("✅ Concurrency rate limit test passed!")

if __name__ == "__main__":
    asyncio.run(test_concurrent_calls())
