
import os
import pytest
import uuid
from unittest.mock import MagicMock, patch

# Mock DB credentials
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")

from services.reporting.reporting_service import InteractiveReportingService

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
async def test_interactive_workflow(mock_generator):
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Initial fake DB state for SessionLocal to find
    initial_db_state = {
        "query": "Test Research",
        "selected_papers": [{"id": "p1"}, {"id": "p2"}],
        "author_graph": {},
        # Report state starts empty/idle
        "report_state": {"report_status": "idle"}
    }
    
    # Store for persistence across mocks
    state_store = {
        session_id: initial_db_state
    }

    # 1. Test Initialize with DB Locking Mock
    with patch("database.db.SessionLocal") as MockSession:
        mock_db = MockSession.return_value
        
        # Setup the row returned by query()...filter()...with_for_update().first()
        mock_row = MagicMock()
        mock_row.state = initial_db_state
        
        # When db.commit() is called, we should theoretically update our store
        # But here valid code updates row.state. We can capture that.
        
        mock_db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_row
        
        # Call Initialize
        init_state = InteractiveReportingService.initialize_report(session_id, user_id, confirm=True)
        
        assert init_state["report_status"] == "planned"
        assert len(init_state["sections"]) > 0
        
        # Capture the updated state from the row for next steps
        state_store[session_id] = mock_row.state

    # 2. Mock Helpers for Rest of Workflow
    # The service uses load_state_for_query / save_state_for_query
    
    def mock_load(sid, uid):
        return state_store.get(sid)
        
    def mock_save(sid, st, uid):
        state_store[sid] = st
        return 1

    with patch("services.reporting.reporting_service.load_state_for_query", side_effect=mock_load), \
         patch("services.reporting.reporting_service.save_state_for_query", side_effect=mock_save):
         
        # 3. Get State
        state = InteractiveReportingService.get_report_state(session_id, user_id)
        assert state["report_status"] == "planned"
        
        sect_id = state["sections"][0]["section_id"]
        
        # Satisfy dependencies for the test section
        target_deps = state["sections"][0]["depends_on"]
        for dep_id in target_deps:
            # Find in sections and mark accepted
            for s in state_store[session_id]["report_state"]["sections"]:
                if s["section_id"] == dep_id:
                    s["status"] = "accepted"

        # 4. Generate (SYNC call)
        target_section = InteractiveReportingService.generate_section(session_id, user_id, sect_id)
        assert target_section["status"] == "review"
        assert target_section["content"] is not None
        
        # Verify global status updated
        current_state = state_store[session_id]["report_state"]
        assert current_state["report_status"] == "in_progress"
        
        # 5. Review - Reject
        InteractiveReportingService.submit_review(session_id, user_id, sect_id, accepted=False, feedback="Bad")
        current_state = state_store[session_id]["report_state"]
        sec = next(s for s in current_state["sections"] if s["section_id"] == sect_id)
        assert sec["status"] == "planned"
        assert sec["last_feedback"] == "Bad"
        
        # 6. Generate Revision 2
        target_section = InteractiveReportingService.generate_section(session_id, user_id, sect_id)
        assert target_section["revision"] == 2
        
        # 7. Accept
        InteractiveReportingService.submit_review(session_id, user_id, sect_id, accepted=True)
        current_state = state_store[session_id]["report_state"]
        sec = next(s for s in current_state["sections"] if s["section_id"] == sect_id)
        assert sec["status"] == "accepted"
        
        # 8. Finalize
        # Cheat: mark all sections accepted
        for s in current_state["sections"]:
            s["status"] = "accepted"
            
        final_state = InteractiveReportingService.finalize_report(session_id, user_id, confirm=True)
        assert final_state["report_status"] == "completed"
