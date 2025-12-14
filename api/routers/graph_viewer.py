# File: api/routers/graph_viewer.py
from html import escape
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from services.graph_persistence_service import load_graphs
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


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
        "sha384-tB6xhxL7sRKqGZo4PMBVXgS5aXoaZySUdkGFUTkOcJCIZy9FHn5Vf3L7hIwrKyYV"
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
