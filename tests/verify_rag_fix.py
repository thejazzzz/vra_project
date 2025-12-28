
import logging
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VERIFY_RAG")

# Add project root to path
sys.path.append(".")

# --- MOCK ENV VARS & DATABASE TO PREVENT CRASHES ---
os.environ["POSTGRES_USER"] = "dummy"
os.environ["POSTGRES_PASSWORD"] = "dummy" 
os.environ["POSTGRES_DB"] = "dummy"
os.environ["POSTGRES_HOST"] = "localhost"

# Mock the database module completely before importing service
sys.modules["database.db"] = MagicMock()
sys.modules["database.db"].SessionLocal = MagicMock()

from services.research_service import get_relevant_context
from clients.chroma_client import _ChromaClient

class TestRetrievalActiveRAG(unittest.TestCase):
    
    @patch('services.research_service.get_client')
    def test_get_relevant_context(self, mock_get_client):
        logger.info("TEST: Verifying get_relevant_context logic...")
        
        # Mock Chroma Client
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance
        
        # Mock Search Results
        mock_results = [
            {
                "id": "paper-1",
                "document": "This is abstract 1.",
                "metadata": {"canonical_id": "P1", "year": 2023},
                "distance": 0.5
            },
            {
                "id": "paper-2",
                "document": "This is abstract 2.",
                "metadata": {"canonical_id": "P2", "year": 2024},
                "distance": 0.8
            },
             {
                "id": "paper-1-dup", # Duplicate canonical ID
                "document": "This is abstract 1 again.",
                "metadata": {"canonical_id": "P1", "year": 2023},
                "distance": 0.6
            }
        ]
        
        mock_client_instance.search.return_value = mock_results
        
        # Execute
        context = get_relevant_context("test query", limit=5)
        
        # Assertions
        logger.info(f"Context Returned:\n{context}")
        
        self.assertIn("[Source: P1]", context)
        self.assertIn("[Source: P2]", context)
        self.assertIn("This is abstract 1.", context)
        
        # Verify Deduplication (P1 should appear only once as a header)
        self.assertEqual(context.count("[Source: P1]"), 1)
        
        # Verify Call Args
        mock_client_instance.search.assert_called_with("test query", n_results=5)
        logger.info("✅ get_relevant_context passed.")

    @patch('services.research_service.get_client')
    def test_fallback_logic(self, mock_get_client):
        logger.info("TEST: Verifying Fallback Logic...")
        
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance
        
        # First call returns empty
        # Second call returns something
        mock_client_instance.search.side_effect = [
            [], # First result (empty)
            [{"id": "fallback", "document": "Fallback doc", "metadata": {"canonical_id": "FB"}, "distance": 0.5}]
        ]
        
        long_query = "this is a very long specific query that fails"
        context = get_relevant_context(long_query)
        
        self.assertIn("Fallback doc", context)
        logger.info("✅ Fallback logic passed.")

if __name__ == "__main__":
    unittest.main()
