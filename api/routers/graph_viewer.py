# File: api/routers/graph_viewer.py
from html import escape
from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException, Header, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from services.graph_persistence_service import load_graphs, save_graphs
from services.graph_editing_service import apply_graph_edit
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class EditGraphRequest(BaseModel):
    """Request model for graph editing operations."""
    action: str = Field(..., description="Edit action to perform")
    graph_type: Literal["knowledge", "citation"] = Field(..., description="Target graph type")
    payload: Dict[str, Any] = Field(..., description="Action-specific payload")

def get_user_id(x_user_id: Optional[str] = Header(None)):
    """
    Temporary user-id resolver.
    """
    return x_user_id or "demo-user"


@router.get("/graph-view/{query}", response_class=HTMLResponse)
def view_graph(query: str, user_id: str = Depends(get_user_id)):

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query parameter")
    graphs = load_graphs(query, user_id)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graphs not found")

    # Safe encode JSON to avoid breaking HTML or enabling JS injection
    kg_json = json.dumps(graphs["knowledge_graph"], ensure_ascii=False).replace("</", "<\\/")
    cg_json = json.dumps(graphs["citation_graph"], ensure_ascii=False).replace("</", "<\\/")

    esc_query = escape(query)
    esc_user = escape(user_id)

    integrity_hash = (
        "sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i"
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"/>
    <title>Graph Viewer - {esc_query}</title>

    <meta http-equiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/ 'unsafe-inline';
                   style-src 'self' 'unsafe-inline';">

    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        button {{
            padding: 10px 16px; margin-right: 10px; cursor: pointer;
            background: #0078ff; color: white; border: none; border-radius: 6px;
            font-size: 14px;
        }}
        button.active {{ background: #005fcc; }}
        svg {{ border: 1px solid #ddd; margin-top: 20px; background: #fafafa; }}
        text {{ font-size: 12px; fill: #111; }}
    </style>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
            integrity="{integrity_hash}"
            crossorigin="anonymous"></script>
</head>

<body>
    <h2>Graph Viewer — {esc_query}</h2>
    <p><small>User: {esc_user}</small></p>

    <button id="btn-kg" class="active">Knowledge Graph</button>
    <button id="btn-cg">Citation Graph</button>

    <svg width="1200" height="700"></svg>

    <script>
        const knowledge = {kg_json};
        const citation = {cg_json};

        const svg = d3.select("svg");
        const width = +svg.attr("width");
        const height = +svg.attr("height");

        let simulation;

        function render(graph) {{
            svg.selectAll("*").remove();
            if (simulation) simulation.stop();

            const links = graph.links || [];
            const nodes = graph.nodes || [];

            const link = svg.append("g")
                .selectAll("line")
                .data(links).enter()
                .append("line")
                .style("stroke", "#aaa")
                .style("stroke-width", 1.2);

            link.append("title")
                .text(d => d.evidence && d.evidence.excerpt 
                    ? `Relation: ${d.relation}\nEvidence: "${d.evidence.excerpt}"\nSource: ${d.evidence.paper_id}` 
                    : `Relation: ${d.relation}`);

            const node = svg.append("g")
                .selectAll("circle")
                .data(nodes).enter()
                .append("circle")
                .attr("r", 14)
                .style("fill", d => d.type === "paper" ? "#ff9f43" :
                                   d.type === "concept" ? "#69b3a2" :
                                   "#999")
                .call(d3.drag()
                    .on("start", event => {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        event.subject.fx = event.subject.x;
                        event.subject.fy = event.subject.y;
                    }})
                    .on("drag", event => {{
                        event.subject.fx = event.x;
                        event.subject.fy = event.y;
                    }})
                    .on("end", event => {{
                        if (!event.active) simulation.alphaTarget(0);
                        event.subject.fx = null;
                        event.subject.fy = null;
                    }}));

            const label = svg.append("g")
                .selectAll("text")
                .data(nodes).enter()
                .append("text")
                .text(d => d.id)
                .attr("dy", -18);

            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-400))
                .force("center", d3.forceCenter(width / 2, height / 2));

            simulation.on("tick", () => {{
                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node.attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                label.attr("x", d => d.x)
                     .attr("y", d => d.y);
            }});
        }}

        document.getElementById("btn-kg").onclick = () => {{
            document.getElementById("btn-kg").classList.add("active");
            document.getElementById("btn-cg").classList.remove("active");
            render(knowledge);
        }};

        document.getElementById("btn-cg").onclick = () => {{
            document.getElementById("btn-cg").classList.add("active");
            document.getElementById("btn-kg").classList.remove("active");
            render(citation);
        }};

        render(knowledge);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/data/{query}")
def get_graph_data(query: str, user_id: str = Depends(get_user_id)):
    """
    Return raw JSON data for the frontend graph viewer.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Invalid query parameter")

    graphs = load_graphs(query, user_id)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graphs not found")

    return {
        "nodes": graphs["knowledge_graph"].get("nodes", []),
        "edges": graphs["knowledge_graph"].get("links", []),
        "citation_nodes": graphs["citation_graph"].get("nodes", []),
        "citation_links": graphs["citation_graph"].get("links", [])
    }


@router.post("/graph-edit/{query}")
def edit_graph(
    query: str,
    request: EditGraphRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Apply an edit to the graph and save it.
    """
    graphs = load_graphs(query, user_id)
    if not graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    target_graph_key = "knowledge_graph" if request.graph_type == "knowledge" else "citation_graph"
    if request.graph_type not in ["knowledge", "citation"]:
        raise HTTPException(status_code=400, detail=f"Invalid graph_type: {request.graph_type}")
    current_graph_data = graphs.get(target_graph_key)
    
    if not current_graph_data:
        current_graph_data = {"nodes": [], "links": []}

    try:
        updated_data = apply_graph_edit(current_graph_data, request.action, request.payload)
        graphs[target_graph_key] = updated_data
        
        # Save back to DB
        save_graphs(
            query=query,
            user_id=user_id,
            knowledge=graphs["knowledge_graph"],
            citation=graphs["citation_graph"]
        )
        
        return {"status": "success", "message": f"Applied {request.action}", "updated_graph": updated_data}

    except Exception as e:
        logger.error(f"Graph edit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply graph edit")

