
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Configuration
logging.basicConfig(level=logging.INFO)
print("🛠️ Testing Level 5: Graph Editing API...")

# AGGRESSIVE MOCKING
# Pre-emptively mock modules that might trigger DB connections
sys.modules["database"] = MagicMock()
sys.modules["database.db"] = MagicMock()
sys.modules["database.models"] = MagicMock()
sys.modules["database.models.graph_model"] = MagicMock()
sys.modules["services.graph_persistence_service"] = MagicMock()

# Now import Router
try:
    from api.routers.graph_viewer import edit_graph, EditGraphRequest, apply_graph_edit
except ImportError as e:
    print(f"❌ ImportError: {e}")
    sys.exit(1)

# Mock Data
mock_knowledge = {
    "nodes": [{"id": "A", "type": "concept"}],
    "links": []
}
mock_citation = {"nodes": [], "links": []}

mock_graphs = {
    "knowledge_graph": mock_knowledge,
    "citation_graph": mock_citation
}

def mock_load_graphs(query, user_id):
    return mock_graphs

def mock_save_graphs(query, user_id, knowledge, citation):
    print("   -> mocked save_graphs called.")
    pass

# Patch Persistence calls inside the router function
# Note: Since we mocked the module, the 'load_graphs' imported by graph_viewer is already a Mock object (attribute of the mock module).
# However, `load_graphs` in graph_viewer is bound to that mock.
# We need to configure that specific mock or patch where it's used.
# Since we mocked the whole module `services.graph_persistence_service`, 
# `from services.graph_persistence_service import load_graphs` makes `load_graphs` a Mock.
# We can set its side_effect.

# Access the mock that was imported into graph_viewer
from api.routers import graph_viewer
graph_viewer.load_graphs.side_effect = mock_load_graphs
graph_viewer.save_graphs.side_effect = mock_save_graphs

# Test 1: Add Node
print("\n[Test 1] Adding a Node...")
req = EditGraphRequest(
    action="add_node",
    graph_type="knowledge",
    payload={"node": {"id": "B", "type": "method"}}
)

resp = edit_graph(query="test_q", request=req, user_id="test_user")

nodes = resp["updated_graph"]["nodes"]
assert len(nodes) == 2, "Failed to add node"
assert any(n["id"] == "B" for n in nodes), "New node B not found"
print("✅ Node Added Successfully.")

# Test 2: Add Edge
print("\n[Test 2] Adding an Edge...")
req = EditGraphRequest(
    action="add_edge",
    graph_type="knowledge",
    payload={"source": "A", "target": "B", "relation": "test_rel"}
)

resp = edit_graph(query="test_q", request=req, user_id="test_user")
links = resp["updated_graph"]["links"]
assert len(links) == 1, "Failed to add edge"
assert links[0]["source"] == "A" and links[0]["target"] == "B", "Edge content mismatch"
print("✅ Edge Added Successfully.")

# Test 3: Delete Node
print("\n[Test 3] Deleting a Node...")
req = EditGraphRequest(
    action="delete_node",
    graph_type="knowledge",
    payload={"id": "A"}
)

resp = edit_graph(query="test_q", request=req, user_id="test_user")
nodes = resp["updated_graph"]["nodes"]
links = resp["updated_graph"]["links"]

assert len(nodes) == 1, "Failed to delete node A (should be 1 left: B)"
assert nodes[0]["id"] == "B", "Wrong node remaining"
assert len(links) == 0, "Failed to cascade delete edge connected to A"
print("✅ Node Deleted (and cascading edge delete) Successful.")

print("\n🎉 Level 5 Graph Editing API Verified.")
