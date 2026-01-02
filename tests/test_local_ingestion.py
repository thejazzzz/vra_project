from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from api.main import app
from services.research_service import ingest_local_file

client = TestClient(app)

from api.dependencies.auth import get_current_user, get_db

# Helper to override Auth
async def mock_get_current_user():
    from database.models.auth_models import User
    return User(id="test_user_id", email="test@example.com")

def mock_get_db():
    try:
        yield MagicMock()
    finally:
        pass

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_db] = mock_get_db

def test_local_ingestion_flow():
    # 1. Mock the PDF extractor to avoid needing a real PDF
    with patch("services.research_service.extract_text_from_pdf_bytes") as mock_extract:
        mock_extract.return_value = "This is the content of the local PDF paper."
        
        # 2. Mock vector client to avoid ChromaDB calls
        with patch("services.research_service.get_client") as mock_chroma:
            mock_chroma.return_value = MagicMock()
            
            # 3. MOCK SessionLocal in the service module!
            with patch("services.research_service.SessionLocal") as mock_session_local:
                mock_session = MagicMock()
                mock_session_local.return_value = mock_session
                
                # Mock refresh
                def side_effect_refresh(obj):
                    obj.id = 123
                mock_session.refresh.side_effect = side_effect_refresh

                # Mock DB Query results
                fake_paper = MagicMock()
                fake_paper.id = 123
                fake_paper.canonical_id = "local_file:hash123"
                fake_paper.title = "My Proposal"
                fake_paper.paper_id = None
                fake_paper.abstract = "This is the content of the local PDF paper."
                fake_paper.paper_metadata = {"source": "local_file", "authors": ["User Upload"]}
                fake_paper.published_year = 2024
                
                # Configure query
                mock_query = mock_session.query.return_value
                mock_filter = mock_query.filter.return_value
                mock_filter.all.return_value = [fake_paper]
                mock_filter.one_or_none.return_value = None
            
                # --- STEP 1: UPLOAD ---
                # Send non-PDF first (should fail)
                response = client.post(
                    "/upload/",
                    files={"file": ("test.txt", b"dummy content", "text/plain")}
                )
                assert response.status_code == 400
                
                # Send PDF
                response = client.post(
                    "/upload/",
                    files={"file": ("my_proposal.pdf", b"%PDF-1.4 dummy binaries", "application/pdf")}
                )
                if response.status_code != 200:
                    print(f"\nUPLOAD FAILED: {response.status_code} {response.text}")

                assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "paper_id" in data
            assert data["title"] == "My Proposal"
            
            paper_id = data["paper_id"]
            canonical_id = data["canonical_id"]
            fake_paper.canonical_id = canonical_id
            
            # --- STEP 2: RESEARCH WITH LOCAL ID ---
            # Mock Data Acquisition to return nothing external
            with patch("services.research_service.data_acquisition_agent.run", new_callable=AsyncMock) as mock_agent:
                mock_agent.return_value = []
                
                payload = {
                    "query": "analyze my proposal",
                    "include_paper_ids": [paper_id]
                }
                
                res_research = client.post("/research/", json=payload)
                assert res_research.status_code == 200
                res_data = res_research.json()
                
                assert res_data["status"] == "success"
                papers = res_data["data"]["papers"]
                
                # Should have 1 paper (our local one)
                assert len(papers) == 1
                p = papers[0]
                assert p["title"] == "My Proposal"
                assert p["abstract"] == "This is the content of the local PDF paper."
                assert p["source"] == "local_file"
                
                # Verify it wasn't deduped away
                assert p["canonical_id"] == canonical_id
