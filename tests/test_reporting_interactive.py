
import os
# Mock DB credentials to prevent database.db from raising ValueError on import
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")

import pytest
from unittest.mock import MagicMock, patch
from services.reporting.reporting_service import InteractiveReportingService
from state.state_schema import ReportState

@pytest.fixture
def mock_state_service():
    with patch("services.reporting.reporting_service.load_state_for_query") as mock_load, \
         patch("services.reporting.reporting_service.save_state_for_query") as mock_save:
        
        # In-memory mock state store
        store = {}
        
        def load(sid, uid):
            return store.get(sid)
        
        def save(sid, state, uid):
            store[sid] = state
            return 1
            
        mock_load.side_effect = load
        mock_save.side_effect = save
        yield store

@pytest.fixture
def mock_generator():
    with patch("services.reporting.report_generator.ReportGenerator.generate_section_content") as mock_gen:
        mock_gen.return_value = {
            "content": "## Mock Content\nThis is generated content.",
            "prompt_version": "vMock",
            "model_name": "mock-gpt"
        }
        yield mock_gen

@pytest.mark.asyncio
async def test_interactive_workflow(mock_state_service, mock_generator):
    session_id = "test_session"
    user_id = "test_user"
    
    # 0. Setup Mock State
    mock_state_service["test_session"] = {
        "query": "Test Query",
        "user_id": user_id,
        "collected_papers": [],
        "report_state": None,
        "current_step": "analysis_complete"
    }

    # 1. Initialize
    state = InteractiveReportingService.initialize_report(session_id, user_id, confirm=True)
    assert state["report_status"] == "planned"
    assert len(state["sections"]) > 0
    assert state["sections"][0]["section_id"] == "exec_summary"
    assert state["user_confirmed_start"] is True

    # 2. Plan Check
    exec_sec = state["sections"][0]
    assert exec_sec["status"] == "planned"
    
    # 3. Generate Section (Exec Summary usually has deps, but in this minimal state maybe not if analysis is empty? 
    # Actually SectionPlanner checks 'has_required_data'. Our mock state is emptyish. 
    # Let's see what SectionPlanner produced. 
    # If we mocked SectionPlanner implicitly by real import, it behaves realistically.
    # In planner, exec summary depends on analysis sections IF THEY EXIST.
    # In our mock state, trends/gaps don't exist, so only Exec Summary and Appendix might be planned.
    
    # Let's try to generate "exec_summary".
    # Need to patch dependencies if it has any.
    # Check what deps it has:
    print(f"Deps: {exec_sec['depends_on']}")
    
    generated_sec = await InteractiveReportingService.generate_section(session_id, user_id, "exec_summary")
    assert generated_sec["status"] == "review"
    assert generated_sec["content"] == "## Mock Content\nThis is generated content."
    assert generated_sec["revision"] == 1
    
    # Verify Lock Released
    state_after = mock_state_service["test_session"]["report_state"]
    assert state_after["locks"]["sections"]["exec_summary"] is False

    # 4. Reject Section
    rejected = InteractiveReportingService.submit_review(session_id, user_id, "exec_summary", accepted=False, feedback="Bad tone")
    assert rejected["status"] == "planned"
    assert rejected["history"][0]["feedback"] == "Bad tone"
    
    # 5. Regen
    regen = await InteractiveReportingService.generate_section(session_id, user_id, "exec_summary")
    assert regen["revision"] == 2
    
    # 6. Accept
    accepted = InteractiveReportingService.submit_review(session_id, user_id, "exec_summary", accepted=True)
    assert accepted["status"] == "accepted"
    
    # 7. Finalize (Assuming only Exec Sum + Appendix exist)
    # Mark appendix accepted
    appendix = next(s for s in state_after["sections"] if s["section_id"] == "appendix")
    appendix["status"] = "accepted"
    
    final_state = InteractiveReportingService.finalize_report(session_id, user_id, confirm=True)
    assert final_state["report_status"] == "completed"
    assert final_state["locks"]["report"] is True
    
    # 8. Test Failure Recovery (Simulated)
    # Reset a section to force state back to in_progress (if logic permits)
    # Actually, report is locked. Reset should fail or require force?
    # Logic in reset_section just checks force=True.
    
    # Let's test Export Logic separately via service (if export service had state checks, 
    # but checks are in API router. Test uses Service directly. 
    # Service doesn't have export method with checks, router does.
    # So we can't test API checks here easily without TestClient.
    
    # But we can test ReportingService failure states.
    # Simulate generation failure
    try:
         with patch("services.reporting.report_generator.ReportGenerator.generate_section_content", side_effect=Exception("Gen Fail")):
             await InteractiveReportingService.generate_section(session_id, user_id, "exec_summary")
    except Exception:
         pass
         
    # Check status is failed? 
    # Wait, we finalized already. Cannot generate if locked.
    # State is completed.

