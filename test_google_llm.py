import sys
import os

# Ensure we can import from the project root
sys.path.insert(0, os.path.abspath('.'))

from services.llm_service import generate_response
from services.llm_factory import LLMProvider

def test_google_provider():
    print("Testing Google LLM Provider...")
    try:
        response = generate_response(
            prompt="Reply with exactly 'GOOGLE_API_WORKS'.",
            provider=LLMProvider.GOOGLE
        )
        print(f"Response: {response}")
        if "GOOGLE_API_WORKS" in response:
            print("SUCCESS! Google AI Studio integration is working.")
        else:
            print("WARNING: Unexpected response.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_google_provider()
