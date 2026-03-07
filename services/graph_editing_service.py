#File: services/graph_editing_service.py
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
        return next((i for i, n in enumerate(nodes) if n.get("id") == nid), -1)
        
    if action == "add_node":
        import uuid
        nid = payload.get("node_id") or str(uuid.uuid4())
        label = payload.get("node_label") or nid
        if find_node_idx(nid) == -1:
            nodes.append({
                "id": nid,
                "label": label,
                "type": payload.get("node_type", "concept"),
                "is_manual": True
            })
            
    elif action == "update_node":
        nid = payload.get("node_id")
        if not nid:
            logger.warning("Cannot update node: node_id missing")
            return {"nodes": nodes, "links": links}
        updates = payload.get("updates", {})
        
        if "id" in updates:
            logger.warning("Cannot update node: 'id' key modification is not allowed to preserve referential integrity.")
            updates.pop("id")
            
        idx = find_node_idx(nid)
        if idx == -1:
            logger.warning(f"Cannot update node: node '{nid}' not found")
            return {"nodes": nodes, "links": links}
        nodes[idx].update(updates)
            
    elif action == "remove_node":
        nid = payload.get("node_id")
        if not nid:
            logger.warning("Cannot remove node: node_id missing")
            return {"nodes": nodes, "links": links}
        nodes[:] = [n for n in nodes if n.get("id") != nid]
        links[:] = [l for l in links if l.get("source") != nid and l.get("target") != nid]

    elif action == "add_edge":
        src = payload.get("source")
        tgt = payload.get("target")
        relation = payload.get("relation", "related_to")
        
        if not src or not tgt:
            logger.warning("Cannot add edge: missing source or target in payload")
            return {"nodes": nodes, "links": links}
            
        if find_node_idx(src) == -1 or find_node_idx(tgt) == -1:
            logger.warning("Cannot add edge: source or target node not found in graph")
            return {"nodes": nodes, "links": links}
            
        exists = any(l.get("source") == src and l.get("target") == tgt for l in links)
        if not exists:
            links.append({
                "source": src,
                "target": tgt,
                "relation": relation,
                "type": "explicit",
                "causal_strength": "associative",
                "confidence": 1.0,
                "is_manual": True
            })
                
    elif action == "remove_edge":
        src = payload.get("source")
        tgt = payload.get("target")
        if not src or not tgt:
            logger.warning("Cannot remove edge: source or target missing")
            return {"nodes": nodes, "links": links}
        links[:] = [l for l in links if not (l.get("source") == src and l.get("target") == tgt)]
        

    return {
        "nodes": nodes,
        "links": links
    }
