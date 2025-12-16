
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def apply_graph_edit(graph_data: Dict[str, Any], action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a manual edit to the graph structure (nodes/links).
    Returns the modified graph_data.
    """
    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    
    # helper to find index
    def find_node_idx(nid):
        return next((i for i, n in enumerate(nodes) if n["id"] == nid), -1)

    if action == "add_node":
        new_node = payload.get("node")
        if new_node and new_node.get("id"):
            # Check if exists
            if find_node_idx(new_node["id"]) == -1:
                nodes.append(new_node)
    
    elif action == "update_node":
        # payload: { "id": "...", "updates": { ... } }
        nid = payload.get("id")
        updates = payload.get("updates", {})
        idx = find_node_idx(nid)
        if idx != -1:
            nodes[idx].update(updates)
            
    elif action == "delete_node":
        nid = payload.get("id")
        # Remove node
        nodes = [n for n in nodes if n["id"] != nid]
        # Remove connected links
        links = [l for l in links if l["source"] != nid and l["target"] != nid]

    elif action == "add_edge":
        # payload: { "source": "...", "target": "...", "relation": "..." }
        src = payload.get("source")
        tgt = payload.get("target")
        if src and tgt:
            # Check if exists
            exists = any(l["source"] == src and l["target"] == tgt for l in links)
            if not exists:
                links.append(payload)

    elif action == "delete_edge":
        src = payload.get("source")
        tgt = payload.get("target")
        links = [l for l in links if not (l["source"] == src and l["target"] == tgt)]

    return {
        "nodes": nodes,
        "links": links
    }
