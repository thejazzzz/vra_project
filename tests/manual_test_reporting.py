import sys
import os
import asyncio
from unittest.mock import MagicMock

from unittest.mock import MagicMock, patch
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 1. Mock OpenAI to prevent import errors if it tries to init client at top level
sys.modules["openai"] = MagicMock()

# 2. Mock the service function in the module that DEFINES it, OR mock where it is imported.
# Since we want to test ReportingAgent which imports it, we can mock it in sys.modules or patch it.

from services import analysis_service

# Detect if we need to set the env var to pass strict checks
os.environ["OPENAI_API_KEY"] = "sk-fake-key-for-testing"

# Mock the function implementation
analysis_service.generate_report_content = MagicMock(return_value="# Mocked Report\n\nThis is a test report.")

# 3. Import Agent AFTER modifications to the service module (if it uses 'from ... import')
# However, 'from x import y' binds y. If we change x.y, the already imported y is unchanged.
# So we need to ensure we import ReportingAgent AFTER this mock if possible, 
# or patch the imported name in ReportingAgent.

from agents import reporting_agent as reporting_agent_module

# Force update the reference in the agent module
reporting_agent_module.generate_report_content = analysis_service.generate_report_content

# Get the instance
agent_instance = reporting_agent_module.reporting_agent

async def test_reporting():
    print("🧪 Testing Reporting Agent...")
    
    fake_state = {
        "query": "Test Query",
        "global_analysis": {
            "summary": "This is a summary of the analysis.",
            "key_concepts": ["AI", "Agents"]
        },
        "current_step": "awaiting_report"
    }
    
    # Run agent
    new_state = agent_instance.run(fake_state)
    
    # Verify
    if new_state.get("draft_report") == "# Mocked Report\n\nThis is a test report.":
        print("✅ Report content set correctly.")
    else:
        print(f"❌ Report content mismatch: {new_state.get('draft_report')}")
        
    if new_state.get("current_step") == "awaiting_final_review":
        print("✅ Step transitioned correctly.")
    else:
        print(f"❌ Step mismatch: {new_state.get('current_step')}")

if __name__ == "__main__":
    asyncio.run(test_reporting())
